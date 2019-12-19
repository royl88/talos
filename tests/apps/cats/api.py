# coding=utf-8

import logging

from talos.db import crud
from talos.db import validator
from talos.core import config

from tests import models


CONF = config.CONF
LOG = logging.getLogger(__name__)


class Department(crud.ResourceBase):
    orm_meta = models.Department


class DepValidator(validator.NullValidator):
    def validate(self, value):
        if Department().count({'id': value}) == 1:
            return True
        else:
            return 'department of %s not found' % value


class User(crud.ResourceBase):
    orm_meta = models.User

    _validate = [
        crud.ColumnValidator(field='id', rule_type='length', rule='1,36', validate_on=['create:M']),
        crud.ColumnValidator(field='name', rule_type='length', rule='1,63', validate_on=['create:M', 'update:O']),
        crud.ColumnValidator(field='department_id', rule=DepValidator(), validate_on=['create:M', 'update:O']),
        crud.ColumnValidator(field='age', rule=validator.NumberValidator(
            range_min=1, range_max=200), validate_on=['create:O', 'update:O'], nullable=True),
    ]

    def _addtional_list(self, query, filters):
        LOG.info(str(query))
        return crud.ResourceBase._addtional_list(self, query, filters)
