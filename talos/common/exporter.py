# coding=utf-8
"""
本模块提供列表导出CSV/Excl功能

"""

from __future__ import absolute_import

import codecs
import csv
import os
import re
import shutil
import tempfile


class _NotExist(object):
    pass


VALUE_NOT_EXIST = _NotExist()


def _recursive_get(data, key, delimiter='.', default=None):
    def _recursive_get_list(data, key, delimiter=';', default=None):
        pattern_int = r'\[\s*(\d+)\s*\]'
        pattern_string = r'\[\s*([-_a-zA-Z0-9]+)\s*\]'
        matches = re.search(pattern_int, key)
        index = None
        value = default
        # 如果在key中找到索引访问
        if matches:
            index = int(matches.groups()[0])
            # 确认索引值在区间[0, len(data))，取值并赋值到value
            if len(data) > index:
                value = data[index]
        # 没有找到索引访问，尝试内部字典方式
        else:
            matches = re.search(pattern_string, key)
            if matches:
                inner_key = matches.groups()[0]
                inner_values = []
                for item in data:
                    inner_value = item.get(inner_key, VALUE_NOT_EXIST)
                    if inner_value != VALUE_NOT_EXIST and inner_value is not None:
                        inner_values.append(inner_value)
                if len(inner_values) > 0:
                    value = delimiter.join(inner_values)
        return value

    keys = key.split(delimiter)
    value = data
    for k in keys:
        # 如果key无效，直接返回default
        if len(k) == 0:
            value = VALUE_NOT_EXIST
            break
        else:
            # 当前value是list
            if isinstance(value, (list, tuple, set)):
                value = _recursive_get_list(value, k, default=VALUE_NOT_EXIST)
            # 当前value是dict，获取字典对应k的值，并赋值到value
            elif isinstance(value, dict):
                value = value.get(k, VALUE_NOT_EXIST)
                # 没有对应的key，直接返回default
                if value == VALUE_NOT_EXIST:
                    break
            # 否则直接返回default
            else:
                value = VALUE_NOT_EXIST
    if value == VALUE_NOT_EXIST:
        value = default
    return value


def export_csv(filename, rows, mapping):
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
    with codecs.open(filename, "w", encoding="gbk") as f:
        csvwriter = csv.writer(f)
        headers = []
        for x in mapping:
            headers.append(x['column'])
        csvwriter.writerow(headers)
        for row in rows:
            gbk_row = []
            for x in mapping:
                if isinstance(x['index'], int) and isinstance(row, (list, tuple, set)):
                    value = row[x['index']]
                else:
                    value = _recursive_get(
                        row, x['index'], default=x.get('default', ''))
                if 'renderer' in x:
                    render = x['renderer']
                    value = render(value)
                gbk_row.append(value)
            csvwriter.writerow(gbk_row)
        return True
    return False


def export_csv_as_string(rows, mapping):
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
    filename = os.path.join(filepath, 'test.csv')
    try:
        export_csv(filename, rows, mapping)
        with open(filename, 'rb') as f:
            return f.read()
    finally:
        shutil.rmtree(filepath, ignore_errors=True)
