# coding=utf-8
"""
talos.db.filter_wrapper
~~~~~~~~~~~~~~~~~~~~~~~

本模块提供DB的filter过滤封装

"""

from __future__ import absolute_import

import re

from sqlalchemy.orm import attributes
from sqlalchemy.orm import properties
from sqlalchemy.orm import relationships
from sqlalchemy.sql.expression import BinaryExpression
from sqlalchemy.sql.sqltypes import _type_map

from talos.core import utils

RE_CIDR = re.compile(r'^(\d{1,3}\.){0,3}\d{1,3}/\d{1,2}$')
RE_IP = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
RE_CIDR_LIKE = re.compile(r'^(\d{1,3}|\d{1,3}\.\d{1,3}|\d{1,3}\.\d{1,3}\.\d{1,3})(\.)?(/\d{1,2})?$')


def column_from_expression(table, expression):
    expr_wrapper = None
    if '.' in expression:
        fields = expression.split('.')
        column = getattr(table, fields.pop(0), None)
        while column is not None and fields:
            field = fields.pop(0)
            # expression as column
            if isinstance(column, BinaryExpression):
                field = int(field) if field.isdigit() else field
                column = column[field]
            # column or relationship
            elif isinstance(column, attributes.InstrumentedAttribute):
                if isinstance(column.property, properties.ColumnProperty):
                    field = int(field) if field.isdigit() else field
                    column = column[field]
                elif isinstance(column.property, relationships.RelationshipProperty):
                    # has or any
                    expr_wrapper = column.has
                    if isinstance(column.impl, attributes.CollectionAttributeImpl):
                        expr_wrapper = column.any
                    sub_fields = fields[:]
                    sub_fields.insert(0, field)
                    sub_expr_wrapper, column = column_from_expression(column.property.mapper.class_ , '.'.join(sub_fields))
                    fields = []
                    if sub_expr_wrapper is not None:
                        # relationship depth too many, can not forged column
                        column = None
                else:
                    column = None
            
            else:
                column = None
    else:
        column = getattr(table, expression, None)
    return expr_wrapper, column


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

    def make_empty_query(self, column):
        return column == None & column != None

    def op(self, column, value):
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            expr = column.in_(tuple(value))
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            expr = column == value
        return expr

    def op_in(self, column, value):
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            expr = column.in_(tuple(value))
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            expr = column == value
        return expr

    def op_nin(self, column, value):
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            expr = column.notin_(tuple(value))
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            expr = column != value
        return expr

    def op_eq(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column == value
        return expr

    def op_ne(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column != value
        return expr

    def op_lt(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column < value
        return expr

    def op_lte(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column <= value
        return expr

    def op_gt(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column > value
        return expr

    def op_gte(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column >= value
        return expr

    def op_like(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.like('%%%s%%' % value)
        return expr

    def op_starts(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.like('%s%%' % value)
        return expr

    def op_ends(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.like('%%%s' % value)
        return expr
    
    def op_nlike(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.notlike('%%%s%%' % value)
        return expr

    def op_ilike(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.ilike('%%%s%%' % value)
        return expr

    def op_istarts(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.ilike('%s%%' % value)
        return expr

    def op_iends(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.ilike('%%%s' % value)
        return expr
    
    def op_nilike(self, column, value):
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.notilike('%%%s%%' % value)
        return expr
    
    def op_nnull(self, column, value):
        expr = column != None
        return expr
    
    def op_null(self, column, value):
        expr = column == None
        return expr


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

    def op(self, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(column)
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            filters = column.op("<<=")(value[0])
            for index in range(1, len(value)):
                filters |= column.op("<<=")(value[index])
            expr = filters
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            expr = column == value
        return expr

    def op_in(self, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(column)
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            filters = column.op("<<=")(value[0])
            for index in range(1, len(value)):
                filters |= column.op("<<=")(value[index])
            expr = filters
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            expr = column.op("<<=")(value)
        return expr

    def op_nin(self, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(column)
        if utils.is_list_type(value):
            if isinstance(column, BinaryExpression):
                column = cast(column, value[0])
            filters = ~column.op("<<=")(value[0])
            for index in range(1, len(value)):
                filters &= ~column.op("<<=")(value[index])
            expr = filters
        else:
            if isinstance(column, BinaryExpression):
                column = cast(column, value)
            expr = ~column.op("<<=")(value)
        return expr

    def op_like(self, column, value):
        return None
    
    def op_nlike(self, column, value):
        return None

    def op_starts(self, column, value):
        return None

    def op_ends(self, column, value):
        return None

    def op_ilike(self, column, value):
        return None
    
    def op_nilike(self, column, value):
        return None

    def op_istarts(self, column, value):
        return None

    def op_iends(self, column, value):
        return None

    def op_lt(self, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(column)
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.op("<<")(value)
        return expr

    def op_lte(self, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(column)
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.op("<<=")(value)
        return expr

    def op_gt(self, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(column)
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.op(">>")(value)
        return expr

    def op_gte(self, column, value):
        value = self.validate_cidr(value)
        if not value:
            return self.make_empty_query(column)
        if isinstance(column, BinaryExpression):
            column = cast(column, value)
        expr = column.op(">>=")(value)
        return expr


class FilterNumber(Filter):
    '''
    数字类型不支持like操作
    '''

    def op_like(self, column, value):
        return None
    
    def op_nlike(self, column, value):
        return None

    def op_starts(self, column, value):
        return None

    def op_ends(self, column, value):
        return None

    def op_ilike(self, column, value):
        return None
    
    def op_nilike(self, column, value):
        return None

    def op_istarts(self, column, value):
        return None

    def op_iends(self, column, value):
        return None


FilterDateTime = FilterNumber
