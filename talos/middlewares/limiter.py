# coding=utf-8
"""
本模块提供调用频率限制功能

"""
from __future__ import absolute_import

import functools
import inspect
import logging
import time

from limits.errors import ConfigurationError
from limits.storage import storage_from_string
from limits.strategies import STRATEGIES
from talos.common import limitwrapper
from talos.common.decorators import LIMITEDS, LIMITEDS_EXEMPT
from talos.core import config
from talos.core.i18n import _


LOG = logging.getLogger(__name__)
CONF = config.CONF


def get_ipaddr(request):
    return request.access_route[0]


class Limiter(object):
    """
    Limiter是基础falcon提供频率限制中间件

    基本使用步骤：

    - 在controller上配置装饰器
    - 将Limiter配置到启动中间件

    装饰器通过管理映射关系表LIMITEDS，LIMITEDS_EXEMPT来定位用户设置的类实例->频率限制器关系，
    频率限制器是实力级别的，意味着每个实例都使用自己的频率限制器

    频率限制器有7个主要参数：频率设置，关键限制参数，限制范围，是否对独立方法进行不同限制, 算法，错误提示信息, hit函数

    - 频率设置：格式[count] [per|/] [n (optional)] [second|minute|hour|day|month|year]
    - 关键限制参数：默认为IP地址(支持X-Forwarded-For)，自定义函数：def key_func(request) -> string
    - 限制范围：默认python类完整路径，自定义函数def scope_func(request) -> string
    - 是否对独立方法进行不同限制: 布尔值，默认True
    - 算法：支持fixed-window、fixed-window-elastic-expiry、moving-window
    - 错误提示信息：错误提示信息可接受3个格式化（limit，remaining，reset）内容
    - hit函数：函数定义为def hit(resource, request) -> bool，为True时则触发频率限制器hit，否则忽略

    PS：真正的频率限制范围 = 关键限制参数(默认IP地址) + 限制范围(默认python类完整路径) + 方法名(如果区分独立方法)，
    当此频率范围被命中后才会触发频率限制
    """

    def __init__(self,
                 enabled=None,
                 global_limits=None,
                 strategy=None,
                 storage_url=None,
                 per_method=None,
                 key_func=None,
                 header_reset=None,
                 header_remaining=None,
                 header_limit=None):
        conf_limits = CONF.rate_limit.global_limits if global_limits is None else global_limits
        callback = self.__raise_exceeded
        self.enabled = CONF.rate_limit.enabled if enabled is None else enabled
        self.strategy = strategy or CONF.rate_limit.strategy
        if self.strategy not in STRATEGIES:
            raise ConfigurationError(_("invalid rate limiting strategy: %(strategy)s") % {'strategy': self.strategy})
        self.storage = storage_from_string(storage_url or CONF.rate_limit.storage_url)
        self.limiters = {}
        for strategy_name, strategy_class in STRATEGIES.items():
            self.limiters[strategy_name] = strategy_class(self.storage)
        self.key_function = get_ipaddr if key_func is None else key_func
        self.per_method = CONF.rate_limit.per_method if per_method is None else per_method
        self.global_limits = []
        if conf_limits:
            self.global_limits = [
                limitwrapper.LimitWrapper(
                    conf_limits, self.key_function, None, self.per_method
                )
            ]
        self.header_mapping = {
            'header_reset': header_reset or CONF.rate_limit.header_reset,
            'header_remaining': header_remaining or CONF.rate_limit.header_remaining,
            'header_limit': header_limit or CONF.rate_limit.header_limit,
        }
        self.callback = callback

    def __raise_exceeded(self, limiter, limit, hit_message=None):
        """
        当到达频率限制时抛出异常
        :param limiter: `RateLimiter` 对象（含存储、限制策略）
        :param limit: (limit, key_func, scope)元组
        :param hit_message: 自定义错误信息
        """
        # 如果用户定义了错误消息，则直接使用消息内容
        if hit_message:
            window_stats = limiter.get_window_stats(*limit)
            hit_message = hit_message % {
                'limit': limit[0].amount, 'remaining': window_stats[1], 'reset': int(window_stats[0] - time.time())}
            raise limitwrapper.RateLimitExceeded(message=hit_message)
        raise limitwrapper.RateLimitExceeded(limit=limit[0])

    def process_resource(self, request, response, resource, params):
        limiter_key = resource
        if limiter_key and inspect.ismethod(limiter_key):
            limiter_key = limiter_key.__func__
        resource_name = resource.__module__ + "." + resource.__class__.__name__ + ":on_" + request.method
        resource_name = resource_name.lower()
        limits = self.global_limits
        if limiter_key is None or not self.enabled or limiter_key in LIMITEDS_EXEMPT:
            return
        if limiter_key in LIMITEDS:
            limits = LIMITEDS[limiter_key]
        limit_for_header = None
        limiter_for_header = None
        limit_reach = False
        failed_message = None
        for lim in limits:
            limiter_for_header = self.limiters[lim.strategy or self.strategy]
            limit_scope = lim.get_scope(resource, request)
            cur_limits = lim.get_limits(resource, request)
            failed_message = lim.message
            for cur_limit in cur_limits:
                if not limit_for_header or cur_limit < limit_for_header[0]:
                    limit_for_header = (cur_limit, (lim.key_func or self.key_function)(request), limit_scope)
                makehit = functools.partial(limiter_for_header.hit, cur_limit,
                                            (lim.key_func or self.key_function)(request), limit_scope)
                hit_result = True
                if lim.hit_func:
                    if lim.hit_func(resource, request):
                        hit_result = makehit()
                else:
                    hit_result = makehit()

                if not hit_result:
                    LOG.warning("rate limit exceeded for %s (%s)", resource_name, cur_limit)
                    limit_reach = True
                    limit_for_header = (cur_limit, (lim.key_func or self.key_function)(request), limit_scope)
                    break
            if limit_reach:
                break
        request.x_rate_limiter = limiter_for_header
        request.x_rate_limit = limit_for_header
        if limit_reach:
            return self.callback(limiter_for_header, limit_for_header, failed_message)

    def process_response(self, request, response, resource, *args, **kwargs):
        """
        :param request:
        :param response:
        :return:
        """
        current_limiter = getattr(request, "x_rate_limiter", None)
        current_limit = getattr(request, "x_rate_limit", None)
        if self.enabled and current_limit:
            window_stats = current_limiter.get_window_stats(*current_limit)
            response.set_header(self.header_mapping['header_limit'], current_limit[0].amount)
            response.set_header(self.header_mapping['header_remaining'], window_stats[1])
            response.set_header(self.header_mapping['header_reset'], int(window_stats[0] - time.time()))
        return response
