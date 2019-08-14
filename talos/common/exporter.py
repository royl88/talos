# coding=utf-8
"""
本模块提供列表导出CSV/Excl功能

"""

from __future__ import absolute_import

import codecs
import csv
import os
import shutil
import tempfile

from talos.core import utils

_recursive_get = utils.get_item


def export_csv(filename, rows, mapping, encoding='utf-8'):
    """
    导出CSV文件

    :param filename: 导出的CSV文件名
    :type filename: str
    :param rows: 数据列表
    :type rows: list
    :param mapping: 列索引定义
            eg.
            [
            {'column': '状态',
            'index': 'state',
            'default': '',
            'renderer': lambda k: {'0': '运行中', '1': '关闭', }.get(k, '')},
            {'column': '管理员email',
            'index': 't_managers.[email]',
            'default': ''}
            {'column': '宿主机',
            'index': 't_host.name',
            'default': ''},
            ]
    :type mapping: list
    """
    with codecs.open(filename, "w", encoding=encoding, errors='replace') as f:
        csvwriter = csv.writer(f)
        headers = []
        for x in mapping:
            headers.append(x['column'])
        csvwriter.writerow(headers)
        for row in rows:
            row_data = []
            for x in mapping:
                if isinstance(x['index'], int) and isinstance(row, (list, tuple, set)):
                    value = row[x['index']]
                else:
                    value = _recursive_get(
                        row, x['index'], default=x.get('default', ''))
                if 'renderer' in x:
                    render = x['renderer']
                    value = render(value)
                elif 'xrenderer' in x:
                    render = x['xrenderer']
                    value = render(row, value)
                row_data.append(value)
            csvwriter.writerow(row_data)
        return True
    return False


def export_csv_as_string(rows, mapping, encoding='utf-8'):
    """
    导出CSV，并返回CSV文件内容字符串

    :param filename: 导出的CSV文件名
    :type filename: str
    :param rows: 数据列表
    :type rows: list
    :param mapping: 列索引定义
            eg.
            {'column': '状态',
            'index': 'state',
            'default': '',
            'renderer': lambda k: {'0': '运行中', '1': '关闭', }.get(k, '')},
            {'column': '管理员email',
            'index': 't_managers.[email]',
            'default': ''}
            {'column': '宿主机',
            'index': 't_host.name',
            'default': ''},
    :type mapping: dict
    :returns: csv字节流
    :rtype: str
    """
    filepath = tempfile.mkdtemp(prefix='__csv_exporter')
    filename = os.path.join(filepath, 'export.csv')
    try:
        export_csv(filename, rows, mapping, encoding=encoding)
        with open(filename, 'rb') as f:
            return f.read()
    finally:
        shutil.rmtree(filepath, ignore_errors=True)
