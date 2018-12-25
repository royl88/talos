# coding=utf-8

TEMPLATE = u'''${sys_default_coding}

from __future__ import absolute_import

import os
from talos.server import base


base.initialize_config(os.environ.get('${pkg_name.upper()}_CONF', '${config_file}'),
                       dir_path=os.environ.get('${pkg_name.upper()}_CONF_DIR', '${config_dir}'))
base.initialize_logger()
base.initialize_i18n('${pkg_name}')
# not allowed database connections by default, if you want to use db features, pls remove '#'
# base.initialize_db()
# import celery later, after initialize config
from talos.common import celery
app = celery.app


'''
