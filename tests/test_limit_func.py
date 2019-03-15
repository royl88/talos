# coding=utf-8

from __future__ import absolute_import

import time
import functools
import pytest
import random

from talos.common import decorators as deco
from talos.common import limitwrapper


def timecost(func):

    @functools.wraps(func)
    def _timecost(*args, **kwargs):
        s = time.time()
        r = func(*args, **kwargs)
        m = func.__module__ + '.' + func.__class__.__name__ + ':' + func.__name__ + 'cost: %s' % (time.time() - s)
        print(m)
        return r

    return _timecost


@deco.flimit('2/second', storage='memory://')
def add(x, y):
    return x + y


@deco.flimit('5/3second', storage='memory://')
@deco.flimit('2/second', storage='memory://')
def mul(x, y):
    return x * y


@deco.flimit('2/second;5/3second', storage='memory://')
def div(x, y):
    return x / y


@deco.flimit('2/second;5/3second', storage='memory://')
@timecost
def add_1(x, y):
    return x + y


@timecost
@deco.flimit('2/second;5/3second', storage='memory://')
def add_2(x, y):
    return x + y


@deco.flimit('5/3second', storage='memory://')
@timecost
@deco.flimit('2/second', storage='memory://')
def add_3(x, y):
    return x + y


@deco.flimit('2/second', scope='add_4', storage='memory://')
def add_4_share_scope(x, y):
    return x + y


@deco.flimit('2/second', scope='add_4', storage='memory://')
def add_5_share_scope(x, y):
    return x + y


@deco.flimit('2/second', key_func=lambda x, y:str(x + y), scope='add_6', storage='memory://')
def add_6_share_key(x, y):
    return x + y


@deco.flimit('2/second', key_func=lambda x, y:str(x + y), scope='add_7', storage='memory://')
def add_7_share_key(x, y):
    return x + y


@deco.flimit('2/second', message='ooh, max access: %(limit)s time reach, you can retry after %(reset)s seconds', storage='memory://')
def add_8_msg(x, y):
    return x + y


def hit(result):
    if result is None:
        return True
    return False


@deco.flimit('2/second', storage='memory://', hit_func=hit, delay_hit=True)
def div_9(x, y):
    try:
        return x / y
    except ZeroDivisionError:
        pass
    
    
def class_instance_key(self, *args, **kwargs):
    return str(self)


class T1(object):

    @deco.flimit('2/second', storage='memory://')
    def add(self, x, y):
        return x + y
        
    @deco.flimit('5/3second', storage='memory://')
    @deco.flimit('2/second', storage='memory://')
    def mul(self, x, y):
        return x * y
        
    @deco.flimit('2/second;5/3second', storage='memory://')
    def div(self, x, y):
        return x / y
    
    @deco.flimit('2/second;5/3second', storage='memory://')
    @timecost
    def add_1(self, x, y):
        return x + y
    
    @timecost
    @deco.flimit('2/second;5/3second', storage='memory://')
    def add_2(self, x, y):
        return x + y
    
    @deco.flimit('5/3second', storage='memory://')
    @timecost
    @deco.flimit('2/second', storage='memory://')
    def add_3(self, x, y):
        return x + y
    
    @deco.flimit('2/second', key_func=class_instance_key, storage='memory://')
    def add_4(self, x, y):
        pass


def test_add_ok():
    add(1, 7)
    add(1, 7)


def test_add_limit():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        add(1, 7)
        add(1, 7)
        add(1, 7)


def test_mul_limit_1():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        mul(3, 7)
        mul(3, 7)
        mul(3, 7)


def test_mul_limit_2():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        mul(3, 7)
        mul(3, 7)
        time.sleep(1.1)
        mul(3, 7)
        mul(3, 7)
        mul(3, 7)
        mul(3, 7)


def test_div_limit_1():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        div(6, 3)
        div(6, 3)
        div(6, 3)


def test_div_limit_2():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        div(6, 3)
        div(6, 3)
        time.sleep(1.1)
        div(6, 3)
        div(6, 3)
        div(6, 3)
        div(6, 3)


def test_extradeco_ok():
    time.sleep(3.1)
    add_1(1, 7)
    add_1(1, 7)
    add_2(1, 7)
    add_2(1, 7)
    add_3(1, 7)
    add_3(1, 7)

    
def test_extradeco_limit():
    time.sleep(3.1)
    with pytest.raises(limitwrapper.RateLimitExceeded):
        add_1(1, 7)
        add_1(1, 7)
        add_1(1, 7)
    with pytest.raises(limitwrapper.RateLimitExceeded):
        add_2(1, 7)
        add_2(1, 7)
        add_2(1, 7)
    with pytest.raises(limitwrapper.RateLimitExceeded):
        add_3(1, 7)
        add_3(1, 7)
        add_3(1, 7)


def test_sharescope_limit():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        add_4_share_scope(1, 7)
        add_4_share_scope(1, 7)
        add_5_share_scope(1, 7)


def test_sharekey_ok():
    add_6_share_key(1, 1)
    add_6_share_key(1, 2)
    add_6_share_key(1, 3)
    add_6_share_key(1, 4)
    add_6_share_key(1, 5)
    add_6_share_key(1, 1)
    add_6_share_key(1, 6)
    add_6_share_key(1, 7)

        
def test_sharekey_limit():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        add_6_share_key(10, 7)
        add_6_share_key(10, 7)
        add_6_share_key(10, 7)
        add_7_share_key(10, 7)


def test_sharekey_difscope():
    add_6_share_key(100, 7)
    add_6_share_key(100, 7)
    add_7_share_key(100, 7)
    add_7_share_key(100, 7)


def test_msg():
    try:
        add_8_msg(1, 7)
        add_8_msg(1, 7)
        add_8_msg(1, 7)
    except limitwrapper.RateLimitExceeded as e:
        assert e.message.startswith('ooh, max access:')
    else:
        assert False


def test_delay_hit_ok():
    div_9(random.randint(0, 100), 3)
    div_9(random.randint(0, 100), 3)
    div_9(random.randint(0, 100), 3)
    div_9(6, 3)
    div_9(6, 3)
    div_9(6, 3)


def test_delay_hit_limit():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        div_9(6, 0)
        div_9(6, 0)
        div_9(6, 0)


def test_classadd_ok():
    time.sleep(1.1)
    a = T1()
    a.add(1, 7)
    a.add(1, 7)


def test_classadd_limit():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        time.sleep(1.1)
        a = T1()
        a.add(1, 7)
        a.add(1, 7)
        a.add(1, 7)


def test_classmul_limit_1():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        time.sleep(3.1)
        a = T1()
        a.mul(3, 7)
        a.mul(3, 7)
        a.mul(3, 7)


def test_classmul_limit_2():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        time.sleep(3.1)
        a = T1()
        a.mul(3, 7)
        a.mul(3, 7)
        time.sleep(1.1)
        a.mul(3, 7)
        a.mul(3, 7)
        a.mul(3, 7)
        a.mul(3, 7)


def test_classdiv_limit_1():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        time.sleep(3.1)
        a = T1()
        a.div(6, 3)
        a.div(6, 3)
        a.div(6, 3)


def test_classdiv_limit_2():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        time.sleep(3.1)
        a = T1()
        a.div(6, 3)
        a.div(6, 3)
        time.sleep(1.1)
        a.div(6, 3)
        a.div(6, 3)
        a.div(6, 3)
        a.div(6, 3)


def test_classextradeco_ok():
    time.sleep(3.1)
    a = T1()
    a.add_1(1, 7)
    a.add_1(1, 7)
    a.add_2(1, 7)
    a.add_2(1, 7)
    a.add_3(1, 7)
    a.add_3(1, 7)

    
def test_classextradeco_limit():
    time.sleep(3.1)
    a = T1()
    with pytest.raises(limitwrapper.RateLimitExceeded):
        a.add_1(1, 7)
        a.add_1(1, 7)
        a.add_1(1, 7)
    with pytest.raises(limitwrapper.RateLimitExceeded):
        a.add_2(1, 7)
        a.add_2(1, 7)
        a.add_2(1, 7)
    with pytest.raises(limitwrapper.RateLimitExceeded):
        a.add_3(1, 7)
        a.add_3(1, 7)
        a.add_3(1, 7)


def test_classinstance_ok():
    a1 = T1()
    a1.add_4(1, 7)
    a1.add_4(1, 7)
    a2 = T1()
    a2.add_4(1, 7)
    a2.add_4(1, 7)
    a3 = T1()
    a3.add_4(1, 7)
    a3.add_4(1, 7)


def test_class_limit():
    with pytest.raises(limitwrapper.RateLimitExceeded):
        time.sleep(1.1)
        a1 = T1()
        a1.add(1, 7)
        a1.add(1, 7)
        a2 = T1()
        a2.add(1, 7)
