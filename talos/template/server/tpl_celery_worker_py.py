# coding=utf-8

TEMPLATE = u'''# coding=utf-8

from __future__ import absolute_import

import os
from talos.server import base


base.initialize_config(os.environ.get('${pkg_name.upper()}_CONF', '${config_file}'),
                       dir_path=os.environ.get('${pkg_name.upper()}_CONF_DIR', '${config_dir}'))
base.initialize_logger()
# import celery later, after initialize config
from talos.common import celery
app = celery.app
'''
