# coding=utf-8

from __future__ import absolute_import


class LazyInit(object):
    """
    中间件，提供延迟初始化
    主要原因：在程序初始化时middleware.init使用了CONF，而此时CONF并未加载导致的报错，均可以使用LazyInit进行包装
    LazyInit(limiter.Limiter)
    """

    def __init__(self, _middleware, *args, **kwargs):
        self._middleware = _middleware
        self._args = args
        self._kwargs = kwargs
        self._instance = None
    
    def _create_not_exist(self):
        if self._instance is None:
            self._instance = self._middleware(*self._args, **self._kwargs)

    def process_request(self, request, response):
        self._create_not_exist()
        if hasattr(self._instance, 'process_request'):
            self._instance.process_request(request, response)
    
    def process_resource(self, request, response, resource, params):
        self._create_not_exist()
        if hasattr(self._instance, 'process_resource'):
            self._instance.process_resource(request, response, resource, params)

    def process_response(self, req, resp, resource, *args, **kwargs):
        self._create_not_exist()
        if hasattr(self._instance, 'process_response'):
            self._instance.process_response(req, resp, resource, *args, **kwargs)
