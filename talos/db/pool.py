# coding=utf-8
"""
本模块统一数据库连接池对象

"""

from __future__ import absolute_import

import sqlalchemy
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from talos.core import config
from talos.core import decorators as deco

CONF = config.CONF


class DBPool(object):
    """数据库连接池，单例模式"""

    def __init__(self, param=None):
        """初始化连接池

        :param params: 连接信息列表
        {connection: xxx, [pool_size: xxx], [pool_recycle: xxx], [pool_timeout: xxx], [max_overflow: xxx]}
        :type params: list
        :param connecter: 连接器，可选pymysql,psycopg2
        :type connecter: str
        :raises: None
        """
        if param:
            self.reflesh(param=param)

    def get_session(self):
        """从连接池中获取一个会话对象

        :returns: 会话对象
        :rtype: scoped_session
        :raises: ValueError
        """
        if self._pool:
            session = scoped_session(self._pool)
            return session
        raise ValueError('failed to get session')

    def transaction(self):
        """从连接池中获取一个事务对象

        :returns: 会话对象
        :rtype: scoped_session
        :raises: ValueError
        """
        if self._pool:
            session = scoped_session(self._pool)
            session.begin()
            return session
        raise ValueError('failed to get session')

    def reflesh(self, param):
        """
        重建连接池

        :param params: 连接信息列表
        {connection: xxx, [pool_size: xxx], [pool_recycle: xxx], [pool_timeout: xxx], [max_overflow: xxx]}
        :type params: list
        :param connector: 连接器，可选pymysql,psycopg2
        :type connector: str
        :returns: 是否重建成功
        :rtype: bool
        """
        param.setdefault('echo', CONF.log.level.upper() == 'DEBUG')
        connection = param.pop('connection')
        self._pool = sessionmaker(bind=sqlalchemy.create_engine(connection, **param), autocommit=True)
        return True


@deco.singleton
class DefaultDBPool(DBPool):
    '''
    默认db配置用的单例数据库连接池
    '''
    pass


defaultPool = DefaultDBPool()
# raise_not_exist必须为False
# 在类似异步任务场景下，不会初始化数据库连接池
# 因此raise_not_exist=True时，任何pool.POOLS.{name}的操作都会引发AttributeError异常
# 导致无法import api/resource相关类，但实际上这些类的定义是可以import但不使用的
POOLS = config.Config(None, raise_not_exist=False)
