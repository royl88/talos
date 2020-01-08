# coding=utf-8

import logging
import time

from talos.db import crud
from talos.core import config
from talos.core import exceptions
from talos.common import async_helper


CONF = config.CONF
LOG = logging.getLogger(__name__)


@async_helper.callback('/callback/add/{x}/{y}', name='callback.add')
def add(data, x, y):
    if data is not None:
        raise exceptions.ValidationError(attribute='data', msg='not None')
    return {'result': int(x) + int(y)}


@async_helper.callback('/callback/timeout', name='callback.timeout')
def timeout(data):
    time.sleep(2)
    return data


@async_helper.callback('/callback/limithosts', name='callback.limithosts')
def limithosts(data):
    return data


@async_helper.callback('/callback/add_backward_compatible/{task_id}/make', name='callback.add')
def add_backward_compatible(task_id, data, request=None, response=None):
    if task_id != 't1':
        raise exceptions.ValidationError(attribute='task_id', msg='shuould be: %s, not: %s' % ('t1', task_id))
    if data != {'hello':'world'}:
        raise exceptions.ValidationError(attribute='data', msg='shuould be: %s, not: %s' % ({'hello':'world'},
                                                                                            data))
    return {'task_id': task_id, 'data': data}
