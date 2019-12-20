# coding=utf-8
"""
本模块提供通用验证器

"""
from __future__ import absolute_import

import re

import ipaddress

from talos.core import utils
from talos.core.i18n import _


class NullValidator(object):
    """空验证器"""

    def validate(self, value):
        return True


class CallbackValidator(NullValidator):
    """回调验证器"""

    def __init__(self, func):
        self._func = func
        if not callable(func):
            raise ValueError(_('must be callable, eg. func(value)'))

    def validate(self, value):
        return self._func(value)


class RegexValidator(NullValidator):
    """正则验证器"""

    def __init__(self, templ, ignore_case=False):
        self._templ = templ
        self._flags = re.IGNORECASE if ignore_case else 0

    def validate(self, value):
        if not utils.is_string_type(value):
            return _('need string input, not %(type)s') % {'type': type(value).__name__}
        if re.match(self._templ, value, self._flags) is not None:
            return True
        return _('regex match error,regex: %(rule)s, value: %(value)s') % {'rule': self._templ, 'value': value}


class EmailValidator(NullValidator):
    """email验证器"""

    def __init__(self):
        self._templ = r'\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*'
        self._msg = _('malformated email address: %(value)s')

    def validate(self, value):
        if not utils.is_string_type(value):
            return _('need string input, not %(type)s') % {'type': type(value).__name__}
        if re.match(self._templ, value) is not None:
            return True
        return self._msg % {'value': value}


class PhoneValidator(EmailValidator):
    """电话号码验证器"""

    def __init__(self):
        self._templ = r'\d{3}-\d{8}|\d{4}-\d{7}|\d{11}'
        self._msg = _('malformated phone number: %(value)s')


class UrlValidator(EmailValidator):
    """url验证器"""

    def __init__(self):
        self._templ = r'[a-zA-z]+://[^\s]+'
        self._msg = _('malformated url address: %(value)s')


class Ipv4CidrValidator(NullValidator):
    """cidr验证器"""

    def __init__(self, strict=True):
        self._strict = strict

    def validate(self, value):
        if not utils.is_string_type(value):
            return _('need string input, not %(type)s') % {'type': type(value).__name__}
        try:
            ipaddress.IPv4Network(utils.ensure_unicode(value), strict=self._strict)
            return True
        except ipaddress.AddressValueError as e:
            return str(e)


class Ipv4Validator(NullValidator):
    """ipv4验证器"""

    def validate(self, value):
        if not utils.is_string_type(value):
            return _('need string input, not %(type)s') % {'type': type(value).__name__}
        try:
            ipaddress.IPv4Address(utils.ensure_unicode(value))
            return True
        except ipaddress.AddressValueError as e:
            return str(e)


class LengthValidator(NullValidator):
    """长度验证器"""

    def __init__(self, minimum, maximum):
        self._minimum = minimum
        self._maximum = maximum

    def validate(self, value):
        if not (utils.is_string_type(value) or utils.is_list_type(value)):
            return _('expected string or list to calculate length, not %(type)s ') % {'type': type(value).__name__}
        if self._minimum <= len(value) and len(value) <= self._maximum:
            return True
        return _('length required: %(min)d <= %(value)d <= %(max)d') % {'min': self._minimum, 'value': len(value), 'max': self._maximum}


class TypeValidator(NullValidator):
    """类型验证器"""

    def __init__(self, *types):
        self._types = types

    def validate(self, value):
        if isinstance(value, self._types):
            return True
        return _('type invalid: %(type)s, expected: %(expected)s') % {'type': type(value), 'expected': ' or '.join([str(t) for t in self._types])}


class NumberValidator(NullValidator):
    """数字型验证器"""

    def __init__(self, *types, **kwargs):
        self._types = tuple(types)
        self._range_min = kwargs.pop('range_min', None)
        self._range_max = kwargs.pop('range_max', None)

    def validate(self, value):
        if not utils.is_number_type(value):
            return _('need number input, not %(type)s') % {'type': type(value).__name__}
        if (self._types and isinstance(value, self._types)) or (not self._types):
            if self._range_min is not None and self._range_min > value:
                return _('number range min required, %(min)d <= value') % {'min': self._range_min}
            if self._range_max is not None and self._range_max < value:
                return _('number range max required, value <= %(max)d') % {'max': self._range_max}
            return True
        return _('type invalid: %(type)s, expected: %(expected)s') % {'type': type(value), 'expected': ' or '.join([str(t) for t in self._types])}


class InValidator(NullValidator):
    """列表内容(在)范围型验证器"""

    def __init__(self, choices):
        self._choices = choices

    def validate(self, value):
        if value in self._choices:
            return True
        return _('invalid choice: %(value)s, expected: %(choice)s') % {'value': value, 'choice': str(self._choices)}


class NotInValidator(NullValidator):
    """列表内容(不在)范围型验证器"""

    def __init__(self, choices):
        self._choices = choices

    def validate(self, value):
        if value not in self._choices:
            return True
        return _('invalid choice: %(value)s, not expected: %(choice)s') % {'value': value, 'choice': str(self._choices)}


class ChainValidator(NullValidator):
    """验证器串联型验证器"""

    def __init__(self, nodes):
        # 每个node都有类似validator的行为（含validate函数，返回True或错误信息）
        self._nodes = nodes

    def validate(self, value):
        for n in self._nodes:
            result = n.validate(value)
            if result is not True:
                return result
        return True
