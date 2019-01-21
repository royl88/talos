# coding=utf-8

from falcon import testing
import pytest
from pprint import pprint

from talos.server import base
from talos.db import crud
import models

base.initialize_server('test', './tests/unittest.conf')


class Department(crud.ResourceBase):
    orm_meta = models.Department


class User(crud.ResourceBase):
    orm_meta = models.User


class Address(crud.ResourceBase):
    orm_meta = models.Address


def test_list():
    users = User().list(filters={'$or': [{'id': '1'}, {'id': '3'}]})
    assert len(users) == 2
    for u in users:
        assert u['id'] in ('1', '3')

