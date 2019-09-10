# coding=utf-8

import logging
import time

from talos.db import crud
from talos.core import config
from talos.common import async_helper


CONF = config.CONF
LOG = logging.getLogger(__name__)


@async_helper.callback('/callback/add/{x}/{y}', name='callback.add')
def add(data, x, y):
    return {'result': int(x) + int(y)}


@async_helper.callback('/callback/timeout', name='callback.timeout')
def timeout(data):
    time.sleep(2)
    return data
