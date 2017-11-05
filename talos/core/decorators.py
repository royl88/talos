# coding=utf-8
"""
本模块提供各类装饰器

"""

from __future__ import absolute_import

import functools
import threading


def singleton(cls):
    """单例模式装饰器"""
    instances = {}
    lock = threading.Lock()

    def _singleton(*args, **kwargs):
        with lock:
            fullkey = str((cls.__name__, tuple(args), tuple(kwargs.items())))
            if fullkey not in instances:
                instances[fullkey] = cls(*args, **kwargs)
        return instances[fullkey]

    return _singleton
