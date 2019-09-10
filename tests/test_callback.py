# coding=utf-8

import time
import logging
import pytest
import multiprocessing
from wsgiref.simple_server import make_server

from talos.core import config
from talos.core import exceptions

from tests.apps.cats import callback


LOG = logging.getLogger(__name__)
CONF = config.CONF


def proc(lock):
    try:
        from talos.server import base
        application = base.initialize_server('test', './tests/unittest.conf')

        bind_addr = CONF.server.bind
        port = CONF.server.port
        print("try 'pip install gevent' to boost simple server")
        print("Serving on %s:%d..." % (bind_addr, port))
        httpd = make_server(bind_addr, port, application)
    finally:
        lock.release()
    httpd.handle_request()


def start_server(lock):
    lock.acquire()
    p = multiprocessing.Process(target=proc, args=(lock, ))
    p.start()
    return p


def test_add_local():
    ret = callback.add(None, x=1, y=8)
    assert ret['result'] == 9


def test_add_remmote():
    l = multiprocessing.Lock()
    p = start_server(l)
    time.sleep(1.0)
    with l:
        ret = callback.add.remote(None, x=3, y=4)
        assert ret['result'] == 7
    # p.join()


def test_timeout_baseurl():
    l = multiprocessing.Lock()
    p = start_server(l)
    time.sleep(1.0)
    with pytest.raises(exceptions.CallBackError):
        with l:
            ret = callback.timeout.baseurl('http://1.2.3.4:9000').context(timeout=3).remote(None)
    # p.join()


def test_timeout_context():
    l = multiprocessing.Lock()
    p = start_server(l)
    time.sleep(1.0)
    with pytest.raises(exceptions.CallBackError):
        with l:
            ret = callback.timeout.context(timeout=1).remote(None)
    # p.join()
