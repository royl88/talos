# coding=utf-8
"""
本模块提供各类装饰器

"""

from __future__ import absolute_import

import functools
import sys
import threading


def singleton(cls):
    """单例模式装饰器"""
    instances = {}
    lock = threading.Lock()

    def _singleton(*args, **kwargs):
        with lock:
            fullkey = str((cls.__module__, cls.__name__, tuple(args), tuple(kwargs.items())))
            if fullkey not in instances:
                instances[fullkey] = cls(*args, **kwargs)
        return instances[fullkey]

    return _singleton


def require(mod_name, attr_name):
    '''
    基于描述符的延迟加载

    :param mod_name: a.b.c:class
    :param attr_name: attrubute name
    '''

    class _lazy_attribute(object):

        def __init__(self, mod_name):
            mods = mod_name.split(':')
            self.mod_name = mods[0]
            self.attr_name = mods[1] if len(mods) > 1 else None

        def __get__(self, instance, owner):
            if self.mod_name not in sys.modules:
                __import__(self.mod_name)
            mod = sys.modules[self.mod_name]
            if self.attr_name:
                return getattr(mod, self.attr_name)
            return mod

    def _require_api(cls):

        def __require_api(*args, **kwargs):
            setattr(cls, attr_name, _lazy_attribute(mod_name))
            instance = cls(*args, **kwargs)
            return instance

        return __require_api

    return _require_api
