# coding=utf-8

from __future__ import absolute_import

from talos.core import decorators as deco


class ClassAttr(object):

    def __init__(self):
        self.hello = 'world'


@deco.require('tests.test_decorator:ClassAttr', 'backend')
class MyClass(object):

    def tryme(self):
        return self.backend().hello


def test_deco_require():
    assert MyClass().tryme() == 'world'

