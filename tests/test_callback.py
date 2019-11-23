# coding=utf-8

import logging
import pytest
import multiprocessing as concurrent
from wsgiref.simple_server import make_server

from talos.server import base
from talos.core import config
from talos.core import exceptions

from tests.apps.cats import callback

LOG = logging.getLogger(__name__)
CONF = config.CONF


def _server_proc(l):
    try:
        application = base.initialize_server('test', './tests/unittest.conf')
        bind_addr = CONF.server.bind
        port = CONF.server.port
        print("Serving on %s:%d..." % (bind_addr, port))
        httpd = make_server(bind_addr, port, application)
    finally:
        l.release()
    httpd.handle_request()


def start_server(lock):
    lock.acquire()
    p = concurrent.Process(target=_server_proc, args=(lock,))
    p.start()
    return p


def test_add_local():
    ret = callback.add(None, x=1, y=8)
    assert ret['result'] == 9


def test_add_remmote():
    l = concurrent.Lock()
    p = start_server(l)
    
    try:
        l.acquire(timeout=20)
        ret = callback.add.remote(None, x=3, y=4)
        assert ret['result'] == 7
    finally:
        l.release()
    p.join()


def test_timeout_baseurl():
    with pytest.raises(exceptions.CallBackError):
        ret = callback.timeout.baseurl('http://1.2.3.4:9000').context(timeout=3.0).remote(None)


def test_timeout_context():
    l = concurrent.Lock()
    p = start_server(l)
    with pytest.raises(exceptions.CallBackError):
        try:
            l.acquire(timeout=20)
            ret = callback.timeout.context(timeout=1).remote(None)
        finally:
            l.release()
    p.join()
