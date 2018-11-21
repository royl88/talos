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


class RegexValidator(NullValidator):
    """正则验证器"""

    def __init__(self, templ, ignore_case=False):
        self.templ = templ
        self.flags = re.IGNORECASE if ignore_case else 0

    def validate(self, value):
        if not utils.is_string_type(value):
            return _('regex validator need string input, not %(type)s') % {'type': type(value).__name__}
        if re.match(self.templ, value, self.flags) is not None:
            return True
        return _('regex match error,regex: %(rule)s, value: %(value)s') % {'rule': self.templ, 'value': value}


class EmailValidator(NullValidator):
    """email验证器"""

    def __init__(self):
        self.templ = r'\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*'
        self.msg = _('malformated email address: %(value)s')

    def validate(self, value):
        if re.match(self.templ, value) is not None:
            return True
        return self.msg % {'value': value}


class PhoneValidator(EmailValidator):
    """电话号码验证器"""

    def __init__(self):
        self.templ = r'\d{3}-\d{8}|\d{4}-\d{7}|\d{11}'
        self.msg = _('malformated phone number: %(value)s')


class UrlValidator(EmailValidator):
    """url验证器"""

    def __init__(self):
        self.templ = r'[a-zA-z]+://[^\s]+'
        self.msg = _('malformated url address: %(value)s')


class Ipv4CidrValidator(NullValidator):
    """cidr验证器"""

    def validate(self, value):
        try:
            ipaddress.IPv4Network(utils.ensure_unicode(value))
            return True
        except ipaddress.AddressValueError as e:
            return str(e)


class Ipv4Validator(NullValidator):
    """ipv4验证器"""

    def validate(self, value):
        try:
            ipaddress.IPv4Address(utils.ensure_unicode(value))
            return True
        except ipaddress.AddressValueError as e:
            return str(e)


class LengthValidator(NullValidator):
    """长度验证器"""

    def __init__(self, minimum, maximum):
        self.minimum = minimum
        self.maximum = maximum

    def validate(self, value):
        if not (utils.is_string_type(value) or utils.is_list_type(value)):
            return _('expected string or list to calculate length, not %(type)s ') % {'type': type(value).__name__}
        if self.minimum <= len(value) and len(value) <= self.maximum:
            return True
        return _('length required: %(min)d <= %(value)d <= %(max)d') % {'min': self.minimum, 'value': len(value), 'max': self.maximum}


class TypeValidator(NullValidator):
    """类型验证器"""

    def __init__(self, *types):
        self.types = types

    def validate(self, value):
        if isinstance(value, self.types):
            return True
        return _('type invalid: %(type)s, expected: %(expected)s') % {'type': type(value), 'expected': ' or '.join([str(t) for t in self.types])}


class NumberValidator(NullValidator):
    """数字型验证器"""

    def __init__(self, *types, **kwargs):
        self.types = tuple(types)
        self.range_min = kwargs.pop('range_min', None)
        self.range_max = kwargs.pop('range_max', None)

    def validate(self, value):
        if isinstance(value, self.types):
            if self.range_min is not None and self.range_min > value:
                return _('number range min required > %(min)d') % {'min': self.range_min}
            if self.range_max is not None and self.range_max < value:
                return _('number range max required < %(max)d') % {'max': self.range_max}
            return True
        return _('type invalid: %(type)s, expected: %(expected)s') % {'type': type(value), 'expected': ' or '.join([str(t) for t in self.types])}


class InValidator(NullValidator):
    """列表内容(在)范围型验证器"""

    def __init__(self, ranger):
        self.ranger = set(ranger)

    def validate(self, value):
        if value in self.ranger:
            return True
        return _('invalid choice: %(value)s, expected: %(choice)s') % {'value': value, 'choice': str(self.ranger)}


class NotInValidator(NullValidator):
    """列表内容(不在)范围型验证器"""

    def __init__(self, ranger):
        self.ranger = set(ranger)

    def validate(self, value):
        if value not in self.ranger:
            return True
        return _('invalid choice: %(value)s, not expected: %(choice)s') % {'value': value, 'choice': str(self.ranger)}
