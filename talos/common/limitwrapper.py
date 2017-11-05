# coding=utf-8
"""
本模块提供频率限制所需的上下文

"""

from __future__ import absolute_import

from limits.util import parse_many


class LimitWrapper(object):
    """
    封装调用频率限制所需的上下文
    """

    def __init__(self, limits, key_func, scope, per_method=True):
        self._limits = limits
        self._scope = scope
        self.per_method = per_method
        self.key_func = key_func

    def get_limits(self, resource, request):
        return list(parse_many(self._limits(request))) if callable(self._limits) else self._limits

    def get_scope(self, resource, request):
        scope = (
            self._scope(request) if callable(self._scope) else (
                self._scope if self._scope else (resource.__module__ + "." + resource.__class__.__name__).lower()
            )
        )
        if self.per_method:
            scope = ':'.join([scope, request.method.lower()])
        return scope
