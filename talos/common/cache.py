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
                "distributed_lock": true,
                "lock_timeout": 30 # 当使用分布式锁时，需要设置此项
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

import contextlib
import logging

from dogpile.cache import make_region
from dogpile.cache.api import NO_VALUE
from talos.core import config
from talos.core import utils

CONF = config.CONF
LOG = logging.getLogger(__name__)


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


@contextlib.contextmanager
def distributed_lock(key, blocking=True):
    '''
    基于cache的简单分布式锁，使用dogpile.cache.redis/dogpile.cache.memcached时
    
    * 必须设置distributed_lock=true
    * 可以设置lock_timeout代表单次上锁可以维持的时间(秒)，如果上锁超过lock_timeout，锁会被自动释放以防止死锁，如果不设置，默认不会自动释放
    * dogpile中以redis，memcached为后端，锁是跨越线程,进程,主机的
    * dogpile中以dbm为后端，锁是跨越线程,进程的
    * dogpile中以memory为后端，锁是跨越线程
    
    使用方式：
    
    with distributed_lock(key) as locked:
    if locked:
        # 获取到锁，进行处理
    else:
        # 未获取到锁

    :param key: 锁的名称
    :param blocking: 是否阻塞式申请锁
    '''
    lock = CACHE.backend.get_mutex(key)
    try:
        # blocking=True(默认)时，进入with代表一定是获取到锁，locked主要用于blocking=False时的判断
        locked = lock.acquire(blocking)
        yield locked
    finally:
        # 锁可能会被自动释放引发异常
        try:
            if locked:
                lock.release()
        except Exception as e:
            LOG.warning('exception raised when release lock: %s, reason: %s' % (key, e))
