# coding=utf-8

from tests.apps.cats import controller
from tests.apps.cats import callback
from talos.common import async_helper


def add_routes(api):
    api.add_route('/v1/limitedusers', controller.CollectionQueryLimitedUser())
    api.add_route('/v1/users', controller.CollectionUser())
    api.add_route('/v1/users/{rid}', controller.ItemUser())
    async_helper.add_callback_route(api, callback.add)
    async_helper.add_callback_route(api, callback.timeout)
    async_helper.add_callback_route(api, callback.limithosts)
    async_helper.add_callback_route(api, callback.add_backward_compatible)
