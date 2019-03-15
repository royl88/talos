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

LIMITEDS = {}
LIMITEDS_EXEMPT = {}
FLIMITEDS = {}
FLIMITEDS_SINGLETON = {}


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
    当装饰类成员函数时，频率限制范围是类级别的，意味着类的不同实例共享相同的频率限制，
    如果需要实例级隔离的频率限制，需要手动指定key_func，并使用返回实例标识作为限制参数
    
    :param limit_value: 频率设置：格式[count] [per|/] [n (optional)] [second|minute|hour|day|month|year]
    :param scope: 限制范围空间：默认python类/函数完整路径.
    :param key_func: 关键限制参数：默认为空字符串，自定义函数：def key_func(*args, **kwargs) -> string
    :param strategy: 算法：支持fixed-window、fixed-window-elastic-expiry、moving-window
    :param message: 错误提示信息：错误提示信息可接受3个格式化（limit，remaining，reset）内容
    :param storage: 频率限制后端存储数据，如: memory://, redis://:pass@localhost:6379
    :param hit_func: 函数定义为def hit(result) -> bool，为True时则触发频率限制器hit，否则忽略
    :param delay_hit: 默认在函数执行前测试频率hit，可以设置为True将频率测试hit放置在函数执行后，搭配hit_func
                       使用，可以获取到函数执行结果来控制是否执行hit

    """
    
    def special_singleton(cls):

        def _singleton(*args, **kwargs):
            fullkey = str((tuple(args), tuple(kwargs.items())))
            if fullkey not in FLIMITEDS_SINGLETON:
                FLIMITEDS_SINGLETON[fullkey] = cls(*args, **kwargs)
            return FLIMITEDS_SINGLETON[fullkey]
    
        return _singleton

    @special_singleton
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
                    cur_scope = cur_scope or (fn.__module__ + '.' + fn.__class__.__name__ + ':' + fn.__name__)
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

            # 如果是多级flimit装饰器，会保留最后一个__inner->[所有limits]的映射关系
            if __inner in FLIMITEDS:
                if not delay_hit:
                    _test_limit(None)
                result = fn(*args, **kwargs)
                if delay_hit:
                    _test_limit(result)
            # 如果是已经被合并的__inner只需要执行并获取结果即可
            else:
                result = fn(*args, **kwargs)
            return result
        
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
