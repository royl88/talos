# coding=utf-8

from talos.common import controller
from tests.apps.cats import api


class CollectionUser(controller.CollectionController):
    name = 'users'
    resource = api.User


class ItemUser(controller.ItemController):
    name = 'user'
    resource = api.User
