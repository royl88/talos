# coding=utf-8
"""
本模块提供各类值的转换功能

"""

from __future__ import absolute_import

import datetime

from talos.core import utils


class NullConverter(object):
    """空转换器"""

    def convert(self, value):
        """
        执行转换

        :param value: 转换前的值
        :type value: any
        :returns: 转换后的值
        :rtype: any
        """
        pass


class DateTimeConverter(NullConverter):
    """时间转换器，转换为datetime.datetime对象"""

    def __init__(self, format=None):
        self.format = format or '%Y-%m-%d %H:%M:%S'

    def convert(self, value):
        """
        执行转换

        :param value: 转换前的值
        :type value: string
        :returns: 转换后的值
        :rtype: datetime.datetime
        """
        if isinstance(value, datetime.datetime):
            return value
        else:
            return datetime.datetime.strptime(value, self.format)


class DateConverter(NullConverter):
    """日期转换器，转换为datetime.date对象"""

    def __init__(self, format=None):
        self.format = format or '%Y-%m-%d'

    def convert(self, value):
        """
        执行转换

        :param value: 转换前的值
        :type value: string
        :returns: 转换后的值
        :rtype: datetime.date
        """
        if isinstance(value, datetime.date):
            return value
        else:
            return datetime.datetime.strptime(value, self.format).date()


class BooleanConverter(NullConverter):
    """布尔值转换器，转换为bool值"""

    def convert(self, value):
        """
        执行转换

        :param value: 转换前的值
        :type value: string
        :returns: 转换后的值
        :rtype: bool
        """
        return utils.bool_from_string(value)
