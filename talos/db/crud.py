# coding=utf-8
"""
本模块提供DB的CRUD封装

"""

from __future__ import absolute_import

import contextlib
import copy
import datetime
import logging

import six
from sqlalchemy import and_
import sqlalchemy.exc
from sqlalchemy.sql.expression import BinaryExpression
from sqlalchemy.sql.sqltypes import _type_map

from talos.core import config
from talos.core import exceptions
from talos.core import utils
from talos.core.i18n import _
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

    def __init__(self, **kwargs):
        """
        初始化
        """
        self.field = kwargs.pop('field')
        self.rule = kwargs.pop('rule', None)
        self.rule_type = kwargs.pop('rule_type', None)
        self.validate_on = kwargs.pop('validate_on', None)
        self.error_msg = kwargs.pop('error_msg', '%(result)s')
        self.converter = kwargs.pop('converter', None)
        self.orm_required = kwargs.pop('orm_required', True)
        self.aliases = kwargs.pop('aliases', [])
        self.nullable = kwargs.pop('nullable', False)
        # 用户不指定，默认全部场景
        if self.validate_on is None:
            self.validate_on = [VALIDATE_ON_ALL]
        self.validate_on = self._build_situation(self.validate_on)
        if self.rule is None and self.rule_type is None:
            pass
        elif not isinstance(self.rule, validator.NullValidator):
            if self.rule_type == 'callback':
                if not callable(self.rule):
                    raise exceptions.CriticalError(msg=_('rule callback function malformat,eg: fucntion(value)'))
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
        if value is None and self.nullable is True:
            return True
        if self.rule is None and self.rule_type is None:
            return True
        elif self.rule_type == 'callback':
            # 如果是用户指定callback，直接调用
            if self.rule(value) is True:
                return True
        else:
            # 否则使用通用validator
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

    def _filters_merge(self, filters, default_filters):
        keys = set(filters.keys()) & set(default_filters.keys())
        for key in keys:
            val = filters[key]
            other_val = default_filters.pop(key)
            if isinstance(val, dict) and isinstance(other_val, dict):
                val.update(other_val)
            elif isinstance(val, dict) and not isinstance(other_val, dict):
                if utils.is_list_type(other_val):
                    val['in'] = other_val
                else:
                    val['eq'] = other_val
            elif not isinstance(val, dict) and isinstance(other_val, dict):
                if utils.is_list_type(val):
                    other_val['in'] = val
                else:
                    other_val['eq'] = val
                filters[key] = other_val
            else:
                nval = {}
                if utils.is_list_type(val):
                    nval['in'] = val
                else:
                    nval['eq'] = val
                if utils.is_list_type(other_val):
                    nval['in'] = other_val
                else:
                    nval['eq'] = other_val
                filters[key] = nval
        filters.update(default_filters)
        return filters

    def _apply_filters(self, query, orm_meta, filters=None, orders=None):
        def cast_from_python_value(column, value):
            """
            将python类型值转换为SQLAlchemy类型值

            :param column:
            :type column:
            :param value:
            :type value:
            """
            cast_to = _type_map.get(type(value), None)
            if cast_to is None:
                column = column.astext
            else:
                column = column.astext.cast(cast_to)
            return column
        filters = filters or {}
        orders = orders or []
        for name, value in filters.items():
            column = self._build_column_from_field(orm_meta, name)
            if column is not None:
                if utils.is_list_type(value) and len(value) > 0:
                    if isinstance(column, BinaryExpression):
                        column = cast_from_python_value(column, value[0])
                    query = query.filter(column.in_(value))
                elif isinstance(value, dict):
                    for operator, value in value.items():
                        # list should cast from element type
                        if operator == 'in' and len(value) > 0:
                            if isinstance(column, BinaryExpression):
                                column = cast_from_python_value(column, value[0])
                            query = query.filter(column.in_(value))
                            continue
                        elif operator == 'nin' and len(value) > 0:
                            if isinstance(column, BinaryExpression):
                                column = cast_from_python_value(column, value[0])
                            query = query.filter(column.notin_(value))
                            continue
                        # cast from value type
                        if isinstance(column, BinaryExpression):
                            column = cast_from_python_value(column, value)
                        if operator == 'eq':
                            query = query.filter(column == value)
                        elif operator == 'ne':
                            query = query.filter(column != value)
                        elif operator == 'lt':
                            query = query.filter(column < value)
                        elif operator == 'lte':
                            query = query.filter(column <= value)
                        elif operator == 'gt':
                            query = query.filter(column > value)
                        elif operator == 'gte':
                            query = query.filter(column >= value)
                        elif operator == 'like':
                            query = query.filter(column.like('%%%s%%' % value))
                        elif operator == 'istarts':
                            query = query.filter(column.like('%s%%' % value))
                        elif operator == 'iends':
                            query = query.filter(column.like('%%%s' % value))
                        elif operator == 'ilike':
                            query = query.filter(column.ilike('%%%s%%' % value))
                        elif operator == 'starts':
                            query = query.filter(column.ilike('%s%%' % value))
                        elif operator == 'ends':
                            query = query.filter(column.ilike('%%%s' % value))
                        else:
                            pass
                else:
                    if isinstance(column, BinaryExpression):
                        column = cast_from_python_value(column, value)
                    query = query.filter(column == value)
        for name in orders:
            order = '+'
            field = name
            if field.startswith('+'):
                order = '+'
                field = field[1:]
            elif field.startswith('-'):
                order = '-'
                field = field[1:]
            else:
                pass
            column_attr = getattr(orm_meta, field, None)
            if column_attr:
                if order == '+':
                    query = query.order_by(column_attr)
                else:
                    query = query.order_by(column_attr.desc())
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
            self._filters_merge(filters, self.default_filter)
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

    def _build_column_from_field(self, table, field):
        if '.' in field:
            cut_fields = field.split('.')
            column = getattr(table, cut_fields.pop(0), None)
            if column:
                for cut_field in cut_fields:
                    column = column[cut_field]
        else:
            column = getattr(table, field, None)
        return column

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

            resource(transaction=session).add()

            resource(transaction=session).update()

            resource(transaction=session).delete()
        """
        session = None
        if self._transaction is None:
            try:
                session = self._pool.transaction()
                yield session
                session.commit()
            except Exception as e:
                LOG.exception(e)
                if session:
                    session.rollback()
                raise e
            finally:
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
                session = self._pool.get_session()
                yield session
            finally:
                if session:
                    session.remove()
        elif self._session:
            yield self._session
        else:
            yield self._transaction

    def _addtional_count(self, query, filters):
        return query

    def count(self, filters=None, offset=None, limit=None):
        """
        获取符合条件的记录数量

        :param filters: 过滤条件
        :type filters: dict
        :param offset: 起始偏移量
        :type offset: int
        :param limit: 数量限制
        :type limit: int
        :returns: 数量
        :rtype: int
        """
        offset = offset or 0
        with self.get_session() as session:
            query = self._get_query(session, filters=filters, orders=[])
            query = self._addtional_count(query, filters=filters)
            if offset:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            return query.count()

    def _addtional_list(self, query, filters):
        return query

    def list(self, filters=None, orders=None, offset=None, limit=None):
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
        :returns: 记录列表
        :rtype: list
        """
        offset = offset or 0
        with self.get_session() as session:
            query = self._get_query(session, filters=filters, orders=orders)
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

    def _addtional_update(self, session, rid, resource, updated):
        pass

    def update(self, rid, resource, validate=True, detail=True):
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
                    self._addtional_update(session, rid, all_fields, after_update)
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

    def delete(self, rid):
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
                record = query.one_or_none()
                resource = None
                count = 0
                if record is not None:
                    resource = record.to_dict()
                if getattr(self.orm_meta, 'removed', None) is not None:
                    if record is not None:
                        count = query.update({'removed': datetime.datetime.now()})
                else:
                    count = query.delete()
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
                if len(records) > 0:
                    if getattr(self.orm_meta, 'removed', None) is not None:
                        count = query.update({'removed': datetime.datetime.now()})
                    else:
                        count = query.delete()
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
