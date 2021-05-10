# coding=utf-8

TEMPLATE = u'''${sys_default_coding}
"""
${pkg_name}.server.wsgi_server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

本模块提供wsgi启动能力

"""

from __future__ import absolute_import

import os
from talos.server import base
from talos.middlewares import lazy_init
from talos.middlewares import json_translator
from talos.middlewares import limiter
from talos.middlewares import globalvars
# from talos.core import config


# @config.intercept('db_password', 'other_password')
# def get_password(value, origin_value):
#     """value为上一个拦截器处理后的值（若此函数为第一个拦截器，等价于origin_value）
#        origin_value为原始配置文件的值
#        没有拦截的变量talos将自动使用原始值，因此定义一个拦截器是很关键的
#        函数处理后要求必须返回一个值
#     """
#     # 演示使用不安全的base64，请使用你认为安全的算法进行处理
#     return base64.b64decode(origin_value)


application = base.initialize_server('${pkg_name}',
                                     os.environ.get('${pkg_name.upper()}_CONF', '${config_file}'),
                                     conf_dir=os.environ.get('${pkg_name.upper()}_CONF_DIR', '${config_dir}'),
                                     middlewares=[
                                         globalvars.GlobalVars(),
                                         json_translator.JSONTranslator(),
                                         lazy_init.LazyInit(limiter.Limiter)
                                     ],
                                     override_middlewares=True)
# https://falcon.readthedocs.io/en/latest/api/app.html?#falcon.RequestOptions
# keep empty query param, eg. ?a=&b=1 => {'a': '', 'b': '1'}
application.req_options.keep_blank_qs_values = True
# Flase: ?t=1,2,3&t=4 => ['1,2,3', '4']      True: t=1,2,3&t=4,5 => ['1', '2', '3', '4', '5']
application.req_options.auto_parse_qs_csv = True
'''
