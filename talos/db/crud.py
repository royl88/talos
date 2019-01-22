# coding=utf-8
"""
本模块提供DB的CRUD封装

"""

from __future__ import absolute_import

import collections
import contextlib
import copy
import logging

import six
from sqlalchemy import and_, or_
import sqlalchemy.exc

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
        self.aliases = aliases
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
                raise exceptions.CriticalError(msg=utils.format_kwstring(
                    _('no support for rule_type: %(rule)s'), rule=str(self.rule_type)))

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

    @staticmethod
    def get_clean_data(validate, data, situation, orm_required=False):
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
                    try:
                        result = col.validate(field_value)
                    except Exception as e:
                        raise exceptions.CriticalError(msg=utils.format_kwstring(
                            _('validate failed on field: %(field)s with data: %(data)s, exception info: %(exception)s'),
                            field=field_name_display,
                            data=data,
                            exception=str(e)))
                    if result is True:
                        if not (orm_required and not col.orm_required):
                            clean_data[field_name] = col.convert(field_value)
                    else:
                        raise exceptions.ValidationError(attribute=field_name_display, msg=result)
                else:
                    if col.is_required(situation):
                        raise exceptions.FieldRequired(attribute=col.field)
        return clean_data

    @staticmethod
    def any_orm_data(validate, data, situation):
        """
        无需验证数据(但会验证字段是否缺失)，返回orm所需数据

        :param validate: 验证配置
        :type validate: list
        :param data: 用户传入数据
        :type data: dict
        :param situation: 验证场景，根据create，update传入目前只有['create', 'update']可选
        :type situation: str
        :returns: 通过过滤后的干净数据
        :rtype: dict
        :raises: exception.FieldRequired
        """
        clean_data = {}
        for col in validate:
            if col.in_situation(situation):
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
                    if col.orm_required:
                        clean_data[field_name] = col.convert(field_value)
                else:
                    if col.is_required(situation):
                        raise exceptions.FieldRequired(attribute=col.field)
        return clean_data


class ResourceBase(object):
    """
    资源基础操作子类
    继承本类需注意：
    1、覆盖orm_meta、_primary_keys、_default_filter、_default_order、_validate属性
    2、delete默认设置removed(datetime类型)列，若不存在则直接删除，若行为不符合请覆盖delete方法
    """
    # 使用的ORM Model
    orm_meta = None
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

    def __init__(self, session=None, transaction=None):
        self._pool = None
        self._session = session
        self._transaction = transaction
        if session is None and transaction is None:
            self._pool = pool.POOL

    def _filter_hander_mapping(self):
        handlers = {
            'INET': filter_wrapper.FilterNetwork(),
            'CIDR': filter_wrapper.FilterNetwork(),
            'small_integer': filter_wrapper.FilterNumber(),
            'integer': filter_wrapper.FilterNumber(),
            'big_integer': filter_wrapper.FilterNumber(),
            'numeric': filter_wrapper.FilterNumber(),
            'float': filter_wrapper.FilterNumber(),
            'date': filter_wrapper.FilterDateTime(),
            'datetime': filter_wrapper.FilterDateTime(),
        }
        return handlers
    
    def _filter_key_mapping(self):
        keys = {
            '$or': or_,
            '$and': and_,
        }
        return keys

    def _get_filter_handler(self, name):
        handlers = self._filter_hander_mapping()
        return handlers.get(name, filter_wrapper.Filter())

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
                if expr is not None:
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
                return unsupported, and_(expressions)

        reserved_keys = self._filter_key_mapping()
        filters = filters or {}
        orders = orders or []
        unsupported, expressions = _get_expression(filters)
        for expr in expressions:
            query = query.filter(expr)
        for idx, error_filter in enumerate(unsupported):
            name, op, value = error_filter
            self._unsupported_filter(query, idx, name, op, value)
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
        :param idx: 第N个不支持的过滤操作
        :type idx: int
        :param name: 过滤字段
        :type name: str
        :param op: 过滤条件
        :type op: str
        :param value: 过滤值对象
        :type value: str/list/dict
        '''
        return query

    def _get_query(self, session, orm_meta=None, filters=None, orders=None, joins=None, ignore_default=False):
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
        :returns: query对象
        :rtype: query
        :raises: ValueError
        """
        orm_meta = orm_meta or self.orm_meta
        filters = filters or {}
        filters = copy.copy(filters)
        if not ignore_default:
            filter_wrapper.merge(filters, self.default_filter)
        if not ignore_default:
            orders = self.default_order if orders is None else orders
        else:
            orders = orders or []
        orders = copy.copy(orders)
        joins = joins or []
        ex_tables = [item['table'] for item in joins]
        tables = list(ex_tables)
        tables.insert(0, orm_meta)
        if orm_meta is None:
            raise exceptions.CriticalError(msg=utils.format_kwstring(
                _('%(name)s.orm_meta can not be None'), name=self.__class__.__name__))
        query = session.query(*tables)
        if len(ex_tables) > 0:
            for item in joins:
                spec_args = [item['table']]
                if len(item['conditions']) > 1:
                    spec_args.append(and_(*item['conditions']))
                else:
                    spec_args.extend(item['conditions'])
                query = query.join(*spec_args,
                                   isouter=item.get('isouter', True))
        query = self._apply_filters(query, orm_meta, filters, orders)
        return query

    def _apply_primary_key_filter(self, query, rid):
        keys = self.primary_keys
        if utils.is_list_type(keys) and utils.is_list_type(rid):
            if len(rid) != len(keys):
                raise exceptions.CriticalError(msg=utils.format_kwstring(
                    _('primary key length not match! require: %(length_require)d, input: %(length_input)d'), length_require=len(keys), length_input=len(rid)))
            for idx, val in enumerate(rid):
                query = query.filter(getattr(self.orm_meta, keys[idx]) == val)
        elif utils.is_string_type(keys) and utils.is_list_type(rid) and len(rid) == 1:
            query = query.filter(getattr(self.orm_meta, keys) == rid[0])
        elif utils.is_list_type(keys) and len(keys) == 1:
            query = query.filter(getattr(self.orm_meta, keys[0]) == rid)
        elif utils.is_string_type(keys) and not utils.is_list_type(rid):
            query = query.filter(getattr(self.orm_meta, keys) == rid)
        else:
            raise exceptions.CriticalError(msg=utils.format_kwstring(
                _('primary key not match! require: %(keys)s'), keys=keys))
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
            return ColumnValidator.any_orm_data(rule, data, situation)
        else:
            return ColumnValidator.get_clean_data(rule, data, situation, orm_required=orm_required)

    @property
    def default_filter(self):
        """
        获取默认过滤条件，只读

        :returns: 默认过滤条件
        :rtype: dict
        """
        return copy.deepcopy(self._default_filter)

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
        if data is None:
            return None
        new_data = {}
        for validator in cls._validate:
            if validator.field in data:
                new_data[validator.field] = data[validator.field]
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
            query = self._get_query(session, filters=filters, orders=[])
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
            query = self._get_query(session)
            query = self._apply_primary_key_filter(query, rid)
            query = query.one_or_none()
            if query:
                result = query.to_detail_dict()
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
        if validate:
            orm_fields = self.validate(resource, utils.get_function_name(), orm_required=True, validate=True)
        else:
            orm_fields = resource
        with self.transaction() as session:
            try:
                item = self.orm_meta(**orm_fields)
                session.add(item)
                session.flush()
                if validate:
                    all_fields = self.validate(resource, utils.get_function_name(),
                                               orm_required=False, validate=True)
                else:
                    all_fields = resource
                self._addtional_create(session, all_fields, item.to_dict())
                if detail:
                    return item.to_detail_dict()
                else:
                    return item.to_dict()
            except sqlalchemy.exc.IntegrityError as e:
                # e.message.split('DETAIL:  ')[1]
                LOG.exception(e)
                raise exceptions.ConflictError(msg=_('can not meet the constraints'))
            except sqlalchemy.exc.SQLAlchemyError as e:
                LOG.exception(e)
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
        if validate:
            orm_fields = self.validate(resource, utils.get_function_name(), orm_required=True, validate=True)
        else:
            orm_fields = resource
        with self.transaction() as session:
            try:
                query = self._get_query(session)
                query = self._apply_primary_key_filter(query, rid)
                if filters:
                    query = self._apply_filters(query, self.orm_meta, filters)
                record = query.one_or_none()
                before_update = None
                after_update = None
                if record is not None:
                    if detail:
                        before_update = record.to_detail_dict()
                    else:
                        before_update = record.to_dict()
                    if orm_fields:
                        record.update(orm_fields)
                    session.flush()
                    if validate:
                        all_fields = self.validate(resource, utils.get_function_name(),
                                                   orm_required=False, validate=True)
                    else:
                        all_fields = resource
                    if detail:
                        after_update = record.to_detail_dict()
                    else:
                        after_update = record.to_dict()
                    self._addtional_update(session, rid, all_fields, before_update, after_update)
                else:
                    after_update = before_update
                return before_update, after_update
            except sqlalchemy.exc.IntegrityError as e:
                # e.message.split('DETAIL:  ')[1]
                LOG.exception(e)
                raise exceptions.ConflictError(msg=_('can not meet the constraints'))
            except sqlalchemy.exc.SQLAlchemyError as e:
                LOG.exception(e)
                raise exceptions.DBError(msg=_('unknown db error'))

    def _before_delete(self, rid):
        pass

    def _addtional_delete(self, session, resource):
        pass

    def delete(self, rid, filters=None):
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
                query = self._get_query(session, orders=[])
                query = self._apply_primary_key_filter(query, rid)
                if filters:
                    query = self._apply_filters(query, self.orm_meta, filters)
                record = query.one_or_none()
                resource = None
                count = 0
                if record is not None:
                    resource = record.to_dict()
                count = query.delete(synchronize_session=False)
                session.flush()
                self._addtional_delete(session, resource)
                return count, [resource]
            except sqlalchemy.exc.IntegrityError as e:
                # e.message.split('DETAIL:  ')[1]
                LOG.exception(e)
                raise exceptions.ConflictError(msg=_('can not meet the constraints'))
            except sqlalchemy.exc.SQLAlchemyError as e:
                LOG.exception(e)
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
                query = self._get_query(session, orders=[], filters=filters)
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
                raise exceptions.ConflictError(msg=_('can not meet the constraints'))
            except sqlalchemy.exc.SQLAlchemyError as e:
                LOG.exception(e)
                raise exceptions.DBError(msg=_('unknown db error'))
