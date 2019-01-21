# coding=utf-8

import pytest

from talos.server import base
from talos.db import crud
import models


base.initialize_server('test', './tests/unittest.conf')


class _Department(crud.ResourceBase):
    orm_meta = models.Department


class _User(crud.ResourceBase):
    orm_meta = models.User


class _Address(crud.ResourceBase):
    orm_meta = models.Address


def test_list_one():
    users = _User().list(filters={'id': '1'})
    assert len(users) == 1
    for u in users:
        assert u['id'] == '1'


def test_list_two():
    users = _User().list(filters={'id': '2', 'name': 'wan'})
    assert len(users) == 1
    for u in users:
        assert u['id'] == '2'


def test_list_or():
    users = _User().list(filters={'$or': [{'id': '1'}, {'id': '3'}]})
    assert len(users) == 2
    for u in users:
        assert u['id'] in ('1', '3')
        
def test_list_and():
    users = _User().list(filters={'$and': [{'id': '3'}, {'name': 'liu'}, {'department.id': '2'}]})
    assert len(users) == 1
    for u in users:
        assert u['id'] == '3'

def test_list_complicate():
    users = _User().list(filters={'$or': [
                                            {'$and': [{'id': '1'}, {'name': 'wu'}]},
                                            {'$and': [{'id': '2'}, {'name': 'wan'}]},
                                            {'id': '3'}
                                         ],
                                  }
                        )
    assert len(users) == 3
    for u in users:
        assert u['id'] in ('1', '2', '3')
