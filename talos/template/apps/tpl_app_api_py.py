# coding=utf-8

TEMPLATE = u'''${sys_default_coding}

from __future__ import absolute_import

import logging

LOG = logging.getLogger(__name__)

class Resource(object):
    def create(self, data):
        return data

    def list(self, filters=None, orders=None, offset=None, limit=None):
        return [{'id': 1, 'name': 'helloworld'}]

    def count(self, filters=None, offset=None, limit=None):
        return 1

    def update(self, rid, data):
        return data, data

    def get(self, rid):
        return {'id': 1, 'name': 'helloworld'}

    def delete(self, rid):
        return 0, None
'''