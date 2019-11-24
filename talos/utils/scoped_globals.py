# coding=utf-8

from __future__ import absolute_import


_GREENLET = False
try:
    import gevent.local
    _GREENLET = True
except:
    import threading

# 使用方式，默认隐含请求中的4个参数
# from talos.utils.scoped_globals import GLOBALS
# GLOBALS.request 请求对象
# GLOBALS.response 响应对象
# GLOBALS.controller Controller对象
# GLOBALS.route_params route模板的匹配值
if _GREENLET:
    GLOBALS = gevent.local.local()
else:
    GLOBALS = threading.local()
