# coding=utf-8
"""
fitcloud.db.crud
~~~~~~~~~~~~~~~

本模块提供DB的CRUD封装

"""

from __future__ import absolute_import


from fitcloud.core import utils
from sqlalchemy.sql.expression import BinaryExpression
from sqlalchemy.sql.sqltypes import _type_map


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


class Filter(object):
    def op(self, query, column, value):
        if utils.is_list_type(value):
            if len(value) == 0:
                return query
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value[0])
            query = query.filter(column.in_(value))
        else:
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value)
            query = query.filter(column == value)
        return query

    def op_in(self, query, column, value):
        if utils.is_list_type(value):
            if len(value) == 0:
                return query
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value[0])
            query = query.filter(column.in_(value))
        else:
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value)
            query = query.filter(column == value)
        return query

    def op_nin(self, query, column, value):
        if utils.is_list_type(value):
            if len(value) == 0:
                return query
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value[0])
            query = query.filter(column.notin_(value))
        else:
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value)
            query = query.filter(column != value)
        return query

    def op_eq(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column == value)
        return query

    def op_ne(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column != value)
        return query

    def op_lt(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column < value)
        return query

    def op_lte(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column <= value)
        return query

    def op_gt(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column > value)
        return query

    def op_gte(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column >= value)
        return query

    def op_like(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column.like('%%%s%%' % value))
        return query

    def op_starts(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column.like('%s%%' % value))
        return query

    def op_ends(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column.like('%%%s' % value))
        return query

    def op_ilike(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column.ilike('%%%s%%' % value))
        return query

    def op_istarts(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column.ilike('%s%%' % value))
        return query

    def op_iends(self, query, column, value):
        if isinstance(column, BinaryExpression):
            column = cast_from_python_value(column, value)
        query = query.filter(column.ilike('%%%s' % value))
        return query


class FilterNetwork(object):
    def op(self, query, column, value):
        if utils.is_list_type(value):
            if len(value) == 0:
                return query
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value[0])
            filters = column.op("<<=")(value[0])
            for index in range(1, len(value)):
                filters |= column.op("<<=")(value[index])
            query = query.filter(filters)
        else:
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value)
            query = query.filter(column == value)
        return query

    def op_in(self, query, column, value):
        if utils.is_list_type(value):
            if len(value) == 0:
                return query
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value[0])
            filters = column.op("<<=")(value[0])
            for index in range(1, len(value)):
                filters |= column.op("<<=")(value[index])
            query = query.filter(filters)
        else:
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value)
            query = query.filter(column.op("<<=")(value))
        return query

    def op_nin(self, query, column, value):
        if utils.is_list_type(value):
            if len(value) == 0:
                return query
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value[0])
            filters = ~column.op("<<=")(value[0])
            for index in range(1, len(value)):
                filters &= ~column.op("<<=")(value[index])
            query = query.filter(filters)
        else:
            if isinstance(column, BinaryExpression):
                column = cast_from_python_value(column, value)
            query = query.filter(~column.op("<<=")(value))
        return query