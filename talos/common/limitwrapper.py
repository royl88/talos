# coding=utf-8
"""
本模块提供频率限制所需的上下文

"""

from __future__ import absolute_import

from limits.util import parse_many
from talos.core import exceptions
from talos.core.i18n import _


class RateLimitExceeded(exceptions.Error):
    code = 429

    def __init__(self, message=None, **kwargs):
        self.limit = kwargs.get('limit', None)
        super(RateLimitExceeded, self).__init__(message, **kwargs)

    @property
    def title(self):
        return _('Rate Limit Exceeded')

    @property
    def message_format(self):
        return _('detail: rate limit exceeded, %(limit)s')


class LimitWrapper(object):
    """
    封装调用频率限制所需的上下文，详细介绍见limiter中间件
    """

    def __init__(self, limits, key_func, scope, per_method, strategy=None, message=None, hit_func=None):
        self._limits = limits
        self._scope = scope
        self.per_method = per_method
        self.key_func = key_func
        self.strategy = strategy
        self.message = message
        self.hit_func = hit_func

    def get_limits(self, resource, request):
        return list(parse_many(self._limits(request))) if callable(self._limits) else list(parse_many(self._limits))

    def get_scope(self, resource, request):
        scope = (
            self._scope(request) if callable(self._scope) else (
                self._scope if self._scope else (resource.__module__ + "." + resource.__class__.__name__).lower()
            )
        )
        if self.per_method:
            scope = ':'.join([scope, request.method.lower()])
        return scope
