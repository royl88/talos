# coding=utf-8

TEMPLATE = u'''${sys_default_coding}

from __future__ import absolute_import

from talos.common.controller import CollectionController
from talos.common.controller import ItemController
from ${pkg_name}.apps.${app_name} import api as ${app_name}_api


class Collection${app_name.upper()}(CollectionController):
    name = '${pkg_name}.${app_name}s'
    resource = ${app_name}_api.Resource


class Item${app_name.upper()}(ItemController):
    name = '${pkg_name}.${app_name}'
    resource = ${app_name}_api.Resource
'''