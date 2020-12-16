# coding=utf-8

import logging

from talos.db import crud
from talos.core import config

from tests import models

LOG = logging.getLogger(__name__)
CONF = config.CONF


class _Business(crud.ResourceBase):
    '''
    id    name    owner_dep_id    create_user_id
    1     bus1    1               1
    '''
    orm_meta = models.Business

    def __init__(self,
                 session=None,
                 transaction=None,
                 dbpool=None,
                 dynamic_relationship=None,
                 dynamic_load_method=None):
        super(_Business, self).__init__(session=session,
                                        transaction=transaction,
                                        dbpool=dbpool,
                                        dynamic_relationship=dynamic_relationship,
                                        dynamic_load_method=dynamic_load_method)
        self._unittest_checks = {}

    def create(self, resource, validate=True, detail=True):
        return super(_Business, self).create(resource, validate=validate, detail=detail)

    def update(self, rid, resource, filters=None, validate=True, detail=True):
        return super(_Business, self).update(rid, resource, filters=filters, validate=validate, detail=detail)

    def _before_create(self, resource, validate):
        self._unittest_checks['_before_create'] = {'resource': resource, 'validate': validate}

    def _addtional_create(self, session, resource, created):
        self._unittest_checks['_addtional_create'] = {'resource': resource, 'created': created}

    def _before_update(self, rid, resource, validate):
        self._unittest_checks['_before_update'] = {'rid': rid, 'resource': resource, 'validate': validate}

    def _addtional_update(self, session, rid, resource, before_updated, after_updated):
        self._unittest_checks['_addtional_update'] = {
            'rid': rid,
            'resource': resource,
            'before_updated': before_updated,
            'after_updated': after_updated
        }

    def _before_delete(self, rid):
        self._unittest_checks['_before_delete'] = {'rid': rid}

    def _addtional_delete(self, session, resource):
        self._unittest_checks['_addtional_delete'] = {'resource': resource}


def test_crud_inner_hooks():
    ref = _Business()
    try:
        with ref.transaction():
            ref.create({'id': '9999', 'name': 'test_crud_inner_hooks', 'owner_dep_id': 1, 'create_user_id': 1})
            ref.update('9999', {'name': 'test_crud_inner_hooks2'})
            ref.delete('9999')
            raise ValueError('force rollback')
    except Exception as e:
        LOG.exception(e)
    assert '_before_create' in ref._unittest_checks
    assert '_addtional_create' in ref._unittest_checks
    assert '_before_update' in ref._unittest_checks
    assert '_addtional_update' in ref._unittest_checks
    assert '_before_delete' in ref._unittest_checks
    assert '_addtional_delete' in ref._unittest_checks

    assert ref._unittest_checks['_before_create']['resource']['id'] == '9999'
    assert ref._unittest_checks['_before_create']['resource']['name'] == 'test_crud_inner_hooks'
    assert 'owner_dep' not in ref._unittest_checks['_addtional_create']['resource']
    assert 'create_user' not in ref._unittest_checks['_addtional_create']['resource']
    assert 'owner_dep' in ref._unittest_checks['_addtional_create']['created']
    assert 'create_user' in ref._unittest_checks['_addtional_create']['created']
    assert ref._unittest_checks['_addtional_create']['created']['owner_dep']
    assert ref._unittest_checks['_addtional_create']['created']['create_user']

    assert ref._unittest_checks['_before_update']['rid'] == '9999'
    assert ref._unittest_checks['_before_update']['resource']['name'] == 'test_crud_inner_hooks2'

    assert 'owner_dep' not in ref._unittest_checks['_addtional_update']['resource']
    assert 'create_user' not in ref._unittest_checks['_addtional_update']['resource']
    assert 'owner_dep' in ref._unittest_checks['_addtional_update']['before_updated']
    assert 'create_user' in ref._unittest_checks['_addtional_update']['before_updated']
    assert ref._unittest_checks['_addtional_update']['resource']['name'] == 'test_crud_inner_hooks2'
    assert ref._unittest_checks['_addtional_update']['before_updated']['name'] == 'test_crud_inner_hooks'
    assert 'owner_dep' in ref._unittest_checks['_addtional_update']['after_updated']
    assert 'create_user' in ref._unittest_checks['_addtional_update']['after_updated']
    assert ref._unittest_checks['_addtional_update']['after_updated']['name'] == 'test_crud_inner_hooks2'
    assert ref._unittest_checks['_addtional_update']['before_updated']['owner_dep']
    assert ref._unittest_checks['_addtional_update']['before_updated']['create_user']
    assert ref._unittest_checks['_addtional_update']['after_updated']['owner_dep']
    assert ref._unittest_checks['_addtional_update']['after_updated']['create_user']

    assert ref._unittest_checks['_before_delete']['rid'] == '9999'
    assert ref._unittest_checks['_addtional_delete']['resource']['name'] == 'test_crud_inner_hooks2'
    assert ref._unittest_checks['_addtional_delete']['resource']['owner_dep']
    assert ref._unittest_checks['_addtional_delete']['resource']['create_user']