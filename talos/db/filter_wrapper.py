# coding=utf-8
"""
talos.db.filter_wrapper
~~~~~~~~~~~~~~~~~~~~~~~

本模块提供DB的filter过滤封装

"""

from __future__ import absolute_import

import re

from sqlalchemy.sql.expression import BinaryExpression
from sqlalchemy.sql.sqltypes import _type_map

from talos.core import utils

RE_CIDR = re.compile(r'^(\d{1,3}\.){0,3}\d{1,3}/\d{1,2}$')
RE_IP = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
RE_CIDR_LIKE = re.compile(r'^(\d{1,3}|\d{1,3}\.\d{1,3}|\d{1,3}\.\d{1,3}\.\d{1,3})(\.)?(/\d{1,2})?$')


def merge(filters, filters_to_merge):
    """
    将filters_to_merage合并到filters中

    :param filters: 待合并的filters(注：内容会被修改并返回)
    :type filters: dict
    :param filters_to_merge: 待合并的filters(注：内容会被修改)
    :type filters_to_merge: dict
    """
    keys = set(filters.keys()) & set(filters_to_merge.keys())
    for key in keys:
        val = filters[key]
        other_val = filters_to_merge.pop(key)
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
    filters.update(filters_to_merge)
    return filters


def column_from_expression(table, expression):
    if '.' in expression:
        fields = expression.split('.')
        column = getattr(table, fields.pop(0), None)
        if column:
            for field in fields:
                column = column[field]
    else:
        column = getattr(table, expression, None)
    return column


def cast(column, value):
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


class Filter(object):

    def make_empty_query(self, query, column):
        query = query.filter(column == None)
        query = query.filter(column != None)
        return query

    def op(self, query, column, value):
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            query = query.filter(column.in_(tuple(value)))
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            query = query.filter(column == value)
        return query

    def op_in(self, query, column, value):
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            query = query.filter(column.in_(tuple(value)))
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            query = query.filter(column == value)
        return query

    def op_nin(self, query, column, value):
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            query = query.filter(column.notin_(tuple(value)))
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            query = query.filter(column != value)
        return query

    def op_eq(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column == value)
        return query

    def op_ne(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column != value)
        return query

    def op_lt(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column < value)
        return query

    def op_lte(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column <= value)
        return query

    def op_gt(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column > value)
        return query

    def op_gte(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column >= value)
        return query

    def op_like(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.like('%%%s%%' % value))
        return query

    def op_starts(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.like('%s%%' % value))
        return query

    def op_ends(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.like('%%%s' % value))
        return query
    
    def op_notlike(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.notlike('%%%s%%' % value))
        return query

    def op_ilike(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.ilike('%%%s%%' % value))
        return query

    def op_istarts(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.ilike('%s%%' % value))
        return query

    def op_iends(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.ilike('%%%s' % value))
        return query
    
    def op_inotlike(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.notilike('%%%s%%' % value))
        return query
    
    def op_nnull(self, query, column, value):
        query = query.filter(column != None)
        return query
    
    def op_null(self, query, column, value):
        query = query.filter(column == None)
        return query


class FilterNetwork(Filter):
    '''
    用于PG数据库， 重写IP，CIDR的范围查询，不支持like操作
    '''

    def _fix_cidr(self, value):
        """
        fix_cidr('192')
        fix_cidr('192.')
        fix_cidr('192.1')
        fix_cidr('192.1.') 
        fix_cidr('192.1.1')
        fix_cidr('192.1.1.')
        fix_cidr('192.1.1.1')
        fix_cidr('192.1.1.1.')
        fix_cidr('192.1.1.1.5/32')
        fix_cidr('192/24')
        fix_cidr('192./16')
        fix_cidr('192.1.1/8')
        fix_cidr('192.1.1.1/32')
        fix_cidr('aaa.1./16')
        fix_cidr('aaa/8.1./16')
        fix_cidr('1/8.1./16')
        """
        try:
            prefix_len = 0
            prefix_value = value
            if '/' in value:
                prefix_value, prefix_len = value.split('/', 1)
                prefix_len = int(prefix_len)
            if prefix_len > 32:
                return None
                # raise ValueError("cidr prefix length larger than 32")
            slice_values = prefix_value.split('.')
            slice_len = len([item for item in slice_values if item])
            if prefix_len > 8 * slice_len:
                return None
                # raise ValueError("cidr prefix length larger than expect %(expected)s" % {'expected': 8 * slice_len})
            if RE_CIDR.match(value):
                return value
            elif RE_IP.match(value):
                return value + '/32'
            else:
                if not RE_CIDR_LIKE.match(value):
                    return None
                    # raise ValueError("not a cidr like value")
                return value + '/' + str(8 * slice_len)
        except ValueError:
            return None

    def validate_cidr(self, value):
        if utils.is_list_type(value):
            new_cidrs = []
            for v in value:
                new_cidr = self._fix_cidr(v)
                if new_cidr is not None:
                    new_cidrs.append(new_cidr)
            return new_cidrs
        else:
            return self._fix_cidr(value)

    def op(self, query, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(query, column)
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            filters = column.op("<<=")(value[0])
            for index in range(1, len(value)):
                filters |= column.op("<<=")(value[index])
            query = query.filter(filters)
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            query = query.filter(column == value)
        return query

    def op_in(self, query, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(query, column)
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            filters = column.op("<<=")(value[0])
            for index in range(1, len(value)):
                filters |= column.op("<<=")(value[index])
            query = query.filter(filters)
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            query = query.filter(column.op("<<=")(value))
        return query

    def op_nin(self, query, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(query, column)
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            filters = ~column.op("<<=")(value[0])
            for index in range(1, len(value)):
                filters &= ~column.op("<<=")(value[index])
            query = query.filter(filters)
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            query = query.filter(~column.op("<<=")(value))
        return query

    def op_like(self, query, column, value):
        return query

    def op_starts(self, query, column, value):
        return query

    def op_ends(self, query, column, value):
        return query

    def op_ilike(self, query, column, value):
        return query

    def op_istarts(self, query, column, value):
        return query

    def op_iends(self, query, column, value):
        return query

    def op_lt(self, query, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(query, column)
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.op("<<")(value))
        return query

    def op_lte(self, query, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(query, column)
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.op("<<=")(value))
        return query

    def op_gt(self, query, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(query, column)
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.op(">>")(value))
        return query

    def op_gte(self, query, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(query, column)
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        query = query.filter(column.op(">>=")(value))
        return query


class FilterNumber(Filter):
    '''
    数字类型不支持like操作
    '''

    def op_like(self, query, column, value):
        return query

    def op_starts(self, query, column, value):
        return query

    def op_ends(self, query, column, value):
        return query

    def op_ilike(self, query, column, value):
        return query

    def op_istarts(self, query, column, value):
        return query

    def op_iends(self, query, column, value):
        return query


FilterDateTime = FilterNumber
