# coding=utf-8
"""
talos.common.ldap
~~~~~~~~~~~~~~~~~

本模块提供AD功能集成

"""

from __future__ import absolute_import

import logging


try:
    # windows机器导入会抛异常  一般用于调试
    import ldap
    import ldap.controls
except:
    pass


LOG = logging.getLogger(__name__)

AD_PORT_SSL = 636
AD_PORT = 389
AD_PAGE_SIZE = 1000


class Ldap(object):
    def __init__(self, server, base_dn, port=None, admin=None, password=None, account_suffix=None,
                 use_ssl=False,
                 account_key='sAMAccountname',
                 user_attrs=None):
        self.base_dn = base_dn
        self.admin_username = admin
        self.admin_password = password
        self.use_ssl = use_ssl
        self.account_suffix = account_suffix or ''
        self.account_key = account_key
        self.user_attrs = user_attrs or ['cn', 'name', 'mail', 'telephoneNumber', 'mobile',
                                         'department', 'company', 'sAMAccountName']
        self.port = port
        if self.use_ssl and not port:
            self.port = AD_PORT_SSL
        if not self.use_ssl and not port:
            self.port = AD_PORT
        if use_ssl:
            server = 'ldaps://%s:%d/' % (server, self.port)
        else:
            server = 'ldap://%s:%d/' % (server, self.port)
        self.ldap_connection = ldap.initialize(server)
        # 关闭MS AD的referrals特性(OpenLDAPv3兼容问题)
        self.ldap_connection.set_option(ldap.OPT_REFERRALS, 0)
        self.ldap_connection.protocol_version = 3
        if self.admin_username is not None and self.admin_password is not None:
            username = '%s%s' % (self.admin_username, self.account_suffix)
            self.ldap_connection.simple_bind_s(username, self.admin_password)

    @classmethod
    def dict_to_filter(cls, data):
        results = []
        for key, value in data.items():
            results.append('(%s=%s)' % (key, value))
        return '(&%s)' % (''.join(results))

    def authenticate(self, username, password, rebind=True):
        filters = '(&(%s=%s)(objectCategory=person))' % (self.account_key, username)
        username = '%s%s' % (username, self.account_suffix)
        try:
            self.ldap_connection.simple_bind_s(username, password)
            result = self.ldap_connection.search_s(self.base_dn,
                                                   ldap.SCOPE_SUBTREE,
                                                   filters,
                                                   self.user_attrs)
            if result:
                addata = result[0][1]
                data = {}
                for attr in self.user_attrs:
                    data[attr] = addata.get(attr, [None])[0]
                return data
            else:
                return None
        except ldap.INVALID_CREDENTIALS as e:
            LOG.exception(e)
            return False
        finally:
            if rebind and self.admin_username and self.admin_password:
                self.ldap_connection.simple_bind_s(self.admin_username, self.admin_password)

    def users(self, filters=None, attrs=None):
        results = []
        filters = filters or 'objectCategory=person'
        pg_ctrl = ldap.controls.SimplePagedResultsControl(True, size=AD_PAGE_SIZE, cookie="")
        attrs = attrs or self.user_attrs
        try:
            while True:
                msgid = self.ldap_connection.search_ext(self.base_dn,
                                                        ldap.SCOPE_SUBTREE,
                                                        filters,
                                                        attrs,
                                                        serverctrls=[pg_ctrl])
                _a, res_data, _b, srv_ctrls = self.ldap_connection.result3(msgid)
                if res_data:
                    for r in res_data:
                        r = r[1]
                        data = {}
                        for attr in attrs:
                            data[attr] = r.get(attr, [None])[0]
                        results.append(data)
                cookie = srv_ctrls[0].cookie
                if cookie:
                    pg_ctrl.cookie = cookie
                else:
                    break
        except ldap.INVALID_CREDENTIALS as e:
            LOG.exception(e)
        return results
