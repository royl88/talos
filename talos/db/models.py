# coding=utf-8
"""
本模块包含数据库模型

"""
from __future__ import absolute_import

from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
metadata = Base.metadata


def get_names():
    """
    获取所有Model类名
    """
    return Base._decl_class_registry.keys()


def get_class_by_name(name):
    """
    根据Model类名获取类

    :param name: Model类名
    :type name: str
    :returns: Model类
    :rtype: class
    """
    return Base._decl_class_registry.get(name, None)


def get_class_by_tablename(tablename):
    """
    根据表名获取类

    :param tablename: 表名
    :type tablename: str
    :returns: Model类
    :rtype: class
    """
    for c in Base._decl_class_registry.values():
        if hasattr(c, '__tablename__') and c.__tablename__ == tablename:
            return c


def get_tablename_by_name(name):
    """
    根据Model类名获取表名

    :param name: Model类名
    :type name: str
    :returns: 表名
    :rtype: str
    """
    return Base._decl_class_registry.get(name, None).__tablename__


def get_name_by_class(modelclass):
    """
    根据Model类获取类名

    :param modelclass: Model类
    :type modelclass: class
    :returns: 类名
    :rtype: str
    """
    for n, c in Base._decl_class_registry.items():
        if c == modelclass:
            return n
