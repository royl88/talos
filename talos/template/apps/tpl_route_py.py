# coding=utf-8

TEMPLATE = '''# coding=utf-8

from __future__ import absolute_import

from ${pkg_name}.apps.${app_name} import controller


def add_routes(api):
    api.add_route('/v1/${pkg_name}/${app_name}s', controller.Collection${app_name.upper()}())
    api.add_route('/v1/${pkg_name}/${app_name}s/{rid}', controller.Item${app_name.upper()}())
'''
