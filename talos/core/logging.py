# coding=utf-8
"""
本模块提供日志初始化功能

"""

from __future__ import absolute_import

import logging
import sys
from logging.handlers import WatchedFileHandler

from talos.core import config
from talos.core import utils

CONF = config.CONF


def _handler_finder(name):
    modpath, handler = name.strip().split(':')
    __import__(modpath)
    mod = sys.modules[modpath]
    return getattr(mod, handler, None)


def _make_handler(obj):
    handler_path = obj.get('handler', None)
    if handler_path:
        handler_cls = _handler_finder(handler_path)
        handler_args = obj.get('handler_args', [])
        if handler_cls is None:
            raise ValueError('logging Handler not found: %s' % handler_path)
        try:
            return handler_cls(*handler_args)
        except Exception as e:
            raise RuntimeError('logging Handler: %s initlize error: %s' % (handler_cls.__name__, e))
    return WatchedFileHandler(obj['path'])


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
    handler = _make_handler(CONF.log)
    # eg. %(asctime)s.%(msecs)03d %(process)d %(levelname)s %(name)s:%(lineno)d [-] %(message)s
    # eg. %Y-%m-%d %H:%M:%S
    formatter = logging.Formatter(fmt=CONF.log.format_string, datefmt=CONF.log.date_format_string)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    if CONF.log.log_console:
        # stream handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(fmt=CONF.log.format_string, datefmt=CONF.log.date_format_string)
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
    logging.captureWarnings(True)
    loggers_configs = getattr(CONF.log, 'loggers', [])
    for log_config in loggers_configs:
        logger = logging.getLogger(log_config['name'])
        logger.propagate = log_config.get('propagate', True)
        logger.setLevel(levelmap.get(log_config.get('level', CONF.log.level.upper()).upper(), logging.INFO))
        handler = _make_handler(log_config)
        formatter = logging.Formatter(fmt=log_config.get('format_string', CONF.log.format_string),
                                      datefmt=log_config.get('date_format_string', CONF.log.date_format_string))
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        sub_log_console = log_config.get('log_console', CONF.log.log_console)
        # 防止控制台重复日志
        if CONF.log.log_console and logger.propagate:
            sub_log_console = False
        if sub_log_console:
            # stream handler
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
