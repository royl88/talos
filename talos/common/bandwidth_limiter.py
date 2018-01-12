# coding=utf-8
"""
本模块提供带宽限制功能

"""

from __future__ import absolute_import

import logging
import os


LOG = logging.getLogger(__name__)
MAX_CLASS_ID = 1000


class BandWidthLimiter(object):
    def __init__(self, queue_id, dev='eth0'):
        self._queue_id = queue_id
        self._dev = dev
        self._bandwidth_limits = {}  # port: {'class_id': x, 'bandwidth': x}
        self.reset()

    def reset(self):
        command = 'tc qdisc del dev %(dev)s root' % {'dev': self._dev}
        os.system(command)
        command = 'tc qdisc add dev %(dev)s root handle %(queue)d:0 htb' % {'queue': self._queue_id, 'dev': self._dev}
        ret = os.system(command)
        if ret > 0:
            LOG.error('traffic control disabled')

    def add(self, port, bandwidth):
        """
        add bandwidth limiter

        :param port: port number
        :param bandwidth: KBytes/sec
        """
        if port in self._bandwidth_limits:
            LOG.error('port in bandwidth limit, pls use change')
            return False
        result = True
        class_ids = set([val['class_id'] for val in self._bandwidth_limits.values()])
        if bandwidth > 0:
            for x in range(1, MAX_CLASS_ID):
                if x not in class_ids:
                    command = 'tc class add dev %(dev)s parent %(queue)d:0 classid %(queue)d:%(class_id)d htb rate %(bandwidth)dkbps ceil %(bandwidth)dkbps burst 15kb' % {
                        'queue': self._queue_id, 'dev': self._dev, 'class_id': x, 'bandwidth': bandwidth}
                    ret = os.system(command)
                    result = ret == 0 and result
                    if ret > 0:
                        LOG.warn('tc adding class failed...bandwidth limit might not work')
                    command = 'tc filter add dev %(dev)s protocol ip parent %(queue)d:0 prio 1 u32 match ip sport %(port)d 0xffff flowid %(queue)d:%(class_id)d' % {
                        'queue': self._queue_id, 'dev': self._dev, 'class_id': x, 'port': port}
                    ret = os.system(command)
                    result = ret == 0 and result
                    if ret > 0:
                        LOG.warn('tc adding filter on port failed...bandwidth limit might not work')
                    if result:
                        self._bandwidth_limits[port] = {'class_id': x, 'bandwidth': bandwidth}
                    break
        else:
            result = False
        return result

    def change(self, port, bandwidth):
        """
        change bandwidth limiter

        :param port: port number
        :param bandwidth: MBytes/sec
        """
        if port not in self._bandwidth_limits:
            LOG.error('port not in bandwidth limit, pls use add')
            return False
        result = True
        class_id = self._bandwidth_limits[port]['class_id']
        if bandwidth > 0:
            command = 'tc class change dev %(dev)s parent %(queue)d:0 classid %(queue)d:%(class_id)d htb rate %(bandwidth)dkbps ceil %(bandwidth)dkbps burst 15kb' % {
                'queue': self._queue_id, 'dev': self._dev, 'class_id': class_id, 'bandwidth': bandwidth}
            ret = os.system(command)
            result = ret == 0 and result
            if ret > 0:
                LOG.warn('tc changing class failed...bandwidth limit might work as old time')
            if result:
                self._bandwidth_limits[port]['bandwidth'] = bandwidth
        else:
            LOG.error('tc invalid bandwidth: %(bandwidth)d', bandwidth=bandwidth)
            result = False
        return result

    def remove(self, port):
        result = True
        if port in self._bandwidth_limits:
            class_id = self._bandwidth_limits[port]['class_id']
            bandwidth = self._bandwidth_limits[port]['bandwidth']
            command = 'tc filter del dev %(dev)s protocol ip parent %(queue)d:0 prio 1 u32 match ip sport %(port)d 0xffff flowid %(queue)d:%(class_id)d' % {
                'queue': self._queue_id, 'dev': self._dev, 'class_id': class_id, 'port': port}
            ret = os.system(command)
            result = ret == 0 and result
            if ret > 0:
                LOG.warn('tc removing filter on port failed...bandwidth limit still work')
            command = 'tc class del dev %(dev)s parent %(queue)d:0 classid %(queue)d:%(class_id)d htb rate %(bandwidth)dkbps ceil %(bandwidth)dkbps burst 15kb' % {
                'queue': self._queue_id, 'dev': self._dev, 'class_id': class_id, 'bandwidth': bandwidth}
            ret = os.system(command)
            result = ret == 0 and result
            if ret > 0:
                LOG.warn('tc removing class failed...bandwidth limit still work')
            if result:
                del self._bandwidth_limits[port]
        return result
