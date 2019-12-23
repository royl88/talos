from talos.server import base

API = base.initialize_server('test', './tests/unittest.conf')


class MockRequest(object):
    method = 'GET'
    path = '/'
    params = {}
    json = {}
