# coding=utf-8

import logging
import pytest
import requests
import threading as concurrent
from wsgiref.simple_server import make_server

from talos.core import config
from talos.db import crud

from tests import API


LOG = logging.getLogger(__name__)
CONF = config.CONF



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
    p.join()


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
    p.join()


def test_get_user():
    l = concurrent.Lock()
    p = start_server(l)

    with l:
        resp = requests.get('http://127.0.0.1:9000/v1/users/1')
        result = resp.json()
        assert result['id'] == '1'
    p.join()


def test_method_not_allow():
    l = concurrent.Lock()
    p = start_server(l)

    with l:
        resp = requests.patch('http://127.0.0.1:9000/v1/users')
        assert resp.status_code == 405
    p.join()


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
    p.join()

    l = concurrent.Lock()
    p = start_server(l)

    with l:
        resp = requests.get('http://127.0.0.1:9000/v1/limitedusers', params={'__limit': 1,
                                                                      '__orders': 'id',
                                                                      'id__ilike': '1',
                                                                      '__fields': 'id'})
        result = resp.json()
        assert result['count'] == 1
    p.join()
