# coding=utf-8
"""
本模块提供日志初始化功能

"""

from __future__ import absolute_import

import logging
# from logging.handlers import RotatingFileHandler
# from logging.handlers import TimedRotatingFileHandler
from logging.handlers import WatchedFileHandler

from talos.core import config

CONF = config.CONF


def setup():
    """日志输出初始化"""
    levelmap = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    logging.getLogger().setLevel(levelmap.get(CONF.log.level.upper(), logging.INFO))
    # TimedRotatingFileHandler、RotatingFileHandler多进程写日志切换后导致日志混乱
    # 修改为使用WatchedFileHandler，日志轮转统一使用logrotate
    handler = WatchedFileHandler(CONF.log.path)
    # handler = TimedRotatingFileHandler(CONF.log.path, when='midnight', backupCount=CONF.log.backupcount)
    # handler = RotatingFileHandler(CONF.log.path, maxBytes=CONF.log.maxbytes, backupCount=CONF.log.backupcount)
    handler.setLevel(levelmap.get(CONF.log.level.upper(), logging.INFO))
    # eg. %(asctime)s.%(msecs)03d %(process)d %(levelname)s %(name)s:%(lineno)d [-] %(message)s
    # eg. %Y-%m-%d %H:%M:%S
    formatter = logging.Formatter(fmt=CONF.log.format_string, datefmt=CONF.log.date_format_string)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    if CONF.log.log_console:
        # stream handler
        handler = logging.StreamHandler()
        handler.setLevel(levelmap.get(CONF.log.level.upper(), logging.INFO))
        formatter = logging.Formatter(fmt=CONF.log.format_string, datefmt=CONF.log.date_format_string)
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
    logging.captureWarnings(True)
    loggers_configs = getattr(CONF.log, 'loggers', [])
    for log_config in loggers_configs:
        logger = logging.getLogger(log_config['name'])
        logger.setLevel(levelmap.get(log_config.get('level', CONF.log.level.upper()).upper(), logging.INFO))
        handler = WatchedFileHandler(log_config['path'])
        handler.setLevel(levelmap.get(log_config.get('level', CONF.log.level.upper()).upper(), logging.INFO))
        formatter = logging.Formatter(fmt=CONF.log.format_string, datefmt=CONF.log.date_format_string)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
