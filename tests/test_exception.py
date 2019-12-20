# coding=utf-8

from __future__ import absolute_import

import pytest
import six

from talos.core import exceptions


def test_exception():
    with pytest.raises(exceptions.Error):
        e = exceptions.Error(exception_data={'test': 'hello'})
        assert isinstance(e.to_dict(), dict)
        assert 'test' in e.to_dict()
        assert isinstance(e.to_json(), six.string_types)
        assert e.to_xml().startswith(u'<?xml'.encode('utf-8'))
        raise e


def test_callback_exception():
    with pytest.raises(exceptions.Error):
        raise exceptions.CallBackError({})


def test_validate_exception():
    with pytest.raises(exceptions.Error):
        raise exceptions.ValidationError(attribute='id', msg='ok')
