# coding=utf-8
import tempfile

from talos.tools import project


def test_create():
    temppath = tempfile.mkdtemp()
    project.create_project(temppath, 'test', '1.0', 'test', 'test@test.com',
                           './etc', 'mysql://root:123456@127.0.0.1/test')
    project.create_app(temppath, 'test', 'user')
