# coding=utf-8
import logging
import tempfile
import os.path

from talos.common import exporter

LOG = logging.getLogger(__name__)

row_data = [
    {'id': '1', 'age': 3, 'state': 'enabled', 'score': 60, 'extend': {'register_time': '2019'}},
    {'id': '1', 'age': 26, 'state': 'disbaled', 'score': 66, 'extend': {'register_time': '1998'}},
    {'id': '\x0a', 'age': 26, 'state': '\x00', 'score': 66, 'extend': {'register_time': '1998'}},
    ]

row_mapping=[
    {'column': u'ID', 'index': 'id', 'default': ''},
    {'column': u'年龄', 'index': 'age', 'default': ''},
    {'column': u'状态', 'index': 'state', 'default': '',
     'renderer': lambda k: {'enabled': u'启用', 'disbaled': u'禁用', }.get(k, '')},
    {'column': u'分数', 'index': 'score', 'default': ''},
    {'column': u'注册时间', 'index': 'extend.register_time', 'default': ''},
    {'column': u'评价', 'index': 'score', 'default': '',
     'xrenderer': lambda r, v: u'优秀' if r['age'] < 18 and v >= 60 else u'一般'},
    ]


def test_export_file():
    filepath = tempfile.mkdtemp(prefix='__csv_exporter')
    filename = os.path.join(filepath, 'unittest.csv')
    assert exporter.export_csv(filename, row_data, row_mapping) is True
    LOG.info('export to file %s', filename)

        
def test_export_as_string():
    content = exporter.export_csv_as_string(row_data, row_mapping)
    assert len(content) > 10
    LOG.info('export as string %s', content.decode('utf-8'))
