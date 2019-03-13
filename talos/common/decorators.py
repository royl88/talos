# coding=utf-8
"""
本模块提供各类装饰器

"""

from __future__ import absolute_import

import functools
from limits.util import parse_many

from talos.common import limitwrapper

LIMITEDS = {}
LIMITED_EXEMPT = {}


def limit(limit_value, key_function=None, scope=None, per_method=True, strategy=None, message=None, hit_func=None):
    """
    用于装饰一个controller表示其受限于此调用频率
    :param limit_value: limits的调用频率字符串或一个能返回限制器的函数.
    :param function key_func: 一个返回唯一标识字符串的函数，用于标识一个limiter,比如远端IP.
    :param function scope: 调用频率限制范围的命名空间.
    :param strategy: 频率限制算法策略.
    :param message: 错误提示信息可接受3个格式化（limit，remaining，reset）内容.
    :param hit_func: 使用自定义hit计算，并非每次访问都触发hit，而由用户自定定义
    """

    def _inner(fn):

        @functools.wraps(fn)
        def __inner(*args, **kwargs):
            instance = fn(*args, **kwargs)
            LIMITEDS.setdefault(instance, []).append(
                limitwrapper.LimitWrapper(limit_value, key_function, scope, per_method=per_method,
                             strategy=strategy, message=message, hit_func=hit_func)
            )
            return instance

        return __inner

    return _inner


def limit_exempt(fn):
    """
    标识一个controller不受限与调用频率限制(当有全局limit时).
    """

    @functools.wraps(fn)
    def __inner(*args, **kwargs):
        instance = fn(*args, **kwargs)
        LIMITED_EXEMPT[instance] = None
        return instance

    return __inner
