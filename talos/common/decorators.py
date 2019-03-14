# coding=utf-8
"""
本模块提供各类装饰器

"""

from __future__ import absolute_import

import functools
import time

from limits.strategies import STRATEGIES
from limits.storage import storage_from_string
from limits.util import parse_many
from talos.common import limitwrapper
from talos.core import config
from talos.core import decorators as deco

LIMITEDS = {}
LIMITEDS_EXEMPT = {}
FLIMITEDS = {}


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
        LIMITEDS_EXEMPT[instance] = None
        return instance

    return __inner


def flimit(limit_value, scope=None, key_func=None, strategy='fixed-window', message=None, storage=None, hit_func=None, delay_hit=False):
    """
    用于装饰一个函数、类函数表示其受限于此调用频率
    :param limit_value: limits的调用频率字符串或一个能返回限制器的函数.
    :param function key_func: 一个返回唯一标识字符串的函数，用于标识一个limiter,比如远端IP.
    :param function scope: 调用频率限制范围的命名空间.
    """

    @deco.singleton
    class _storage_agent(object):

        def __init__(self, s):
            self.storage = storage_from_string(s)

    def _default_key_func(*args, **kwargs):
        return ''

    def _default_hit_func(x):
        return True

    key_func = key_func or _default_key_func
    hit_func = hit_func or _default_hit_func

    def _inner(fn):

        @functools.wraps(fn)
        def __inner(*args, **kwargs):

            def _test_limit(user_result):
                for grp_limit in FLIMITEDS[__inner]:
                    cur_limits, cur_key_func, cur_scope, cur_message, cur_hit_func = grp_limit
                    storage_a = _storage_agent(storage or config.CONF.rate_limit.storage_url).storage
                    limiter = STRATEGIES[strategy](storage_a)
                    for cur_limit in cur_limits:
                        plimit = (cur_limit, cur_key_func(*args, **kwargs), cur_scope)
                        if cur_hit_func(user_result) and not limiter.hit(*plimit):
                            if cur_message:
                                window_stats = limiter.get_window_stats(*plimit)
                                cur_message = cur_message % {
                                    'limit': cur_limit.amount, 'remaining': window_stats[1], 'reset': int(window_stats[0] - time.time())}
                                raise limitwrapper.RateLimitExceeded(message=cur_message)
                            raise limitwrapper.RateLimitExceeded(limit=cur_limit)

            if __inner in FLIMITEDS:
                if not delay_hit:
                    _test_limit(None)
                result = fn(*args, **kwargs)
                if delay_hit:
                    _test_limit(result)
                    
            else:
                result = fn(*args, **kwargs)
            return result

        scope = scope or (fn.__module__ + '.' + fn.__class__.__name__ + ':' + fn.__name__)
        # 处理重复的装饰器
        # @flimit(...)
        # @flimit(...)
        # def test():
        #     pass
        if fn in FLIMITEDS:
            FLIMITEDS.setdefault(__inner, FLIMITEDS.pop(fn))
        FLIMITEDS.setdefault(__inner, []).append((parse_many(limit_value), key_func, scope, message, hit_func))
        return __inner

    return _inner
