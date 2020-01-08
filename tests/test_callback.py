# coding=utf-8

import logging
import pytest
import threading as concurrent
from wsgiref.simple_server import make_server
from tests import API

from talos.core import config
from talos.core import exceptions

from tests.apps.cats import callback

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


def test_add_local():
    ret = callback.add(None, x=1, y=8)
    assert ret['result'] == 9


def test_add_remmote():
    l = concurrent.Lock()
    p = start_server(l)
    
    with l:
        ret = callback.add.remote(None, x=3, y=4)
        assert ret['result'] == 7
    p.join()


def test_timeout_baseurl():
    with pytest.raises(exceptions.CallBackError):
        ret = callback.timeout.baseurl('http://1.2.3.4:9000').context(timeout=3.0).remote(None)


def test_timeout_context():
    l = concurrent.Lock()
    p = start_server(l)
    with pytest.raises(exceptions.CallBackError):
        with l:
            ret = callback.timeout.context(timeout=1).remote(None)
    p.join()


def test_limited_hosts():
    with pytest.raises(exceptions.CallBackError, match='not allow'):
        l = concurrent.Lock()
        p = start_server(l)
        with l:
            ret = callback.limithosts.remote(None)
        p.join()


def test_add_backward_compatible():
    l = concurrent.Lock()
    p = start_server(l)
    with l:
        ret = callback.add_backward_compatible.remote({'hello':'world'}, task_id='t1')
        assert ret == {'task_id': 't1', 'data': {'hello':'world'}}
    p.join()
    p = start_server(l)
    with l:
        ret = callback.add_backward_compatible.remote(data={'hello':'world'}, task_id='t1')
        assert ret == {'task_id': 't1', 'data': {'hello':'world'}}
    p.join()
    p = start_server(l)
    with l:
        ret = callback.async_helper.send_callback(None, callback.add_backward_compatible,
                                            data={'hello':'world'},
                                            task_id='t1')
        assert ret == {'task_id': 't1', 'data': {'hello':'world'}}
    p.join()
