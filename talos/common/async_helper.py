# coding=utf-8

from __future__ import absolute_import

import functools
import logging

from falcon.routing import util

from talos.common import celery
from talos.utils import http


LOG = logging.getLogger(__name__)


class CallbackController(object):
    def __init__(self, func, method):
        self.func = func
        self.method = method
        setattr(self, 'on_%s' % method.lower(), self.template)

    def template(self, req, resp, **kwargs):
        data = req.json
        ref = self.func(data=data, request=req, response=resp, **kwargs)


def callback(url, method='POST'):
    def _wraps(func):
        @functools.wraps(func)
        def __wraps(*args, **kwargs):
            return func(*args, **kwargs)
        __wraps.__url = url
        __wraps.__method = method
        return __wraps
    return _wraps


def add_callback_route(api, func):
    url = func.__url
    method = func.__method.lower()
    api.add_route(url, CallbackController(func, method))


def send_callback(url_base, func, data, **kwargs):
    url = func.__url
    method = func.__method.lower()
    vars, pattern = util.compile_uri_template(url)
    for var in vars:
        url = url.replace('{%s}' % var, kwargs.get(var))
    url = url_base + url
    http_method = getattr(http.RestfulJson, method, None)
    LOG.debug('######## worker callback %s %s, data: %s', method, url, data)
    result = http_method(url, json=data)
    return result


def send_task(name, kwargs, **task_kwargs):
    return celery.app.send_task(name,
                                kwargs=kwargs,
                                **task_kwargs)
