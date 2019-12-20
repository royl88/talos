# coding=utf-8

import logging
import requests
import threading as concurrent
from wsgiref.simple_server import make_server

from talos.core import config

from tests import API


LOG = logging.getLogger(__name__)
CONF = config.CONF
WAIT_TIMEOUT = 10


def _server_proc(l):
    try:
        application = API
        bind_addr = CONF.server.bind
        port = CONF.server.port
        LOG.info("Serving on %s:%d..." % (bind_addr, port))
        httpd = make_server(bind_addr, port, application)
    finally:
        l.release()
    httpd.handle_request()


def start_server(lock):
    lock.acquire()
    p = concurrent.Thread(target=_server_proc, args=(lock,))
    p.start()
    return p


def test_list_user():
    l = concurrent.Lock()
    p = start_server(l)
    
    with l:
        resp = requests.get('http://127.0.0.1:9000/v1/users')
        result = resp.json()
        assert result['count'] >= 0
    p.join(WAIT_TIMEOUT)


def test_list_user_params():
    l = concurrent.Lock()
    p = start_server(l)

    with l:
        resp = requests.get('http://127.0.0.1:9000/v1/users', params={'__limit': 1,
                                                                      '__orders': 'id',
                                                                      'id__eq': '1',
                                                                      '__fields': 'id'})
        result = resp.json()
        assert result['count'] == 1
        assert result['data'][0]['id'] == '1'
        assert 'name' not in result['data'][0]
    p.join(WAIT_TIMEOUT)


def test_get_user():
    l = concurrent.Lock()
    p = start_server(l)

    with l:
        resp = requests.get('http://127.0.0.1:9000/v1/users/1')
        result = resp.json()
        assert result['id'] == '1'
    p.join(WAIT_TIMEOUT)


def test_create_user():
    from tests.apps.cats import api
    result = api.User().create({'id': '9999',
                       'name': 'talos',
                       'age': 1,
                       'department_id': '1'})
    assert result['id'] == '9999'
    
    result = api.User().update('9999', {'age': 2})
    assert result[0]['age'] == 1 and result[1]['age'] == 2

    result = api.User().delete('9999')
    assert result[0] == 1 and result[1][0]['id'] == '9999'


def test_method_not_allow():
    l = concurrent.Lock()
    p = start_server(l)
    with l:
        resp = requests.patch('http://127.0.0.1:9000/v1/users')
        assert resp.status_code == 405
    p.join(WAIT_TIMEOUT)


def test_list_user_only_ilike():
    l = concurrent.Lock()
    p = start_server(l)
    with l:
        resp = requests.get('http://127.0.0.1:9000/v1/limitedusers', params={'__limit': 1,
                                                                      '__orders': 'id',
                                                                      'id__eq': '1',
                                                                      '__fields': 'id'})
        result = resp.json()
        assert result['count'] > 1
    p.join(WAIT_TIMEOUT)

    p = start_server(l)
    with l:
        resp = requests.get('http://127.0.0.1:9000/v1/limitedusers', params={'__limit': 1,
                                                                      '__orders': 'id',
                                                                      'id__ilike': '1',
                                                                      '__fields': 'id'})
        result = resp.json()
        assert result['count'] == 1
    p.join(WAIT_TIMEOUT)
