# coding=utf-8

from talos.common import controller
from tests.apps.cats import api


class CollectionUser(controller.CollectionController):
    name = 'users'
    resource = api.User


class ItemUser(controller.ItemController):
    name = 'user'
    resource = api.User


class CollectionQueryLimitedUser(controller.CollectionController):
    name = 'limited.users'
    resource = api.User

    def _build_criteria(self, req, supported_filters=None):
        supported_filters = ['id__ilike']
        return controller.CollectionController._build_criteria(self, req, supported_filters=supported_filters)
