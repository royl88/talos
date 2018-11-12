# coding=utf-8

from __future__ import absolute_import

import functools
import logging
import uuid

from falcon.routing import util

from talos.common import celery
from talos.utils import http
from talos.core import config
from talos.core import utils as talos_util
from talos.core import exceptions


LOG = logging.getLogger(__name__)
CONF = config.CONF


class CallbackController(object):
    def __init__(self, func, method, name=None):
        self.name = name or uuid.uuid4().hex
        self.func = func
        self.method = method
        setattr(self, 'on_%s' % method.lower(), self.template)

    def template(self, req, resp, **kwargs):
        data = req.json
        self.func(data=data, request=req, response=resp, **kwargs)


def callback(url, name=None, method='POST'):
    def _wraps(func):
        def _get_ipaddr(request, strict):
            if strict:
                return request.remote_addr
            else:
                return request.access_route[0]

        def _merge_hosts(g_hosts, n_hosts):
            allow_hosts = None
            if g_hosts is None:
                if n_hosts is None:
                    allow_hosts = None
                else:
                    allow_hosts = list(n_hosts[:])
            else:
                allow_hosts = list(g_hosts[:])
                if n_hosts is not None:
                    allow_hosts.extend(n_hosts[:])
            if allow_hosts is not None:
                return set(allow_hosts)

        @functools.wraps(func)
        def __wraps(data, request, response, **kwargs):
            strict_client = talos_util.get_config(CONF, 'worker.callback.strict_client', True)
            global_allow_hosts = talos_util.get_config(CONF, 'worker.callback.allow_hosts', None)
            name_allow_hosts = talos_util.get_config(CONF, 'worker.callback.name.%s.allow_hosts' % name, None)
            allow_hosts = _merge_hosts(global_allow_hosts, name_allow_hosts)
            cur_client = _get_ipaddr(request, strict_client)
            if allow_hosts is not None and cur_client not in allow_hosts:
                raise exceptions.ForbiddenError()
            return func(data=data, request=request, response=response, **kwargs)
        __wraps.__url = url
        __wraps.__name = name
        __wraps.__method = method
        return __wraps
    return _wraps


def add_callback_route(api, func):
    url = func.__url
    name = func.__name
    method = func.__method.lower()
    api.add_route(url, CallbackController(func, method, name=name))


def send_callback(url_base, func, data, timeout=3, **kwargs):
    url = func.__url
    method = func.__method.lower()
    vars, pattern = util.compile_uri_template(url)
    for var in vars:
        url = url.replace('{%s}' % var, kwargs.get(var))
    url_base = CONF.public_endpoint if url_base is None else url_base
    url = url_base + url
    http_method = getattr(http.RestfulJson, method, None)
    LOG.debug('######## worker callback %s %s, data: %s', method, url, data)
    result = http_method(url, json=data, timeout=timeout)
    return result


# since v1.1.9, rename callback to rpc
rpc = callback
add_rpc_route = add_callback_route
rpc_call = send_callback


def send_task(name, kwargs, **task_kwargs):
    return celery.app.send_task(name,
                                kwargs=kwargs,
                                **task_kwargs)
