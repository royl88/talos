# coding=utf-8
"""
本模块提供DB的CRUD封装

"""

from __future__ import absolute_import

import collections
import contextlib
import copy
import logging
import warnings

import six
from sqlalchemy import text, and_, or_
import sqlalchemy.exc
import sqlalchemy.orm

from talos.core import config
from talos.core import exceptions
from talos.core import utils
from talos.core.i18n import _
from talos.db import filter_wrapper
from talos.db import pool
from talos.db import validator

if six.PY3:
    long = int
CONF = config.CONF
LOG = logging.getLogger(__name__)
VALIDATE_ON_ALL = '*:M'
SITUATION_ALL = '*'


class ColumnValidator(object):
    """
    列验证封装类
    """
    field = None
    rule = None
    rule_type = 'regex'
    validate_on = None
    error_msg = ''
    converter = None
    orm_required = True
    aliases = None
    nullable = False

    def __init__(self,
                 field,
                 rule=None,
                 rule_type=None,
                 validate_on=None,
                 error_msg='%(result)s',
                 converter=None,
                 orm_required=True,
                 aliases=None,
                 nullable=False):
        '''
        :param field: 字段名称
        :type field: str
        :param rule: 校验规则，或者校验规则的参数
        :type rule: Validator object/arguments of Validator
        :param rule_type: 校验规则的类型，如果rule是Validator对象，则rule_type不生效
        :type rule_type: str
        :param validate_on: 验证场景以及可选必选性, ['create:M', 'update:O'], create为函数名，M是必选，O是可选
        :type validate_on: list
        :param error_msg: 错误信息模板，可以接受result格式化参数，result为实际校验器返回错误信息
        :type error_msg: str
        :param converter: 转换器
        :type converter: Convertor object
        :param orm_required: 是否数据库字段，可以控制是否传递到实际数据库sql语句中
        :type orm_required: bool
        :param aliases: 别名列表，别名的key也被当做field进行处理
        :type aliases: list
        :param nullable: 是否可以为None
        :type nullable: bool
        '''

        self.field = field
        self.rule = rule
        self.rule_type = rule_type
        # 用户不指定，默认全部场景
        self.validate_on = validate_on or [VALIDATE_ON_ALL]
        self.error_msg = error_msg
        self.converter = converter
        self.orm_required = orm_required
        self.aliases = aliases or []
        self.nullable = nullable

        self.validate_on = self._build_situation(self.validate_on)
        if self.rule is None and self.rule_type is None:
            pass
        elif not isinstance(self.rule, validator.NullValidator):
            if self.rule_type == 'callback':
                self.rule = validator.CallbackValidator(self.rule)
            elif self.rule_type == 'regex':
                if utils.is_string_type(self.rule):
                    self.rule = validator.RegexValidator(self.rule)
            elif self.rule_type == 'email':
                self.rule = validator.EmailValidator()
            elif self.rule_type == 'phone':
                self.rule = validator.PhoneValidator()
            elif self.rule_type == 'url':
                self.rule = validator.UrlValidator()
            elif self.rule_type == 'length' and utils.is_string_type(self.rule):
                ranger = self.rule.split(',')
                self.rule = validator.LengthValidator(int(ranger[0].strip()), int(ranger[1].strip()))
            elif self.rule_type == 'in':
                self.rule = validator.InValidator(self.rule)
            elif self.rule_type == 'notin':
                self.rule = validator.NotInValidator(self.rule)
            elif self.rule_type == 'integer':
                self.rule = validator.NumberValidator(int, long)
            elif self.rule_type == 'float':
                self.rule = validator.NumberValidator(float)
            elif self.rule_type == 'type':
                types = self.rule
                self.rule = validator.TypeValidator(*types)
            else:
                raise exceptions.CriticalError(
                    msg=utils.format_kwstring(_('no support for rule_type: %(rule)s'), rule=str(self.rule_type)))

    def _build_situation(self, situations):
        result = {}
        for situation in situations:
            if ':' in situation:
                keys = situation.split(':')
                result[keys[0].strip()] = keys[1].strip()
            else:
                result[situation.strip()] = 'M'
        for key in result:
            if result[key] == 'M':
                result[key] = True
            else:
                result[key] = False
        return result

    def in_situation(self, situation):
        """
        判断当前场景是否在设定验证的场景内

        :param situation: 场景
        :type situation: string
        :returns: 是/否
        :rtype: bool
        """
        if SITUATION_ALL in self.validate_on:
            return True
        if situation in self.validate_on:
            return True
        return False

    def is_required(self, situation):
        """
        判断当前字段是否必选

        :param situation: 场景
        :type situation: string
        :returns: 是/否
        :rtype: bool
        """
        return self.validate_on.get(situation)

    def validate(self, value):
        """
        验证是否符合条件

        :param value: 输入值
        :type value: any
        :returns: 验证通过返回True，失败返回错误信息
        :rtype: bool/string
        """
        # 可以为null
        if value is None and self.nullable is True:
            return True
        # 不需要校验
        if self.rule is None and self.rule_type is None:
            return True
        if value is None and not self.nullable:
            return _('not nullable')

        # 使用通用validate
        result = self.rule.validate(value)
        if result is True:
            return True
        return self.error_msg % ({'result': result})

    def convert(self, value):
        """
        将输入值转换为指定类型的值

        :param value: 输入值
        :type value: any
        :returns: 转换值
        :rtype: any
        """
        if self.converter:
            return self.converter.convert(value)
        return value

    @classmethod
    def get_clean_data(cls, validate, data, situation, orm_required=False, data_validation=True):
        """
        将数据经过验证，返回符合条件的数据

        :param validate: 验证配置
        :type validate: list
        :param data: 用户传入数据
        :type data: dict
        :param situation: 验证场景，根据create，update传入目前只有['create', 'update']可选
        :type situation: str
        :param orm_required: 是否过滤出符合ORM初始化数据
        :type orm_required: boolean
        :param data_validation: 是否校验数据合理性
        :type data_validation: boolean
        :returns: 通过验证后的干净数据
        :rtype: dict
        :raises: exception.UnknownValidationError, exception.FieldRequired
        """
        clean_data = {}
        for col in validate:
            if col.in_situation(situation):
                field_name = None
                field_name_display = None
                field_value = None
                if col.field in data:
                    field_name = col.field
                    field_name_display = col.field
                    field_value = data[col.field]
                else:
                    for field in col.aliases:
                        if field in data:
                            field_name = col.field
                            field_name_display = field
                            field_value = data[field]
                            break
                if field_name is not None:
                    result = True
                    if data_validation:
                        try:
                            result = col.validate(field_value)
                        except Exception as e:
                            raise exceptions.ValidationError(message=utils.format_kwstring(_(
                                'validate failed on field: %(field)s with data: %(data)s, exception info: %(exception)s'
                            ),
                                                                                           field=field_name_display,
                                                                                           data=data,
                                                                                           exception=str(e)))
                    if result is True:
                        # add clean_data when validate true
                        # and check if user needed orm_required only
                        if (orm_required and col.orm_required) or (not orm_required):
                            clean_data[field_name] = col.convert(field_value)
                    else:
                        raise exceptions.ValidationError(attribute=field_name_display, msg=result)
                else:
                    if col.is_required(situation):
                        raise exceptions.FieldRequired(attribute=col.field)
        return clean_data

    @classmethod
    def any_orm_data(cls, validate, data, situation):
        """
        无需验证数据(但会验证字段是否缺失)，返回orm所需数据
        """
        warnings.warn(
            'ColumnValidator.any_orm_data will be removed in version 1.3.5, use ColumnValidator.get_clean_data instead',
            DeprecationWarning)
        return cls.get_clean_data(validate, data, situation, orm_required=True, data_validation=False)


class ResourceBase(object):
    """
    资源基础操作子类
    继承本类需注意：
    1、覆盖orm_meta、_primary_keys、_default_filter、_default_order、_validate属性
    2、delete默认设置removed(datetime类型)列，若不存在则直接删除，若行为不符合请覆盖delete方法
    """
    # 使用的ORM Model
    orm_meta = None
    # DB连接池对象，若不指定，默认使用defaultPool
    orm_pool = None
    # 是否根据Model中定义的attribute自动改变外键加载策略
    _dynamic_relationship = None
    # 启用动态外键加载策略时，动态加载外键的方式，默认joinedload（取决于全局配置）
    # joinedload 简便，在常用小型查询中响应优于subqueryload
    # subqueryload 在大型复杂(多层外键)查询中响应优于joinedload
    _dynamic_load_method = None
    # get获取信息时，默认根据detail->list->summary层级依次进行取值(取决于全局配置)
    # 如果希望本资源get获取到的第一层级外键是summary级，则设置为True
    _detail_relationship_as_summary = None
    # 当发生数据库异常时，是否抛出带有数据库细节的异常信息，默认False
    # False仅返回数据冲突错误，True可能会暴露数据库表名，字段，约束等细节内容
    _db_exception_detail = False
    # 表对应的主键列，单个主键时，使用字符串，多个联合主键时为字符串列表
    _primary_keys = 'id'
    # 默认过滤查询，应用于每次查询本类资源，此处应当是静态数据，不可被更改
    _default_filter = {}
    # 默认排序，获取默认查询资源是被应用，('name', '+id', '-status'), +表示递增，-表示递减，默认递增
    _default_order = []
    # 数据验证ColumnValidator数组
    # field 字符串，字段名称
    # rule 不同验证不同类型，validator验证参数
    # rule_type 字符串，validator验证类型，支持[regex,email,phone,url,length,integer,float,in,notin, callback]
    #           默认regex（不指定rule也不会生效）,callback回调函数为func(value)
    # validate_on，数组，元素为字符串，['create:M', 'update:M', 'create_or_update:O']，第一个为场景，第二个为是否必须
    # error_msg，字符串，错误提示消息
    # converter，对象实例，converter中的类型，可以自定义
    _validate = []

    def __init__(self,
                 session=None,
                 transaction=None,
                 dbpool=None,
                 dynamic_relationship=None,
                 dynamic_load_method=None):
        def _first_not_none(vals):
            for v in vals:
                if v is not None:
                    return v

        self._pool = dbpool or self.orm_pool or pool.defaultPool
        load_strategies = [dynamic_relationship, self._dynamic_relationship, CONF.dbcrud.dynamic_relationship]
        self._dynamic_relationship = _first_not_none(load_strategies)
        load_methods = [dynamic_load_method, self._dynamic_load_method, CONF.dbcrud.dynamic_load_method]
        self._dynamic_load_method = _first_not_none(load_methods)
        self._detail_relationship_as_summary = CONF.dbcrud.detail_relationship_as_summary if self._detail_relationship_as_summary is None else self._detail_relationship_as_summary
        self._session = session
        self._transaction = transaction

    def _filter_key_mapping(self):
        keys = {
            '$or': or_,
            '$and': and_,
        }
        return keys

    def _get_filter_handler(self, name):
        return filter_wrapper.get_filter(name.lower())

    def _apply_filters(self, query, orm_meta, filters=None, orders=None):
        def _extract_column_visit_name(column):
            '''
            获取列名称
            :param column: 列对象
            :type column: `ColumnAttribute`
            '''
            col_type = getattr(column, 'type', None)
            if col_type:
                return getattr(col_type, '__visit_name__', None)
            return None

        def _handle_filter(expr_wrapper, handler, op, column, value):
            '''
            将具体列+操作+值转化为SQL表达式（SQLAlchmey表达式）
            :param expr_wrapper: 表达式的外包装器，比如一对一的外键列expr_wrapper为relationship.column.has
            :type expr_wrapper: callable
            :param handler: filter wrapper对应的Filter对象
            :type handler: `talos.db.filter_wrapper.Filter`
            :param op: 过滤条件，如None, eq, ne, gt, gte, lt, lte 等
            :type op: str
            :param column: 列对象
            :type column: `ColumnAttribute`
            :param value: 过滤值
            :type value: any
            '''
            expr = None
            func = None
            if op:
                func = getattr(handler, 'op_%s' % op, None)
            else:
                func = getattr(handler, 'op', None)
            if func:
                expr = func(column, value)
                if expr is not None:
                    if expr_wrapper:
                        expr = expr_wrapper(expr)
            return expr

        def _get_expression(filters):
            '''
            将所有filters转换为表达式
            :param filters: 过滤条件字典
            :type filters: dict
            '''
            expressions = []
            unsupported = []
            for name, value in filters.items():
                if name in reserved_keys:
                    _unsupported, expr = _get_key_expression(name, value)
                else:
                    _unsupported, expr = _get_column_expression(name, value)
                unsupported.extend(_unsupported)
                if expr is not None:
                    expressions.append(expr)
            return unsupported, expressions

        def _get_key_expression(name, value):
            '''
            将$and, $or类的组合过滤转换为表达式
            :param name:
            :type name:
            :param value:
            :type value:
            '''
            key_wrapper = reserved_keys[name]
            unsupported = []
            expressions = []
            for key_filters in value:
                _unsupported, expr = _get_expression(key_filters)
                unsupported.extend(_unsupported)
                if expr:
                    expr = and_(*expr)
                    expressions.append(expr)
            if len(expressions) == 0:
                return unsupported, None
            if len(expressions) == 1:
                return unsupported, expressions[0]
            else:
                return unsupported, key_wrapper(*expressions)

        def _get_column_expression(name, value):
            '''
            将列+值过滤转换为表达式
            :param name:
            :type name:
            :param value:
            :type value:
            '''
            expr_wrapper, column = filter_wrapper.column_from_expression(orm_meta, name)
            unsupported = []
            expressions = []
            if column is not None:
                handler = self._get_filter_handler(_extract_column_visit_name(column))
                if isinstance(value, collections.Mapping):
                    for operator, value in value.items():
                        expr = _handle_filter(expr_wrapper, handler, operator, column, value)
                        if expr is not None:
                            expressions.append(expr)
                        else:
                            unsupported.append((name, operator, value))
                else:
                    # op is None
                    expr = _handle_filter(expr_wrapper, handler, None, column, value)
                    if expr is not None:
                        expressions.append(expr)
                    else:
                        unsupported.append((name, None, value))
            if column is None:
                unsupported.insert(0, (name, None, value))
            if len(expressions) == 0:
                return unsupported, None
            if len(expressions) == 1:
                return unsupported, expressions[0]
            else:
                return unsupported, and_(*expressions)

        reserved_keys = self._filter_key_mapping()
        filters = filters or {}
        if filters:
            unsupported, expressions = _get_expression(filters)
            for expr in expressions:
                query = query.filter(expr)
            for idx, error_filter in enumerate(unsupported):
                name, op, value = error_filter
                query = self._unsupported_filter(query, idx, name, op, value)
        orders = orders or []
        if orders:
            for field in orders:
                order = '+'
                if field.startswith('+'):
                    order = '+'
                    field = field[1:]
                elif field.startswith('-'):
                    order = '-'
                    field = field[1:]
                expr_wrapper, column = filter_wrapper.column_from_expression(orm_meta, field)
                # 不支持relationship排序
                if column is not None and expr_wrapper is None:
                    if order == '+':
                        query = query.order_by(column)
                    else:
                        query = query.order_by(column.desc())
        return query

    def _unsupported_filter(self, query, idx, name, op, value):
        '''
        未默认受支持的过滤条件，因talos以前行为为忽略，因此默认返回query不做任何处理，
        此处可以修改并返回query对象更改默认行为
        :param query: SQL查询对象
        :type query: sqlalchemy.query
        :param idx: 第N个不支持的过滤操作(0~N-1)
        :type idx: int
        :param name: 过滤字段
        :type name: str
        :param op: 过滤条件
        :type op: str
        :param value: 过滤值对象
        :type value: str/list/dict
        '''
        # FIXME(wujj): 伪造一个必定为空的查询
        if idx == 0 and CONF.dbcrud.unsupported_filter_as_empty:
            query = query.filter(text('1!=1'))
        return query

    def _dynamic_relationship_load(self, query, orm_meta=None, level=2, parent=None, fallback_raise=True):
        '''
        将query中所有的relationship加载方式更改为动态加载，
        在数据库依赖层级比较深或相互依赖时可提升效率
        
        :param query: SQL查询对象
        :type query: sqlalchemy.query
        :param orm_meta: models类，若不指定，则为当前类的orm_meta
        :type orm_meta: model
        :param level: 初始对象属性层级，3：detail及，2：list级，1：summary级
        :type level: int
        :param parent: 父级load对象
        :type parent: loadstrategy
        :param fallback_raise: 没有在attributes中指定时，默认使用raiseload，False则使用lazyload
        :type fallback_raise: bool
        '''
        level = max(level, 1)
        orm_meta = orm_meta or self.orm_meta
        relationship_cols = orm_meta().list_relationship_columns()
        load_method_map = {
            'joinedload': sqlalchemy.orm.joinedload,
            'subqueryload': sqlalchemy.orm.subqueryload,
            'selectinload': sqlalchemy.orm.selectinload,
            'immediateload': sqlalchemy.orm.immediateload
        }
        level_map = {3: 'get_columns', 2: 'list_columns', 1: 'sum_columns'}
        attributes = getattr(orm_meta(), level_map[level], None)()
        if relationship_cols:
            for rel_col_name in relationship_cols:
                col = getattr(orm_meta, rel_col_name)
                if rel_col_name in attributes:
                    # FIXME: (wujj)remove this, debug msg
                    load_msg = 'dynamic relationship eager load: '
                    load_msg += '%s->' % self.__class__.__name__
                    if parent:
                        for p in parent.path:
                            load_msg += '%s->' % p.property.key
                    load_msg += '%s' % col.property.key
                    LOG.debug(load_msg)
                    parent_next = None
                    if parent:
                        load_method_obj = getattr(parent, self._dynamic_load_method)
                        parent_next = load_method_obj(col)
                        query = query.options(parent_next)
                    else:
                        parent_next = load_method_map[self._dynamic_load_method](col)
                        query = query.options(parent_next)
                    # 当要按照detail级取信息时，需要根据用户指定的detail_relationship_as_summary信息进行动态判定
                    if level == 3 and parent is None and self._detail_relationship_as_summary:
                        next_level = 1
                    else:
                        next_level = level - 1
                    query = self._dynamic_relationship_load(query,
                                                            orm_meta=col.property.entity.entity,
                                                            level=next_level,
                                                            parent=parent_next,
                                                            fallback_raise=fallback_raise)
                else:
                    # FIXME: (wujj)remove this, debug msg
                    load_msg = 'dynamic relationship raise load: '
                    load_msg += '%s->' % self.__class__.__name__
                    if parent:
                        for p in parent.path:
                            load_msg += '%s->' % p.property.key
                    load_msg += '%s' % col.property.key
                    LOG.debug(load_msg)
                    if parent:
                        if fallback_raise:
                            query = query.options(parent.raiseload(col))
                        else:
                            query = query.options(parent.lazyload(col))
                    else:
                        if fallback_raise:
                            query = query.options(sqlalchemy.orm.raiseload(col))
                        else:
                            query = query.options(sqlalchemy.orm.lazyload(col))
        return query

    def _get_query(self,
                   session,
                   orm_meta=None,
                   filters=None,
                   orders=None,
                   joins=None,
                   ignore_default=False,
                   ignore_default_orders=False,
                   dynamic_relationship=None,
                   level_of_relationship=2):
        """获取一个query对象，这个对象已经应用了filter，可以确保查询的数据只包含我们感兴趣的数据，常用于过滤已被删除的数据

        :param session: session对象
        :type session: session
        :param orm_meta: ORM Model, 如果None, 则默认使用self.orm_meta
        :type orm_meta: ORM Model
        :param filters: 简单的等于过滤条件, eg.{'column1': value, 'column2':
        value}，如果None，则默认使用default filter
        :type filters: dict
        :param orders: 排序['+field', '-field', 'field']，+表示递增，-表示递减，不设置默认递增
        :type orders: list
        :param joins: 指定动态join,eg.[{'table': model, 'conditions': [model_a.col_1 == model_b.col_1]}]
        :type joins: list
        :param ignore_default: 是否忽略默认的类指定的filters
        :type ignore_default: bool
        :param ignore_default_orders: 是否忽略默认的类指定的orders
        :type ignore_default_orders: bool
        :param dynamic_relationship: 是否使用动态外键加载方式，None代表依次使用实例指定/类指定/配置指定
        :type dynamic_relationship: bool/None
        :param level_of_relationship: 初始加载的字段级别，1:summary, 2: list, 3: detail
        :type level_of_relationship: int[1,2,3]
        :returns: query对象
        :rtype: query
        :raises: ValueError
        """
        orm_meta = orm_meta or self.orm_meta
        filters = filters or {}
        orders = orders or []
        # orders优先使用用户传递排序
        orders = copy.copy(orders)
        if not ignore_default_orders:
            orders.extend(self.default_order)

        joins = joins or []
        ex_tables = [item['table'] for item in joins]
        tables = list(ex_tables)
        tables.insert(0, orm_meta)
        if orm_meta is None:
            raise exceptions.CriticalError(
                msg=utils.format_kwstring(_('%(name)s.orm_meta can not be None'), name=self.__class__.__name__))
        query = session.query(*tables)
        if len(ex_tables) > 0:
            for item in joins:
                spec_args = [item['table']]
                if len(item['conditions']) > 1:
                    spec_args.append(and_(*item['conditions']))
                else:
                    spec_args.extend(item['conditions'])
                query = query.join(*spec_args, isouter=item.get('isouter', True))
        query = self._apply_filters(query, orm_meta, filters, orders)
        # 如果不是忽略default模式，default_filter必须进行过滤
        if not ignore_default:
            query = self._apply_filters(query, orm_meta, self.default_filter)
        do_dynamic_relationship = self._dynamic_relationship if dynamic_relationship is None else dynamic_relationship
        if do_dynamic_relationship:
            query = self._dynamic_relationship_load(query, orm_meta=orm_meta, level=level_of_relationship)
        return query

    def _apply_primary_key_filter(self, query, rid):
        keys = self.primary_keys
        if utils.is_list_type(keys) and utils.is_list_type(rid):
            if len(rid) != len(keys):
                raise exceptions.CriticalError(msg=utils.format_kwstring(_(
                    'primary key length not match! require: %(length_require)d, input: %(length_input)d'),
                                                                         length_require=len(keys),
                                                                         length_input=len(rid)))
            for idx, val in enumerate(rid):
                query = query.filter(getattr(self.orm_meta, keys[idx]) == val)
        elif utils.is_string_type(keys) and utils.is_list_type(rid) and len(rid) == 1:
            query = query.filter(getattr(self.orm_meta, keys) == rid[0])
        elif utils.is_list_type(keys) and len(keys) == 1:
            query = query.filter(getattr(self.orm_meta, keys[0]) == rid)
        elif utils.is_string_type(keys) and not utils.is_list_type(rid):
            query = query.filter(getattr(self.orm_meta, keys) == rid)
        else:
            raise exceptions.CriticalError(
                msg=utils.format_kwstring(_('primary key not match! require: %(keys)s'), keys=keys))
        return query

    @classmethod
    def validate(cls, data, situation, orm_required=False, validate=True, rule=None):
        """
        验证字段，并返回清洗后的数据

        * 当validate=False，不会对数据进行校验，仅返回ORM需要数据
        * 当validate=True，对数据进行校验，并根据orm_required返回全部/ORM数据

        :param data: 清洗前的数据
        :type data: dict
        :param situation: 当前场景
        :type situation: string
        :param orm_required: 是否ORM需要的数据(ORM即Model表定义的字段)
        :type orm_required: bool
        :param validate: 是否验证规则
        :type validate: bool
        :param rule: 规则配置
        :type rule: dict
        :returns: 返回清洗后的数据
        :rtype: dict
        """
        rule = rule or cls._validate
        if not validate:
            return ColumnValidator.get_clean_data(rule,
                                                  data,
                                                  situation,
                                                  orm_required=orm_required,
                                                  data_validation=False)
        else:
            return ColumnValidator.get_clean_data(rule, data, situation, orm_required=orm_required)

    @property
    def default_filter(self):
        """
        获取默认过滤条件，只读

        :returns: 默认过滤条件
        :rtype: dict
        """
        return copy.deepcopy(self._default_filter) if self._default_filter else {}

    @property
    def default_order(self):
        """
        获取默认排序规则，只读

        :returns: 默认排序规则
        :rtype: list
        """
        return copy.copy(self._default_order)

    @property
    def primary_keys(self):
        """
        获取默认主键列，只读

        :returns: 默认主键列
        :rtype: list
        """
        return copy.copy(self._primary_keys)

    @contextlib.contextmanager
    def transaction(self):
        """
        事务管理上下文, 如果资源初始化时指定使用外部事务，则返回的也是外部事务对象，

        保证事务统一性

        eg.

        with self.transaction() as session:

            self.create()

            self.update()

            self.delete()

            OtherResource(transaction=session).create()
        """
        session = None
        if self._transaction is None:
            try:
                old_transaction = self._transaction
                session = self._pool.transaction()
                self._transaction = session
                yield session
                session.commit()
            except Exception as e:
                LOG.exception(e)
                if session:
                    session.rollback()
                raise e
            finally:
                self._transaction = old_transaction
                if session:
                    session.remove()
        else:
            yield self._transaction

    @classmethod
    def extract_validate_fileds(cls, data):
        '''
        ColumnValidator总是会根据场景进行字段的存在性校验[可选合理性校验]
        本函数提供了不校验场景&存在性&合理性的纯key-value的提取式函数（不推荐）
        '''
        # TODO: (wujj)remove deprecated function
        warnings.warn('ResourceBase.extract_validate_fileds will be removed in version 1.3.5', DeprecationWarning)
        if data is None:
            return None
        new_data = {}
        for col in cls._validate:
            field_name = None
            field_value = None
            if col.field in data:
                field_name = col.field
                field_value = data[col.field]
            else:
                for field in col.aliases:
                    if field in data:
                        field_name = col.field
                        field_value = data[field]
                        break
            if field_name is not None:
                new_data[field_name] = field_value
        return new_data

    @contextlib.contextmanager
    def get_session(self):
        """
        会话管理上下文, 如果资源初始化时指定使用外部会话，则返回的也是外部会话对象
        """
        if self._session is None and self._transaction is None:
            try:
                old_session = self._session
                session = self._pool.get_session()
                self._session = session
                yield session
            finally:
                self._session = old_session
                if session:
                    session.remove()
        elif self._session:
            yield self._session
        else:
            yield self._transaction

    def _addtional_count(self, query, filters):
        return query

    def count(self, filters=None, offset=None, limit=None, hooks=None):
        """
        获取符合条件的记录数量

        :param filters: 过滤条件
        :type filters: dict
        :param offset: 起始偏移量
        :type offset: int
        :param limit: 数量限制
        :type limit: int
        :param hooks: 钩子函数列表，函数形式为func(query, filters)
        :type hooks: list
        :returns: 数量
        :rtype: int
        """
        offset = offset or 0
        with self.get_session() as session:
            query = self._get_query(session,
                                    filters=filters,
                                    orders=[],
                                    ignore_default_orders=True,
                                    dynamic_relationship=False)
            if hooks:
                for h in hooks:
                    query = h(query, filters)
            query = self._addtional_count(query, filters=filters)
            if offset:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            return query.count()

    def _addtional_list(self, query, filters):
        return query

    def list(self, filters=None, orders=None, offset=None, limit=None, hooks=None):
        """
        获取符合条件的记录

        :param filters: 过滤条件
        :type filters: dict
        :param orders: 排序
        :type orders: list
        :param offset: 起始偏移量
        :type offset: int
        :param limit: 数量限制
        :type limit: int
        :param hooks: 钩子函数列表，函数形式为func(query, filters)
        :type hooks: list
        :returns: 记录列表
        :rtype: list
        """
        offset = offset or 0
        with self.get_session() as session:
            query = self._get_query(session, filters=filters, orders=orders)
            if hooks:
                for h in hooks:
                    query = h(query, filters)
            query = self._addtional_list(query, filters)
            if offset:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            results = [rec.to_dict() for rec in query]
            return results

    def get(self, rid):
        """
        获取指定id的资源

        :param rid: 根据不同的资源主键定义，内容也有所不同，单个值或者多个值的元组, 与主键(primary_keys)数量、顺序相匹配
        :type rid: any
        :returns: 资源详细属性
        :rtype: dict
        """
        with self.get_session() as session:
            query = self._get_query(session, level_of_relationship=3)
            query = self._apply_primary_key_filter(query, rid)
            query = query.one_or_none()
            if query:
                result = query.to_detail_dict(child_as_summary=self._detail_relationship_as_summary)
                return result
            else:
                return None

    def _before_create(self, resource, validate):
        pass

    def _addtional_create(self, session, resource, created):
        pass

    def create(self, resource, validate=True, detail=True):
        """
        创建新资源

        :param resource: 资源的属性值
        :type resource: dict
        :param validate: 是否验证
        :type validate: bool
        :returns: 创建的资源属性值
        :rtype: dict
        """
        validate = False if not self._validate else validate
        self._before_create(resource, validate)
        # 不校验 => orm，extra
        # 校验=> orm, extra
        # 为了避免重复调用校验器，因此获取一次全量字段，然后进行一次orm字段筛选即可
        all_fields = resource
        orm_fields = resource
        if validate:
            all_fields = self.validate(resource, utils.get_function_name(), orm_required=False, validate=True)
            orm_fields = self.validate(resource, utils.get_function_name(), orm_required=True, validate=False)
        with self.transaction() as session:
            try:
                # pylint:disable=not-callable
                item = self.orm_meta(**orm_fields)
                session.add(item)
                session.flush()
                self._addtional_create(session, all_fields, item.to_dict())
                session.refresh(item)
                if detail:
                    return item.to_detail_dict(child_as_summary=self._detail_relationship_as_summary)
                return item.to_dict()
            except sqlalchemy.exc.IntegrityError as e:
                # e.message.split('DETAIL:  ')[1]
                LOG.exception(e)
                if self._db_exception_detail:
                    raise exceptions.ConflictError(message=str(e))
                raise exceptions.ConflictError(msg=_('can not meet the constraints'))
            except sqlalchemy.exc.SQLAlchemyError as e:
                LOG.exception(e)
                if self._db_exception_detail:
                    raise exceptions.DBError(message=str(e))
                raise exceptions.DBError(msg=_('unknown db error'))

        # with statement will commit or rollback for user

    def _before_update(self, rid, resource, validate):
        pass

    def _addtional_update(self, session, rid, resource, before_updated, after_updated):
        pass

    def update(self, rid, resource, filters=None, validate=True, detail=True):
        """
        更新资源

        :param rid: 根据不同的资源主键定义，内容也有所不同，单个值或者多个值的元组, 与主键(primary_keys)数量、顺序相匹配
        :type rid: any
        :param resource: 更新的属性以及值，patch的概念，如果不更新这个属性，则无需传入这个属性以及值
        :type resource: dict
        :param validate: 是否验证
        :type validate: bool
        :returns: 更新后的资源属性值
        :rtype: dict
        """
        validate = False if not self._validate else validate
        self._before_update(rid, resource, validate)
        # 不校验 => orm，extra
        # 校验=> orm, extra
        # 为了避免重复调用校验器，因此获取一次全量字段，然后进行一次orm字段筛选即可
        all_fields = resource
        orm_fields = resource
        if validate:
            all_fields = self.validate(resource, utils.get_function_name(), orm_required=False, validate=True)
            orm_fields = self.validate(resource, utils.get_function_name(), orm_required=True, validate=False)
        with self.transaction() as session:
            try:
                if detail:
                    query = self._get_query(session, ignore_default_orders=True, level_of_relationship=3)
                else:
                    query = self._get_query(session, ignore_default_orders=True)
                query = self._apply_primary_key_filter(query, rid)
                if filters:
                    query = self._apply_filters(query, self.orm_meta, filters)
                record = query.one_or_none()
                before_update = None
                after_update = None
                if record is not None:
                    if detail:
                        before_update = record.to_detail_dict(child_as_summary=self._detail_relationship_as_summary)
                    else:
                        before_update = record.to_dict()
                    if orm_fields:
                        record.update(orm_fields)
                    session.flush()
                    self._addtional_update(session, rid, all_fields, before_update, after_update)
                    session.refresh(record)
                    if detail:
                        after_update = record.to_detail_dict(child_as_summary=self._detail_relationship_as_summary)
                    else:
                        after_update = record.to_dict()
                else:
                    after_update = before_update
                return before_update, after_update
            except sqlalchemy.exc.IntegrityError as e:
                # e.message.split('DETAIL:  ')[1]
                LOG.exception(e)
                if self._db_exception_detail:
                    raise exceptions.ConflictError(message=str(e))
                raise exceptions.ConflictError(msg=_('can not meet the constraints'))
            except sqlalchemy.exc.SQLAlchemyError as e:
                LOG.exception(e)
                if self._db_exception_detail:
                    raise exceptions.DBError(message=str(e))
                raise exceptions.DBError(msg=_('unknown db error'))

    def _before_delete(self, rid):
        pass

    def _addtional_delete(self, session, resource):
        pass

    def delete(self, rid, filters=None, detail=True):
        """
        删除资源

        :param rid: 根据不同的资源主键定义，内容也有所不同，单个值或者多个值的元组, 与主键(primary_keys)数量、顺序相匹配
        :type rid: any
        :returns: 返回影响条目数量
        :rtype: int
        """
        self._before_delete(rid)
        with self.transaction() as session:
            try:
                if detail:
                    query = self._get_query(session, orders=[], ignore_default_orders=True, level_of_relationship=3)
                else:
                    query = self._get_query(session, orders=[], ignore_default_orders=True)
                query = self._apply_primary_key_filter(query, rid)
                if filters:
                    query = self._apply_filters(query, self.orm_meta, filters)
                record = query.one_or_none()
                resource = None
                count = 0
                if record is not None:
                    if detail:
                        resource = record.to_detail_dict(child_as_summary=self._detail_relationship_as_summary)
                    else:
                        resource = record.to_dict()
                count = query.delete(synchronize_session=False)
                session.flush()
                self._addtional_delete(session, resource)
                return count, [resource]
            except sqlalchemy.exc.IntegrityError as e:
                # e.message.split('DETAIL:  ')[1]
                LOG.exception(e)
                if self._db_exception_detail:
                    raise exceptions.ConflictError(message=str(e))
                raise exceptions.ConflictError(msg=_('can not meet the constraints'))
            except sqlalchemy.exc.SQLAlchemyError as e:
                LOG.exception(e)
                if self._db_exception_detail:
                    raise exceptions.DBError(message=str(e))
                raise exceptions.DBError(msg=_('unknown db error'))

    def _before_delete_all(self, filters):
        pass

    def _addtional_delete_all(self, session, resources):
        pass

    def delete_all(self, filters=None):
        """
        根据条件删除资源

        :param rid: 根据不同的资源主键定义，内容也有所不同，单个值或者多个值的元组, 与主键(primary_keys)数量、顺序相匹配
        :type rid: any
        :returns: 返回影响条目数量
        :rtype: int
        """
        filters = filters or []
        self._before_delete_all(filters)
        with self.transaction() as session:
            try:
                query = self._get_query(session, orders=[], ignore_default_orders=True, filters=filters)
                records = query.all()
                count = 0
                records = [rec.to_dict() for rec in records]
                # FIXED, 数据已经通过.all()返回，此时不能使用synchronize_session的默认值'evaluate'，可以为fetch或False
                # 因数据已被取回，所以此处直接False性能最高
                count = query.delete(synchronize_session=False)
                session.flush()
                self._addtional_delete_all(session, records)
                return count, records
            except sqlalchemy.exc.IntegrityError as e:
                # e.message.split('DETAIL:  ')[1]
                LOG.exception(e)
                if self._db_exception_detail:
                    raise exceptions.ConflictError(message=str(e))
                raise exceptions.ConflictError(msg=_('can not meet the constraints'))
            except sqlalchemy.exc.SQLAlchemyError as e:
                LOG.exception(e)
                if self._db_exception_detail:
                    raise exceptions.DBError(message=str(e))
                raise exceptions.DBError(msg=_('unknown db error'))
