# coding=utf-8
"""
本模块提供服务相关初始化

"""

from __future__ import absolute_import

from collections import OrderedDict
import json
import logging
import sys

import falcon
import six
from talos.core import config
from talos.core import exceptions
from talos.core import i18n
from talos.core import logging as mylogger
from talos.core import utils
from talos.core import xmlutils
from talos.middlewares import lazy_init

LOG = logging.getLogger(__name__)

if six.PY2:
    reload(sys)
    sys.setdefaultencoding('UTF-8')


class EnhancedHTTPError(falcon.HTTPError):

    def __init__(self, status, title=None, description=None, headers=None,
                 href=None, href_text=None, code=None, extra_data=None):
        super(EnhancedHTTPError, self).__init__(status, title, description, headers, href, href_text, code)
        self._extra_data = extra_data or {}

    def to_dict(self, obj_type=dict):
        obj = obj_type()
        obj['title'] = self.title
        if self.description is not None:
            obj['description'] = self.description
        if self.code is not None:
            obj['code'] = self.code
        if self._extra_data:
            obj.update(self._extra_data)
        return obj

    def to_json(self):
        data = self.to_dict(OrderedDict)
        return json.dumps(data, cls=utils.ComplexEncoder)

    def to_xml(self):
        data = self.to_dict(OrderedDict)
        return xmlutils.toxml(data, root_tag='error')


def error_http_exception(ex, req, resp, params):
    """捕获并转换内部Exception为falcon Exception"""
    code = None
    title = None
    description = None
    exception_data = None
    if isinstance(ex, falcon.http_status.HTTPStatus):
        # falcon中redirect作为异常抛出，但不需要额外处理
        raise ex
    LOG.exception(ex)
    if isinstance(ex, falcon.errors.HTTPError):
        # 只捕获HTTPError
        code = int(ex.status.split(' ', 1)[0])
        title = ex.status.split(' ', 1)[1]
        description = title if ex.description is None else ex.description
    elif isinstance(ex, exceptions.Error):
        # 抛出框架异常，通常是用户有意为之
        code = ex.code
        title = ex.title
        description = ex.message
        exception_data = ex.exception_data
    else:
        code = 500
        title = 'Internal Server Error'
        description = str(ex)
    http_status = 'HTTP_' + str(code)
    if hasattr(falcon, http_status):
        http_status = getattr(falcon, http_status)
    else:
        http_status = falcon.HTTP_500
    raise EnhancedHTTPError(http_status,
                            title=title,
                            description=description,
                            code=code,
                            extra_data=exception_data)


def error_serializer(req, resp, exception):
    """
    将Exception信息转换为用户偏向返回格式

    eg. 用户提交的请求包含Accept: application/json，则返回json格式，

    可选xml, json，默认为application/json
    """
    representation = None

    preferred = req.client_prefers(('application/xml',
                                    'application/json',))

    if preferred is None:
        preferred = 'application/json'
    else:
        resp.append_header('Vary', 'Accept')
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
            pool.defaultPool.reflesh(param=CONF.db.to_dict())
    except AttributeError:
        LOG.warning("config db.connection not set, skip")
    # 初始化附加DB连接
    try:
        if CONF.dbs:
            db_confs = CONF.dbs.to_dict()
            conns = {}
            for name, param in db_confs.items():
                conns[name] = pool.DBPool(param=param)
            pool.POOLS.set_options(conns)
    except AttributeError:
        LOG.warning("config dbs not set, skip")


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
            json_translator.JSONTranslator(),
            lazy_init.LazyInit(limiter.Limiter),
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
    api.add_error_handler(Exception, error_http_exception)
    api.set_error_serializer(error_serializer)
    return api
