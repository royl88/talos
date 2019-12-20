# coding=utf-8

from __future__ import absolute_import

import datetime
import json
import logging
import pytest
import decimal
import uuid
from xml.etree import ElementTree as et

from talos.core import utils
from talos.core import xmlutils

LOG = logging.getLogger(__name__)


def test_json():
    datetime_data1 = datetime.datetime(1, 1, 1)
    datetime_data2 = datetime.datetime(9999, 1, 1)
    date_data1 = datetime.date(1, 1, 1)
    date_data2 = datetime.date(9999, 1, 1)
    data = {'int': 1, 'float': 1.234567890123456789, 'list': [1, '2', 1.234567890123456789],
            'datetime1': datetime_data1, 'datetime2': datetime_data2,
            'date1': date_data1, 'date2': date_data2}
    with pytest.raises(TypeError):
        json.dumps(data)
    json.dumps(data, cls=utils.ComplexEncoder)


def test_get_hostname():
    assert len(utils.get_hostname()) > 0


def test_encrypt_password():
    assert utils.encrypt_password('1', '2') == '3c794f0c67bd561ce841fc6a5999bf0df298a0f0ae3487efda9d0ef4'
    assert utils.check_password('3c794f0c67bd561ce841fc6a5999bf0df298a0f0ae3487efda9d0ef4', '1', '2') is True
    assert utils.check_password('3c794f0c67bd561ce841fc6a5999bf0df298a0f0ae3487efda9d0ef4', '1', '3') is False
    assert len(utils.generate_salt(13)) == 13


def test_get_function_name():
    assert utils.get_function_name() == 'test_get_function_name'


def test_walk_dir():
    for n in utils.walk_dir('tests', '*.conf'):
        assert n.endswith('unittest.conf')


def test_uuid():
    u = utils.generate_uuid(dashed=True, version=1, lower=True)
    assert '-' in u
    assert u.islower() is True
    u = utils.generate_uuid(dashed=False, version=1, lower=False)
    assert '-' not in u
    assert u.islower() is False

    u = utils.generate_uuid(dashed=True, version=4, lower=True)
    assert '-' in u
    assert u.islower() is True
    u = utils.generate_uuid(dashed=False, version=4, lower=False)
    assert '-' not in u
    assert u.islower() is False
    assert utils.generate_uuid() != utils.generate_uuid()
    with pytest.raises(ValueError):
        utils.generate_prefix_uuid('talos-', length=5)
    assert len(utils.generate_prefix_uuid('talos-', length=11)) == 17
    assert utils.generate_prefix_uuid('talos-', length=8) != utils.generate_prefix_uuid('talos-', length=8)
    assert utils.generate_prefix_uuid('talos-', length=12) != utils.generate_prefix_uuid('talos-', length=12)


def test_bool_from_string():
    true_exprs = ('1', 't', 'true', 'on', 'y', 'yes',
                 'T', 'trUe', 'oN', 'Y', 'yeS',)
    false_exprs = ('0', 'f', 'false', 'off', 'n', 'no',
                   'F', 'fAlse', 'oFf', 'N', 'No')
    non_exprs = ('Ko', 'thx', 'you', '-1', '0.0')
    for e in true_exprs:
        assert utils.bool_from_string(e, strict=False, default=None) is True
    for e in false_exprs:
        assert utils.bool_from_string(e, strict=False, default=None) is False
    for e in non_exprs:
        assert utils.bool_from_string(e, strict=False, default=None) is None
    with pytest.raises(ValueError):
        utils.bool_from_string('s', strict=True)


def test_encoding():
    assert utils.ensure_unicode('你好') == u'你好'
    assert utils.ensure_bytes('你好') == u'你好'.encode('utf-8')

    assert utils.ensure_unicode(b'\x99', errors='replace') == u'\ufffd'
    assert utils.ensure_unicode(b'\x99', errors='ignore') == u''
    with pytest.raises(UnicodeDecodeError):
        utils.ensure_unicode(b'\x99', errors='strict')
    assert utils.ensure_bytes(u'\x99', errors='replace') == b'\xc2\x99'
    assert utils.ensure_bytes(u'\x99', errors='ignore') == b'\xc2\x99'
    assert utils.ensure_bytes(u'\x99', errors='strict') == b'\xc2\x99'


def test_get_item():
    data = {'a': {'b': {'c': 1, 'd': [{'e': 'got me'}]}}}
    assert utils.get_item(data, expr='a.b.c') == 1
    assert utils.get_item(data, expr='a.b.d.[0].e') == 'got me'
    assert utils.get_item(data, expr='a.b.d.[3].e', default=None) is None


def test_xmlutils():
    data = {'a': 1, 'b': 1.2340932, 'c': True, 'd': None, 'e': 'hello <world />', 'f': {
        'k': 'v', 'm': 'n'}, 'g': [1, '2', False, None, {'k': 'v', 'm': [1, 2, 3, [4, 5, 6]]}],
        'h': et.Element('root'), 'i': datetime.datetime.now(), 'j': datetime.date.today(),
        'k': decimal.Decimal(3.141592653589793238462643383),
        'l': uuid.uuid4()}
    ret = xmlutils.toxml(data, attr_type=True,
                hooks={'etree': {'render': lambda x: x.tag, 'hit': lambda x: isinstance(x, et.Element)}})
    LOG.info(ret)
    assert ret.startswith(u'<?xml'.encode('utf-8'))
    ret = xmlutils.toxml([1, 2, {3: [4, 5, [6, 7]]}])
    LOG.info(ret)
    assert ret.startswith(u'<?xml'.encode('utf-8'))
    ret = xmlutils.toxml('test')
    LOG.info(ret)
    assert ret.startswith(u'<?xml'.encode('utf-8'))

