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


application = base.initialize_server('${pkg_name}',
                                     os.environ.get('${pkg_name.upper()}_CONF', '${config_file}'),
                                     conf_dir=os.environ.get('${pkg_name.upper()}_CONF_DIR', '${config_dir}'))
'''