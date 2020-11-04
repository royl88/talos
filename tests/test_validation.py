# coding=utf-8

from __future__ import absolute_import

import logging
import pytest

from talos.db import crud
from talos.db import converter
from talos.core import exceptions
from talos.db import validator

LOG = logging.getLogger(__name__)


def test_validator():
    assert validator.NullValidator().validate(None) is True
    assert validator.CallbackValidator(lambda x: False).validate(None) is not True
    assert validator.RegexValidator('1.a').validate('1+a') is True
    assert validator.RegexValidator('1.a').validate('2+a') is not True
    assert validator.EmailValidator().validate('talos@talos.com') is True
    assert validator.EmailValidator().validate('talos.com') is not True
    assert validator.PhoneValidator().validate('13800138000') is True
    assert validator.PhoneValidator().validate('13800') is not True
    assert validator.UrlValidator().validate('http://www.google.com') is True
    assert validator.UrlValidator().validate('www.google.com') is not True
    assert validator.Ipv4CidrValidator().validate('192.168.0.0') is True
    assert validator.Ipv4CidrValidator().validate('192.168.1.0/24') is True
    assert validator.Ipv4CidrValidator().validate(None) is not True
    assert validator.Ipv4Validator().validate('192.168.1.1') is True
    assert validator.Ipv4Validator().validate('192.168.1.0/24') is not True
    assert validator.Ipv4Validator().validate(None) is not True
    assert validator.LengthValidator(5, 15).validate('1234567') is True
    assert validator.LengthValidator(5, 15).validate('123') is not True
    assert validator.TypeValidator(int).validate(1) is True
    assert validator.TypeValidator(int).validate('1') is not True
    assert validator.NumberValidator(float).validate(1.0) is True
    assert validator.NumberValidator(float).validate(1) is not True
    assert validator.NumberValidator().validate(1) is True
    assert validator.NumberValidator(range_min=1, range_max=10).validate(3) is True
    assert validator.NumberValidator(range_min=1, range_max=10).validate(30) is not True
    assert validator.NumberValidator(int, range_min=1, range_max=10).validate(3) is True
    assert validator.NumberValidator(int, range_min=1, range_max=10).validate(30) is not True
    assert validator.InValidator([1, 2, 3]).validate(2) is True
    assert validator.InValidator([1, 2, 3]).validate(4) is not True
    assert validator.NotInValidator([1, 2, 3]).validate(2) is not True
    assert validator.NotInValidator([1, 2, 3]).validate(4) is True
    assert validator.ChainValidator(
        (validator.EmailValidator(), validator.LengthValidator(5, 7), validator.InValidator(
            ('1@1.com', )))).validate('1@1.com') is True
    assert validator.ChainValidator(
        (validator.EmailValidator(), validator.LengthValidator(5, 7), validator.InValidator(
            ('11.com', )))).validate('11.com') is not True
    assert validator.ChainValidator(
        (validator.EmailValidator(), validator.LengthValidator(5, 7), validator.InValidator(
            ('12345@1.com', )))).validate('12345@1.com') is not True
    assert validator.ChainValidator(
        (validator.EmailValidator(), validator.LengthValidator(5, 7), validator.InValidator(
            ('2@1.com', )))).validate('1@1.com') is not True


def test_converter():
    converter.DateTimeConverter().convert('2019-01-01 00:01:02')
    converter.DateConverter().convert('2019-01-01')
    assert converter.BooleanConverter().convert('ko') is False
    assert converter.BooleanConverter().convert('t') is True
    assert converter.BooleanConverter().convert('f') is False


def test_col_validator():
    validators = [
        crud.ColumnValidator(field='name', rule_type='length', rule='1,36', validate_on=['create:M', 'update:O']),
        crud.ColumnValidator(field='description',
                             rule_type='length',
                             rule='0,63',
                             validate_on=('create:O', 'update:O'),
                             nullable=True),
        crud.ColumnValidator(field='enabled', rule_type='in', rule=[0, 1], validate_on=('create:M', 'update:O')),
        crud.ColumnValidator(field='children',
                             rule=validator.TypeValidator(list),
                             validate_on=('create:O', 'update:O'),
                             orm_required=False)
    ]
    for_orm_required = {'name': 'test01', 'enabled': 1, 'children': [{'children_id': 1}]}
    orm_data = crud.ColumnValidator.any_orm_data(validators, for_orm_required, 'create')
    assert 'name' in orm_data
    assert 'description' not in orm_data
    assert 'enabled' in orm_data
    assert 'children' not in orm_data
    orm_data = crud.ColumnValidator.get_clean_data(validators, for_orm_required, 'create', orm_required=False)
    assert 'name' in orm_data
    assert 'description' not in orm_data
    assert 'enabled' in orm_data
    assert 'children' in orm_data
    orm_data = crud.ColumnValidator.get_clean_data(validators, for_orm_required, 'create', orm_required=True)
    assert 'name' in orm_data
    assert 'description' not in orm_data
    assert 'enabled' in orm_data
    assert 'children' not in orm_data

    for_required = {}
    with pytest.raises(exceptions.FieldRequired):
        orm_data = crud.ColumnValidator.any_orm_data(validators, for_required, 'create')
    with pytest.raises(exceptions.FieldRequired):
        orm_data = crud.ColumnValidator.get_clean_data(validators, for_required, 'create')
    assert len(crud.ColumnValidator.any_orm_data(validators, for_required, 'update')) == 0
    assert len(crud.ColumnValidator.get_clean_data(validators, for_required, 'update')) == 0

    for_validation = {'name': '', 'description': None, 'enabled': 2, 'children': None}
    # raise for name validation
    with pytest.raises(exceptions.ValidationError):
        crud.ColumnValidator.get_clean_data(validators, for_validation, 'create')
    for_validation['name'] = 'test01'
    # raise for enabled validation
    with pytest.raises(exceptions.ValidationError):
        crud.ColumnValidator.get_clean_data(validators, for_validation, 'create')
    for_validation['enabled'] = 1
    # we must check children in orm_required=True/False
    # raise for children nullable validation
    with pytest.raises(exceptions.ValidationError):
        crud.ColumnValidator.get_clean_data(validators, for_validation, 'create')
    with pytest.raises(exceptions.ValidationError):
        crud.ColumnValidator.get_clean_data(validators, for_validation, 'create', orm_required=True)
    for_validation['children'] = []
    # ok
    assert len(crud.ColumnValidator.get_clean_data(validators, for_validation, 'create')) == 4
