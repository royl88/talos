# coding=utf-8
${coding}

from __future__ import absolute_import

from ${pkg_name}.apps.${app_name} import ${app_name}_controller


def add_routes(api):
    api.add_route('/v1/${pkg_name}/${app_name}s', ${app_name}_controller.Collection${app_name.upper()}())
    api.add_route('/v1/${pkg_name}/${app_name}/{rid}', ${app_name}_controller.Item${app_name.upper()}())
