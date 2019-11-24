# coding=utf-8

import logging

from talos.db import crud, pool
from talos.core import config

from tests import models

LOG = logging.getLogger(__name__)
CONF = config.CONF


class _User(crud.ResourceBase):
    '''
    use db as default
    '''
    orm_meta = models.User
    _default_order = ['id']


class _User_01(crud.ResourceBase):
    '''
    use dbs.db01 as default
    '''
    orm_meta = models.User
    orm_pool = pool.POOLS.db01
    _default_order = ['id']


class _User_02(crud.ResourceBase):
    '''
    use dbs.db02 as default
    '''
    orm_meta = models.User
    orm_pool = pool.POOLS.db02
    _default_order = ['id']


class _User_dynamic(crud.ResourceBase):
    '''
    use __init__(dbpool) as default, fallback default if dbpool not exist
    '''
    orm_meta = models.User
    _default_order = ['id']


class _User_None(crud.ResourceBase):
    '''
    fallback db as default
    '''
    orm_meta = models.User
    orm_pool = pool.POOLS.db101
    _default_order = ['id']


def test_default():
    users = _User().list()
    assert len(users) > 3
    for u in users:
        assert u['name'] not in ['multi_01_01', 'multi_01_02', 'multi_01_03']


def test_db_01():
    users = _User_01().list()
    assert len(users) == 3
    for u in users:
        assert u['name'] in ['multi_01_01', 'multi_01_02', 'multi_01_03']


def test_db_02():
    users = _User_02().list()
    assert len(users) == 3
    for u in users:
        assert u['name'] in ['multi_02_01', 'multi_02_02', 'multi_02_03']


def test_db_dynamic():
    users = _User_dynamic(dbpool=pool.POOLS.db03).list()
    assert len(users) == 3
    for u in users:
        assert u['name'] in ['multi_03_01', 'multi_03_02', 'multi_03_03']


def test_db_none():
    users = _User_None().list()
    assert len(users) > 3
    for u in users:
        assert u['name'] not in ['multi_01_01', 'multi_01_02', 'multi_01_03']


def test_db_dynamic_none():
    users = _User_dynamic(dbpool=pool.POOLS.db101).list()
    assert len(users) > 3
    for u in users:
        assert u['name'] not in ['multi_01_01', 'multi_01_02', 'multi_01_03']
