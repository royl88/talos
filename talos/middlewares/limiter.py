# coding=utf-8
"""
本模块提供调用频率限制功能

"""
from __future__ import absolute_import

import inspect
import logging
import time

from limits.errors import ConfigurationError
from limits.storage import storage_from_string
from limits.strategies import STRATEGIES
from limits.util import parse_many

from talos.common.decorators import LIMITEDS, LIMITED_EXEMPT
from talos.common.limitwrapper import LimitWrapper
from talos.core import config
from talos.core import exceptions
from talos.core.i18n import _


LOG = logging.getLogger(__name__)
CONF = config.CONF


def get_ipaddr(request):
    return request.access_route[0]


class RateLimitExceeded(exceptions.Error):
    code = 429

    @property
    def title(self):
        return _('Rate Limit Exceeded')

    @property
    def message_format(self):
        return _('detail: rate limit exceeded, %(limit)s')


class Limiter(object):
    """
    """

    def __init__(self):
        conf_limits = CONF.rate_limit.global_limits
        callback = self.__raise_exceeded
        self.enabled = CONF.rate_limit.enabled
        self.strategy = CONF.rate_limit.strategy
        if self.strategy not in STRATEGIES:
            raise ConfigurationError(_("invalid rate limiting strategy: %(strategy)s") % {'strategy': self.strategy})
        self.storage = storage_from_string(CONF.rate_limit.storage_url)
        self.limiter = STRATEGIES[self.strategy](self.storage)
        self.key_function = get_ipaddr
        self.per_method = CONF.rate_limit.per_method
        self.global_limits = []
        if conf_limits:
            self.global_limits = [
                LimitWrapper(
                    list(parse_many(conf_limits)), self.key_function, None, self.per_method
                )
            ]
        self.header_mapping = {
            'header_reset': CONF.rate_limit.header_reset,
            'header_remaining': CONF.rate_limit.header_remaining,
            'header_limit': CONF.rate_limit.header_limit,
        }
        self.callback = callback

    def __raise_exceeded(self, limit):
        raise RateLimitExceeded(limit=limit)

    def process_resource(self, request, response, resource, params):
        limiter_key = getattr(resource, "on_" + request.method.lower(), None)
        if limiter_key and inspect.ismethod(limiter_key):
            limiter_key = limiter_key.__func__
        limiter_name = resource.__module__ + "." + resource.__class__.__name__ + ":on_" + request.method
        limiter_name = limiter_name.lower()
        limits = self.global_limits
        if limiter_key is None or not self.enabled or limiter_key in LIMITED_EXEMPT:
            return
        if limiter_key in LIMITEDS:
            limits = LIMITEDS[limiter_key]
        limit_for_header = None
        failed_limit = None
        for lim in limits:
            limit_scope = lim.get_scope(resource, request)
            cur_limits = lim.get_limits(resource, request)
            for cur_limit in cur_limits:
                if not limit_for_header or cur_limit < limit_for_header[0]:
                    limit_for_header = (cur_limit, (lim.key_func or self.key_function)(request), limit_scope)
                if not self.limiter.hit(cur_limit, (lim.key_func or self.key_function)(request), limit_scope):
                    LOG.warning("rate limit exceeded for %s (%s)", limiter_name, cur_limit)
                    failed_limit = cur_limit
                    limit_for_header = (cur_limit, (lim.key_func or self.key_function)(request), limit_scope)
                    break
            if failed_limit:
                break
        request.x_rate_limit = limit_for_header
        if failed_limit:
            return self.callback(failed_limit)

    def process_response(self, request, response, resource):
        """
        :param request:
        :param response:
        :return:
        """
        current_limit = getattr(request, "x_rate_limit", None)
        if self.enabled and current_limit:
            window_stats = self.limiter.get_window_stats(*current_limit)
            response.set_header(self.header_mapping['header_limit'], str(current_limit[0].amount))
            response.set_header(self.header_mapping['header_remaining'], window_stats[1])
            response.set_header(self.header_mapping['header_reset'], int(window_stats[0] - time.time()))
        return response
