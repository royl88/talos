# coding=utf-8

from __future__ import absolute_import

import logging
import uuid

from falcon.routing import util
import ipaddress

from talos.common import celery
from talos.core import config
from talos.core import exceptions
from talos.core import utils as talos_util
from talos.utils import http

LOG = logging.getLogger(__name__)
CONF = config.CONF


class CallbackController(object):

    def __init__(self, func, method, name=None, with_request=False, with_response=False):
        self.name = name or uuid.uuid4().hex
        self.func = func
        self.method = method
        self.with_request = with_request
        self.with_response = with_response
        setattr(self, 'on_%s' % method.lower(), self.template)

    def _get_ipaddr(self, request, strict):
        if strict:
            return request.remote_addr
        else:
            return request.access_route[0]

    def _merge_hosts(self, g_hosts, n_hosts):
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

    def _check_auth(self, req, resp):
        strict_client = talos_util.get_config(CONF, 'worker.callback.strict_client', True)
        global_allow_hosts = talos_util.get_config(CONF, 'worker.callback.allow_hosts', None)
        name_allow_hosts = talos_util.get_config(CONF, 'worker.callback.name', None)
        # 防止controller的name中带有.特殊字符，无法取出值
        if name_allow_hosts is not None:
            name_allow_hosts = name_allow_hosts.get(self.name, {}).get('allow_hosts', None)
        allow_hosts = self._merge_hosts(global_allow_hosts, name_allow_hosts)
        cur_client = self._get_ipaddr(req, strict_client)
        if allow_hosts:
            allow_hosts = [ipaddress.IPv4Network(talos_util.ensure_unicode(h), strict=False) for h in allow_hosts]
        if allow_hosts is not None and ipaddress.IPv4Address(talos_util.ensure_unicode(cur_client)) not in allow_hosts:
            raise exceptions.ForbiddenError()

    def template(self, req, resp, **kwargs):
        self._check_auth(req, resp)
        data = getattr(req, 'json', None)
        if self.with_request:
            kwargs['request'] = req
        if self.with_response:
            kwargs['response'] = resp
        resp_data = self.func(data, **kwargs)
        resp.json = resp_data


def send_callback(url_base, func, data, request_context=None, **kwargs):
    """
    进行远程函数调用

    talos>=1.3.0: 建议使用func.remote(data, xxx)方式进行更便捷的远程调用
    talos>=1.3.0: 移除了原有的timeout参数，全部封装到request_context参数中，默认有timeout=10,verify=False
                 可以使用func.context(timeout=30).remote(data, xxx)进行context参数的修改

    :param url_base:
    :type url_base:
    :param func:
    :type func:
    :param data:
    :type data:
    :param request_context:
    :type request_context:
    """
    url = func.url_path
    method = func.method.lower()
    request_context = request_context or {}
    request_context.setdefault('timeout', 10)
    request_context.setdefault('verify', False)
    vars, pattern = util.compile_uri_template(url)
    for var in vars:
        url = url.replace('{%s}' % var, str(kwargs.get(var)))
    url_base = CONF.public_endpoint if url_base is None else url_base
    url = url_base + url
    http_method = getattr(http.RestfulJson, method, None)
    LOG.debug('######## async_helper:send_callback %s %s, data: %s', method, url, data)
    result = http_method(url, json=data, **request_context)
    return result


def callback(url, name=None, method='POST', with_request=False, with_response=False):
    """
    远程函数调用装饰器(别名rpc, eg. @rpc)，可提供异步任务的回调机制，用法如下：

    @callback('/callback/orders/{order_id}', name='order_notify')
    def test(data, order_id):
        pass

    url是talos标准的route url格式，url中接受标准变量格式，url中的变量会体现在test函数中的参数中
    name主要是用于控制controller的名称，主要便于权限控制管理，若不指定，则自动生成uuid
    method是标准的http方法，支持带body数据的方法，常用的：POST，PATCH，PUT

    test是用户自定义的回调函数，此函数是在客户端使用，但实际在服务端运行

    函数要求func(data, **kwargs), data是强制参数，**kwargs是根据url的参数自行确定

    本地调用：
    test(data, 'order_20190193922')，可以作为普通本地函数调用(注：客户端运行）

    远程调用方式：
    send_callback(None, test, data, order_id='order_20190193922')

    talos version >= 1.3.0：
    移除了回调函数对request，response参数定义的要求
    直接调用：
    test.remote({'val': '123'}, order_id='order_20190193922')
    可以设置context再进行调用，context为requests库的额外参数，比如headers，timeout，verify等
    test.context(timeout=10, headers={'X-Auth-Token': 'token_1'}).remote({'val': '123'}, order_id='order_20190193922')
    test.context(timeout=10).baseurl('http://clusterip.of.app.com').remote({'val': '123'}, order_id='order_20190193922')
    """

    def _wraps(func):

        class __wraps_c(object):

            def __init__(self, base_url=None, requests_ctx=None):
                self.__url = url
                self.__name = name
                self.__method = method
                self.__with_request = with_request
                self.__with_response = with_response
                self.__base_url = base_url
                self.__requests_ctx = requests_ctx

            @property
            def url_path(self):
                return self.__url

            @property
            def name(self):
                return self.__name

            @property
            def method(self):
                return self.__method

            @property
            def with_request(self):
                return self.__with_request

            @property
            def with_response(self):
                return self.__with_response

            def __call__(self, data, **kwargs):
                return func(data=data, **kwargs)

            def context(self, **kwargs):
                new_instance = self.__class__(base_url=self.__base_url, requests_ctx=kwargs)
                return new_instance

            def baseurl(self, url_prefix):
                new_instance = self.__class__(base_url=url_prefix, requests_ctx=self.__requests_ctx)
                return new_instance

            def remote(self, data, **kwargs):
                url_prefix = self.__base_url
                return send_callback(url_prefix, self, data,
                                     request_context=self.__requests_ctx, **kwargs)

        return __wraps_c()

    return _wraps


def add_callback_route(api, func):
    """
    将回调函数注册到url route中
    :param api: falcon.Api对象
    :type api: falcon.Api
    :param func: @callback/@rpc装饰器包装的函数
    :type func: function
    """
    url = func.url_path
    name = func.name
    method = func.method.lower()
    with_request = func.with_request
    with_response = func.with_response
    api.add_route(url, CallbackController(func, method, name=name,
                                          with_request=with_request, with_response=with_response))


# since v1.1.9, rename callback to rpc
rpc = callback
add_rpc_route = add_callback_route
rpc_call = send_callback


def send_task(name, kwargs, **task_kwargs):
    return celery.app.send_task(name,
                                kwargs=kwargs,
                                **task_kwargs)
