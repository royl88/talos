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


CONF = config.CONF
CACHE = make_region().configure(
    CONF.cache.type,  # dogpile.cache.redis
    expiration_time=CONF.cache.expiration_time or 3600,
    arguments=CONF.cache.arguments.to_dict()
    #     {
    #         'host': 'localhost',
    #         'password': '',
    #         'port': 6379,
    #         'db': 0,
    #         'redis_expiration_time': 60*60*2,   # 2 hours
    #         'distributed_lock': True
    #     }
)


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
