# coding=utf-8

import logging
import requests
import threading as concurrent
import collections
from wsgiref.simple_server import make_server

from talos.core import config
from talos.common import controller

from tests import API, MockRequest

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


def test_criteria():
    req = MockRequest()
    req.params = collections.OrderedDict(age='1', name__ilike='a', __limit='10', __offset='20', __orders='-name', __fields='id')
    criteria = controller.Controller()._build_criteria(req)
    assert criteria['filters']['age'] == '1'
    assert criteria['filters']['name']['ilike'] == 'a'
    assert criteria['offset'] == 20
    assert criteria['limit'] == 10
    assert criteria['orders'] == ['-name']
    assert criteria['fields'] == ['id']

    req = MockRequest()
    req.params = collections.OrderedDict(name__ilike='a', name__ne='b')
    criteria = controller.Controller()._build_criteria(req)
    assert criteria['filters'] == {'name': {'ilike': 'a', 'ne': 'b'}}

    req = MockRequest()
    req.params = collections.OrderedDict()
    req.params['name'] = ['a', 'b', 'c']
    criteria = controller.Controller()._build_criteria(req)
    assert criteria['filters'] == {'name': ['a', 'b', 'c']}

    req = MockRequest()
    req.params = collections.OrderedDict()
    req.params['name[]'] = ['a', 'b', 'c']
    criteria = controller.Controller()._build_criteria(req)
    assert criteria['filters'] == {'name': ['a', 'b', 'c']}

    req = MockRequest()
    req.params = collections.OrderedDict()
    req.params['name[0]'] = 'a'
    req.params['name[1]'] = 'b'
    req.params['name[2]'] = 'c'
    criteria = controller.Controller()._build_criteria(req)
    assert criteria['filters'] == {'name': ['a', 'b', 'c']}

    # 不同版本OrderedDict的kwargs初始化方式可能会得到不同的排序结果
    # 但这不意味着_build_criteria的处理方式不正确，因此本用例被注释，详见下一用例
    # req = MockRequest()
    # req.params = collections.OrderedDict(name__ilike='a', name__ne='b', name='c')
    # criteria = controller.Controller()._build_criteria(req)
    # assert criteria['filters'] == {'name': 'c'}

    req = MockRequest()
    req.params = collections.OrderedDict()
    req.params['name__ilike'] = 'a'
    req.params['name__ne'] = 'b'
    req.params['name'] = 'c'
    criteria = controller.Controller()._build_criteria(req)
    assert criteria['filters'] == {'name': 'c'}

    req = MockRequest()
    req.params = collections.OrderedDict()
    req.params['name'] = 'c'
    req.params['name__ilike'] = 'a'
    req.params['name__ne'] = 'b'
    criteria = controller.Controller()._build_criteria(req)
    assert criteria['filters'] == {'name': {'ilike': 'a', 'ne': 'b'}}


def test_criteria_supported():
    req = MockRequest()
    req.params = collections.OrderedDict()
    req.params['name__ilike'] = 'a'
    req.params['name__ne'] = 'a'
    req.params['name__lte'] = 'a'
    req.params['name__gte'] = 'a'
    req.params['name__null'] = 'a'
    criteria = controller.Controller()._build_criteria(req, ['name'])
    assert criteria['filters'] == {'name': {'ilike': 'a',
                                            'ne': 'a',
                                            'lte': 'a',
                                            'gte': 'a',
                                            'null': 'a'}}
    
    criteria = controller.Controller()._build_criteria(req, ['name(__(ilike|lte))?$'])
    assert criteria['filters'] == {'name': {'ilike': 'a',
                                            'lte': 'a'}}

    criteria = controller.Controller()._build_criteria(req, ['name__(ilike|nnull)$'])
    assert criteria['filters'] == {'name': {'ilike': 'a'}}

    req = MockRequest()
    req.params = collections.OrderedDict()
    req.params['name'] = ['1', '2']
    criteria = controller.Controller()._build_criteria(req, ['name(__(ilike|lte))?$'])
    assert criteria['filters'] == {'name': ['1', '2']}

    criteria = controller.Controller()._build_criteria(req, ['name__(ilike|lte)$'])
    assert criteria['filters'] == {}


def test_criteria_unsupported_as_empty():
    try:
        origin_conf_val = CONF.dbcrud.unsupported_filter_as_empty
        CONF.to_dict()['dbcrud']['unsupported_filter_as_empty'] = True
        req = MockRequest()
        req.params = collections.OrderedDict()
        req.params['name__ilike'] = 'a'
        req.params['name__ne'] = 'a'
        req.params['name__lte'] = 'a'
        req.params['name__gte'] = 'a'
        req.params['name__null'] = 'a'
        criteria = controller.Controller()._build_criteria(req, ['name'])
        assert criteria['filters'] == {'name': {'ilike': 'a',
                                                'ne': 'a',
                                                'lte': 'a',
                                                'gte': 'a',
                                                'null': 'a'}}

        criteria = controller.Controller()._build_criteria(req, ['name(__(ilike|lte))?$'])
        assert criteria is None

        criteria = controller.Controller()._build_criteria(req, ['name__(ilike|nnull)$'])
        assert criteria is None

        req = MockRequest()
        req.params = collections.OrderedDict()
        req.params['name'] = ['1', '2']
        criteria = controller.Controller()._build_criteria(req, ['name(__(ilike|lte))?$'])
        assert criteria['filters'] == {'name': ['1', '2']}

        criteria = controller.Controller()._build_criteria(req, ['name__(ilike|lte)$'])
        assert criteria is None
    finally:
        CONF.to_dict()['dbcrud']['unsupported_filter_as_empty'] = origin_conf_val
