# coding=utf-8

from __future__ import absolute_import

import time

from talos.common import decorators as deco
from talos.common import limitwrapper


@deco.flimit('2/second', 't1', storage='memory://')
def t1():
    pass


@deco.flimit('1/second', 't1', storage='memory://')
@deco.flimit('3/second', 't1', storage='memory://')
def t2():
    pass

