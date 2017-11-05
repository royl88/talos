# coding=utf-8
${coding}
"""
${pkg_name}.server.wsgi_server
~~~~~~~~~~~~~~~~~~~~~~~~~~

本模块提供wsgi启动能力

"""

from __future__ import absolute_import

from talos.server import base


application = base.initialize_server('${pkg_name}', '${config_file}', conf_dir='${config_dir}')
