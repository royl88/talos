# coding=utf-8
"""
包装了命令执行模块，支持超时设置，超时可强制kill进程及子进程
pip install psuitl
"""

from __future__ import absolute_import
import logging
import subprocess
import threading

import psutil

from talos.core.i18n import _

LOG = logging.getLogger(__name__)


def exec_command(command, timeout=None, raise_error=False, **kwargs):
    def timeout_callback(p, command):
        LOG.error(_('process(%(pid)s) execute timeout: %(command)s'), {'pid': p.pid, 'command': str(command)})
        try:
            _ps = psutil.Process(p.pid)
            for _p in _ps.children(recursive=True):
                try:
                    _p.kill()
                except psutil.NoSuchProcess:
                    pass
            try:
                _ps.kill()
            except psutil.NoSuchProcess:
                pass
        except psutil.Error as e:
            LOG.exception(e)

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
    if timeout:
        waiter = threading.Timer(timeout, timeout_callback, (process, command))
        waiter.start()
    output = process.communicate()[0]
    retcode = process.poll()
    if timeout:
        waiter.cancel()
    if retcode:
        LOG.error(_('Command %(command)s exited with %(retcode)s'
                    '- %(output)s'), {
                        'command': command,
                        'retcode': retcode,
                        'output': output
                    })
        if raise_error:
            e = subprocess.CalledProcessError(retcode, command)
            e.output = output
            raise e
        else:
            return False, retcode, output
    return True, retcode, output
