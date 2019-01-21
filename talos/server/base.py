# coding=utf-8
"""
本模块提供服务相关初始化

"""

from __future__ import absolute_import

import logging
import sys

import falcon
import six

from talos.core import config
from talos.core import exceptions
from talos.core import i18n
from talos.core import logging as mylogger


LOG = logging.getLogger(__name__)

if six.PY2:
    reload(sys)
    sys.setdefaultencoding('UTF-8')


def error_http_exception(ex, req, resp, params):
    """捕获并转换内部Exception为falcon Exception"""
    LOG.exception(ex)
    http_status = 'HTTP_' + str(getattr(ex, 'code', 500))
    if hasattr(falcon, http_status):
        http_status = getattr(falcon, http_status)
    else:
        http_status = falcon.HTTP_500
    raise falcon.HTTPError(http_status,
                           title=getattr(ex, 'title', http_status.split(' ')[1]),
                           description=getattr(ex, 'message', str(ex)),
                           code=http_status.split(' ')[0])


def error_serializer(req, resp, exception):
    """
    将Exception信息转换为用户偏向返回格式

    eg. 用户提交的请求包含Accept: application/json，则返回json格式，

    可选xml, json，默认为application/json
    """
    representation = None

    preferred = req.client_prefers(('application/xml',
                                    'application/json',))

    if preferred:
        if preferred == 'application/json':
            representation = exception.to_json()
        else:
            representation = exception.to_xml()
        resp.body = representation
        resp.content_type = preferred


def initialize_config(path, dir_path=None):
    """初始化配置"""
    config.setup(path, dir_path=dir_path)


def initialize_logger():
    """初始化日志配置"""
    mylogger.setup()


def initialize_i18n(appname):
    """初始化国际化配置"""
    i18n._.setup(appname, config.CONF.locale_path, config.CONF.language)


def initialize_db():
    """初始化DB连接池"""
    from talos.db import pool
    CONF = config.CONF
    try:
        if CONF.db.connection:
            pool.POOL.reflesh(param=CONF.db.to_dict())
    except AttributeError:
        LOG.warning("config db.connection not set, skip")


def initialize_applications(api):
    """初始化wsgi application"""
    for name in config.CONF.application.names:
        if name:
            __import__(name)
            app = sys.modules[name]
            app.route.add_routes(api)


def initialize_middlewares(middlewares=None, override_defalut=False):
    """初始化中间件"""
    from talos.middlewares import json_translator
    from talos.middlewares import limiter
    from talos.middlewares import globalvars
    override_defalut = override_defalut or config.CONF.override_defalut_middlewares
    if override_defalut:
        mids = []
    else:
        mids = [
            globalvars.GlobalVars(),
            limiter.Limiter(),
            json_translator.JSONTranslator(),
        ]
    middlewares = middlewares or []
    mids.extend(middlewares)
    return mids


def initialize_server(appname, conf, conf_dir=None, middlewares=None, override_middlewares=False):
    """
    初始化整个service

    初始化顺序为
    * 配置文件
    * 日志
    * 国际化
    * DB连接池
    * 中间件
    * wsgi server
    """
    initialize_config(conf, dir_path=conf_dir)
    initialize_logger()
    initialize_i18n(appname)
    initialize_db()
    api = falcon.API(middleware=initialize_middlewares(middlewares, override_defalut=override_middlewares))
    initialize_applications(api)
    api.add_error_handler(exceptions.Error, error_http_exception)
    api.set_error_serializer(error_serializer)
    return api
