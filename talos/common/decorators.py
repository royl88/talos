# coding=utf-8
"""
本模块提供各类装饰器

"""

from __future__ import absolute_import

import functools
from limits.util import parse_many

from talos.common.limitwrapper import LimitWrapper


LIMITEDS = {}
LIMITED_EXEMPT = {}


def limit(limit_value, key_function=None, scope=None, per_method=True):
    """
    用于装饰一个controller表示其受限于此调用频率
    :param limit_value: limits的调用频率字符串或一个能返回限制器的函数.
    :param function key_func: 一个返回唯一标识字符串的函数，用于标识一个limiter,比如远端IP.
    :param function scope: 调用频率限制范围的命名空间.
    """
    def _inner(fn):
        @functools.wraps(fn)
        def __inner(*args, **kwargs):
            return fn(*args, **kwargs)
        if fn in LIMITEDS:
            LIMITEDS.setdefault(__inner, LIMITEDS.pop(fn))
        if callable(limit_value):
            LIMITEDS.setdefault(__inner, []).append(
                LimitWrapper(limit_value, key_function, scope, per_method=per_method)
            )
        else:
            LIMITEDS.setdefault(__inner, []).append(
                LimitWrapper(list(parse_many(limit_value)), key_function, scope, per_method=per_method)
            )
        return __inner
    return _inner


def limit_exempt(fn):
    """
    标识一个函数不受限与调用频率限制.
    """
    @functools.wraps(fn)
    def __inner(*args, **kwargs):
        return fn(*args, **kwargs)
    LIMITED_EXEMPT[__inner] = None
    return __inner
