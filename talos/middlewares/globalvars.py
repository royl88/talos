# coding=utf-8

from __future__ import absolute_import

from talos.utils import scoped_globals


class GlobalVars(object):
    """中间件，提供线程级的全局request, response参数"""

    def process_request(self, req, resp):
        scoped_globals.GLOBALS.request = req
        scoped_globals.GLOBALS.response = resp

    def process_resource(self, req, resp, resource, params):
        scoped_globals.GLOBALS.controller = resource
        scoped_globals.GLOBALS.route_params = params
