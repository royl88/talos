# coding=utf-8

from __future__ import absolute_import

import logging
import sys

LOG = logging.getLogger(__name__)


class TMockCookie(object):

    def __init__(self, cookie=None):
        self.cookie = cookie


def test_ldap_auth(mocker):
    sys.modules['ldap'] = mocker.MagicMock()
    from talos.common import ldap_util
    mocker.patch('ldap.initialize')
    l = ldap_util.Ldap('127.0.0.1', 'OU=Users,DC=test,DC=com', 
                       admin='test', password='123', account_suffix='@example.com')
    l = ldap_util.Ldap('127.0.0.1', 'OU=Users,DC=test,DC=com', use_ssl=True,
                       admin='test', password='123', account_suffix='@example.com')
    l.authenticate('test', '123456')
    mocker.patch.object(l.ldap_connection, 'search_s', return_value=None)
    l.authenticate('test', '123456')


def test_ldap_user(mocker):
    sys.modules['ldap'] = mocker.MagicMock()
    from talos.common import ldap_util
    mocker.patch('ldap.initialize')
    mocker.patch('ldap.controls.SimplePagedResultsControl')
    _inner_params = {}
    def mock_result3(v):
        if v > 3:
            return None, [], None, [TMockCookie()]
        return None, [mocker.MagicMock()], None, [TMockCookie(1)]

    def mock_search_ext(*args, **kwargs):
        _inner_params.setdefault('counter', 0)
        _inner_params['counter'] += 1
        return _inner_params['counter']

    l = ldap_util.Ldap('127.0.0.1', 'OU=Users,DC=test,DC=com',
                       admin='test', password='123', account_suffix='@example.com')
    mocker.patch.object(l.ldap_connection, 'search_ext', side_effect=mock_search_ext)
    mocker.patch.object(l.ldap_connection, 'result3', side_effect=mock_result3)
    rets = l.users()
    assert len(rets) == 3
    # wo have not reset counter, will get 0 result set
    assert len(l.users()) == 0
