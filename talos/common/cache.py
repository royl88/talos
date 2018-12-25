# coding=utf-8
"""
依赖: 
    库:
        -- dogpile.cache
        -- redis
    配置:
        -- 
        "cache": {
            "type": "dogpile.cache.redis",
            "expiration_time": 6,
            "arguments": {
                "host": "127.0.0.1",
                "password": "",
                "port": 6379,
                "db": 0,
                "redis_expiration_time": 21600,
                "distributed_lock": true
            }
        }

使用方式:
    get(key)
    set(key, value)
    get_or_create(key, func_value)
    delete(key)
    validate(get(key))
"""

from __future__ import absolute_import

from dogpile.cache import make_region
from dogpile.cache.api import NO_VALUE
from talos.core import config
from talos.core import utils


CONF = config.CONF


class CacheProxy(object):
    def __init__(self):
        self.cache = None

    def __getattr__(self, name):
        """
        魔法函数，实现.操作符访问

        :param name: 配置项
        :type name: string
        :returns: 原属性
        :rtype: any
        :raises: KeyError
        """
        if self.cache is None:
            self.cache = make_region().configure(
                # dogpile.cache.redis, dogpile.cache.memory
                CONF.cache.type,
                expiration_time=CONF.cache.expiration_time or 3600,
                #  for redis
                #     {
                #         'host': 'localhost',
                #         'password': '',
                #         'port': 6379,
                #         'db': 0,
                #         'redis_expiration_time': 60*60*2,   # 2 hours
                #         'distributed_lock': True
                #     }
                arguments=CONF.cache.arguments.to_dict() if \
                utils.get_config(CONF, 'cache.arguments', None) is not None else None
            )
        return getattr(self.cache, name)


CACHE = CacheProxy()


def validate(value):
    if value == NO_VALUE:
        return False
    return True


def get(key, exipres=None):
    value = CACHE.get(key, expiration_time=exipres)
    return value


def set(key, value):
    return CACHE.set(key, value)


def get_or_create(key, creator, expires=None):
    value = get(key, exipres=expires)
    if not validate(value):
        value = creator()
        set(key, value)
    return value


def delete(key):
    return CACHE.delete(key)
