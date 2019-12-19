# coding=utf-8

from __future__ import absolute_import

import time

from talos.common import cache


def test_cache():
    key = 'talos.unittest.1'
    val = '2'
    cache.set(key, val)
    key = 'talos.unittest.1'
    ret = cache.get(key)
    assert cache.validate(ret) is True
    assert ret == val
    # more than exipres: 1
    time.sleep(1.2)
    ret = cache.get(key)
    assert cache.validate(ret) is False

    key = 'talos.unittest.2'
    val = 'val'
    creator = lambda: val
    cache.get_or_create(key, creator, expires=0.1)
    ret = cache.get(key)
    assert ret == val
    cache.delete(key)
    ret = cache.get(key)
    assert cache.validate(ret) is False

