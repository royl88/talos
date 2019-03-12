# coding=utf-8

from __future__ import absolute_import

import time
import falcon
from falcon import testing
import pytest

from talos.middlewares.limiter import RateLimitExceeded
from talos.middlewares import limiter
from talos.common import decorators as deco


@deco.limit_class('1/second')
class ControllerPerMethod(object):
    def on_get(self, req, resp):
        pass

    def on_post(self, req, resp):
        pass


@deco.limit_class('1/second', per_method=False)
class ControllerPerCtl(object):
    def on_get(self, req, resp):
        pass

    def on_post(self, req, resp):
        pass


@deco.limit_class('1/second', msg_fmt='ooh, max access: %(limit)s time reach, you can retry after %(reset)s seconds')
class ControllerUserMsg(object):
    def on_get(self, req, resp):
        pass


def key_extract(req):
    data = req.media
    return data['name']


@deco.limit_class('1/second', key_function=key_extract)
class ControllerUserKeyFunc(object):
    def on_get(self, req, resp):
        pass


def error_http_exception(ex, req, resp, params):
    """捕获并转换内部Exception为falcon Exception"""
    print(ex)
    http_status = 'HTTP_' + str(getattr(ex, 'code', 500))
    if hasattr(falcon, http_status):
        http_status = getattr(falcon, http_status)
    else:
        http_status = falcon.HTTP_500
    raise falcon.HTTPError(http_status,
                           title=getattr(ex, 'title', http_status.split(' ')[1]),
                           description=getattr(ex, 'message', str(ex)),
                           code=http_status.split(' ')[0])


def error_serializer(req, resp, exception):
    representation = None

    preferred = req.client_prefers(('application/xml',
                                    'application/json',))

    if preferred:
        if preferred == 'application/json':
            representation = exception.to_json()
        else:
            representation = exception.to_xml()
        resp.body = representation
        resp.content_type = preferred


app = falcon.API(middleware=[limiter.Limiter(True, [], 'fixed-window',
                                             'memory://', True, 'X-RESET', 'X-REMAIN', 'X-LIMIT')])
app.add_route('/permethod', ControllerPerMethod())
app.add_route('/perctl', ControllerPerCtl())
app.add_route('/usermsg', ControllerUserMsg())
app.add_route('/userkeyfunc', ControllerUserKeyFunc())
app.add_error_handler(Exception, error_http_exception)
app.set_error_serializer(error_serializer)
client = testing.TestClient(app)
from wsgiref.simple_server import make_server
httpd = make_server('0.0.0.0', 9000, app)
httpd.serve_forever()


def test_permethod_ok():
    time.sleep(1.1)
    client.simulate_get('/permethod')
    client.simulate_post('/permethod')


def test_permethod_limit():
    time.sleep(1.1)
    client.simulate_get('/permethod')
    client.simulate_post('/permethod')
    resp = client.simulate_get('/permethod')
    assert resp.status == falcon.HTTP_429


def test_perctl_limit():
    time.sleep(1.1)
    client.simulate_get('/perctl')
    resp = client.simulate_post('/perctl')
    assert resp.status == falcon.HTTP_429


def test_usermsg_limit():
    time.sleep(1.1)
    client.simulate_get('/usermsg')
    resp = client.simulate_get('/usermsg')
    assert resp.status == falcon.HTTP_429
    assert resp.json['message'].startswith('ooh, max accesss')


def test_userkeyfunc_ok():
    time.sleep(1.1)
    client.simulate_post('/userkeyfunc', json={'name': 'test1'})
    client.simulate_post('/userkeyfunc', json={'name': 'test2'})
    client.simulate_post('/userkeyfunc', json={'name': 'test3'})
    client.simulate_post('/userkeyfunc', json={'name': 'test4'})
    client.simulate_post('/userkeyfunc', json={'name': 'test5'})


def test_userkeyfunc_limit():
    time.sleep(1.1)
    client.simulate_post('/userkeyfunc', json={'name': 'test123'})
    resp = client.simulate_post('/userkeyfunc', json={'name': 'test123'})
    assert resp.status == falcon.HTTP_429
