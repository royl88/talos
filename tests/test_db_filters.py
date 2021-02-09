# coding=utf-8

import pytest
import logging
import random

from talos.db import crud
from talos.core import config
from talos.core import exceptions

from tests import models

LOG = logging.getLogger(__name__)
CONF = config.CONF


class _Base(crud.ResourceBase):
    _dynamic_load_method = 'joinedload'

    def _unsupported_filter(self, query, idx, name, op, value):
        LOG.error('#############################unsupported filter#####################################')
        LOG.error('index:%(idx)s name:%(name)s op:%(op)s value:%(value)s - %(sql)s' % {
            'sql': query,
            'idx': idx,
            'name': name,
            'op': op,
            'value': value
        })
        return crud.ResourceBase._unsupported_filter(self, query, idx, name, op, value)

    def _get_query(self, session, orm_meta=None, filters=None, orders=None, joins=None, ignore_default=False, **kwargs):
        query = crud.ResourceBase._get_query(self,
                                             session,
                                             orm_meta=orm_meta,
                                             filters=filters,
                                             orders=orders,
                                             joins=joins,
                                             ignore_default=ignore_default,
                                             **kwargs)
        LOG.error('#############################get query#####################################')
        LOG.error('%s' % query)
        return query


class _Department(_Base):
    '''
    id    name
    1     技术部
    2     业务部
    '''

    orm_meta = models.Department


class _User(_Base):
    '''
    id    name    department_id    age
    1     Deke    1                23
    2     Jacob   1                16
    3     Rachel  2                
    4     Paco    2                3
    '''
    orm_meta = models.User


class _UserWithFilter(_Base):
    orm_meta = models.User
    _default_filter = {'age': {'lte': 3, 'gte': 1}}


class _Address(_Base):
    '''
    id    location    user_id
    1     深圳        1
    2     广州        1
    3     随机        3
    '''

    orm_meta = models.Address


class _Business(_Base):
    '''
    id    name    owner_dep_id    create_user_id
    1     bus1    1               1
    '''

    orm_meta = models.Business

    def get_list_query(self, filters=None, orders=None, offset=None, limit=None, hooks=None):
        offset = offset or 0
        with self.get_session() as session:
            query = self._get_query(session, filters=filters, orders=orders)
            if hooks:
                for h in hooks:
                    query = h(query, filters)

            query = self._addtional_list(query, filters)
            if offset:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            return query

    def get_detail_query(self, rid):
        with self.get_session() as session:
            query = self._get_query(session, level_of_relationship=3)
            query = self._apply_primary_key_filter(query, rid)
            return query


class _BusinessDetailSum(_Business):
    '''
    id    name    owner_dep_id    create_user_id
    1     bus1    1               1
    '''

    orm_meta = models.Business
    _detail_relationship_as_summary = True


class _BusinessDisableDnyamicRel(_Business):
    '''
    id    name    owner_dep_id    create_user_id
    1     bus1    1               1
    '''

    orm_meta = models.Business
    _dynamic_relationship = False


def test_orders():
    users = _User().list(orders=['-age', '+id', 'name'])
    LOG.info(users)
    assert len(users) > 0


def test_list_one():
    # WHERE user.id = ?
    users = _User().list(filters={'id': '1'})
    assert len(users) == 1
    for u in users:
        assert u['id'] == '1'


def test_list_two():
    # WHERE user.age = ? AND user.id = ? AND user.name = ?
    users = _User().list(filters={'id': '2', 'name': 'Jacob', 'age': 16})
    assert len(users) == 1
    for u in users:
        assert u['id'] == '2'


def test_list_or_1():
    # WHERE user.id = ? OR user.id = ?
    users = _User().list(filters={'$or': [{'id': '1'}, {'id': '3'}]})
    assert len(users) == 2
    for u in users:
        assert u['id'] in ('1', '3')


def test_list_or_2():
    # WHERE user.id = ? OR user.id = ?
    users = _User().list(filters={'$or': [{'id': '1'}]})
    assert len(users) == 1
    for u in users:
        assert u['id'] in ('1', )


def test_list_or_3():
    users = _User().list(filters={'$or': [{'notexistscol': '1'}]})
    if CONF.dbcrud.unsupported_filter_as_empty:
        assert len(users) == 0
    else:
        assert len(users) > 1


def test_list_or_4():
    users = _User().list(filters={'$or': [{'age': {'like': 3}}]})
    if CONF.dbcrud.unsupported_filter_as_empty:
        assert len(users) == 0
    else:
        assert len(users) > 1


def test_list_and_1():
    # WHERE department.id = user.department_id AND department.id = ?)) AND user.age IS NULL
    users = _User().list(filters={'$and': [{'id': '3'}, {'name': 'Rachel'}, {'department.id': '2'}, {'age': None}]})
    assert len(users) == 1
    for u in users:
        assert u['id'] == '3'


def test_list_and_2():
    # WHERE user.age IS NULL AND (EXISTS (SELECT 1
    # FROM department
    # WHERE department.id = user.department_id AND department.id = ?)) AND user.id = ? AND user.name = ?
    users = _User().list(filters={'id': '3', 'name': 'Rachel', 'department.id': '2', 'age': None})
    assert len(users) == 1
    for u in users:
        assert u['id'] == '3'


def test_list_complicate_1():
    # WHERE user.id = ? AND user.name = ? OR user.id = ? AND user.name = ? OR user.id = ?
    users = _User().list(filters={
        '$or': [{
            '$and': [{
                'id': '1'
            }, {
                'name': 'Deke'
            }]
        }, {
            '$and': [{
                'id': '2'
            }, {
                'name': 'Jacob'
            }]
        }, {
            'id': '3'
        }],
    })
    assert len(users) == 3
    for u in users:
        assert u['id'] in ('1', '2', '3')


def test_list_complicate_2():
    # WHERE user.id = ? AND user.name = ? AND (EXISTS (SELECT 1
    # FROM department
    # WHERE department.id = user.department_id AND department.id = ?)) AND user.age < ? AND user.age > ?
    users = _User().list(
        filters={'$and': [{
            'id': '2'
        }, {
            'name': 'Jacob'
        }, {
            'department.id': '1'
        }, {
            'age': {
                'gt': 15,
                'lt': 17
            }
        }]})
    assert len(users) == 1
    assert users[0]['id'] == '2'


def test_list_complicate_3():
    # WHERE (EXISTS (SELECT 1
    # FROM department
    # WHERE department.id = user.department_id AND department.id = ?)) AND
    # (user.age < ? AND user.age > ? OR user.age IS NULL)
    users = _User().list(
        filters={'$and': [{
            'department.id': '2'
        }, {
            '$or': [{
                'age': {
                    'gt': 2,
                    'lt': 4
                }
            }, {
                'age': None
            }]
        }]})
    assert len(users) == 2
    for u in users:
        assert u['id'] in (
            '3',
            '4',
        )


def test_update():
    location_after = 'auto_update_%d' % random.randint(1, 1000)
    addr_before, addr_after = _Address().update('3', {'location': location_after})
    assert addr_after['location'] == location_after


def test_update_rollback():
    with pytest.raises(ValueError):
        with _User().transaction() as session:
            age_after = 'auto_update_%d' % random.randint(1, 1000)
            age_before, age_after = _User(transaction=session).update('3', {'age': age_after})
            raise ValueError('sqlite column int accept string, raise an exception make sure it will rollback')
    assert age_before['age'] == _User().get('3')['age']


def test_get_1():
    addr = _Address().get('3')
    assert addr['id'] == '3'


def test_get_2():
    addr = _Address().get(('3', ))
    assert addr['id'] == '3'


def test_get_3():
    addr = _Address().get(('3kalsdjflsdkjfll2kfj23231ll12'))
    assert addr is None


def test_get_error():
    with pytest.raises(exceptions.CriticalError):
        addr = _Address().get(('3', 'something'))


def test_create():
    with _Address().transaction() as session:
        addr = _Address(transaction=session).create(resource={
            'id': 'auto_test_gen',
            'location': 'auto_test_gen',
            'user_id': '3'
        })
        assert addr['id'] == 'auto_test_gen'
        count, addrs = _Address(transaction=session).delete('auto_test_gen')
        assert count == 1
        assert addrs[0]['id'] == 'auto_test_gen'


def test_count():
    count = _User().count({'id': '3'})
    assert count == 1


def test_default_filter():
    # WHERE user.age > ? AND user.age = ? AND user.age >= ? AND user.age <= ?
    users = _UserWithFilter().list({'age': {'eq': 3, 'gt': 1}})
    assert len(users) == 1
    assert users[0]['id'] == '4'


def test_unsupported_column():
    users = _UserWithFilter().list({'kagenomore': {'eq': 3, 'gt': 1}})
    if CONF.dbcrud.unsupported_filter_as_empty:
        assert len(users) == 0
    else:
        assert len(users) == 1
        assert users[0]['id'] == '4'


def test_unsupported_filter():
    users = _UserWithFilter().list({'age': {'ilike': '3'}})
    if CONF.dbcrud.unsupported_filter_as_empty:
        assert len(users) == 0
    else:
        assert len(users) == 1
        assert users[0]['id'] == '4'


def test_dynamic_relationship():
    bs_query = _Business().get_list_query()
    assert 'address' not in str(bs_query)
    bs_query = _Business().get_detail_query('1')
    assert 'address' in str(bs_query)

    bs_query = _BusinessDetailSum().get_list_query()
    assert 'address' not in str(bs_query)
    bs_query = _BusinessDetailSum().get_detail_query('1')
    assert 'address' not in str(bs_query)

    bs_query = _BusinessDisableDnyamicRel().get_list_query()
    assert 'address' in str(bs_query)


def test_multi_level_relationship_error():
    origin = CONF.dbcrud.unsupported_filter_as_empty
    CONF.dbcrud.to_dict()['unsupported_filter_as_empty'] = True
    assert len(_Business().list({'create_user.department.name': {'技术部'}})) == 0
    CONF.dbcrud.to_dict()['unsupported_filter_as_empty'] = False
    assert len(_Business().list({'create_user.department.name': {'技术部'}})) == 1
    CONF.dbcrud.to_dict()['unsupported_filter_as_empty'] = origin


def test_multi_level_relationship():
    assert len(_Business().list({'create_user': {'addresses': {'location': '广州'}}})) == 1
    assert _Business().count({'create_user': {'addresses': {'location': '广州'}}}) == 1
    assert len(_Business().list({'create_user': {'addresses': {'location': '北京666'}}})) == 0
    assert _Business().count({'create_user': {'addresses': {'location': '北京666'}}}) == 0
    assert len(_Business().list({'create_user': {'department': {'name': '技术部'}}})) == 1
    assert _Business().count({'create_user': {'department': {'name': '技术部'}}}) == 1
    assert len(_Business().list({'create_user': {'department': {'name': '业务部'}}})) == 0
    assert _Business().count({'create_user': {'department': {'name': '业务部'}}}) == 0
    assert len(_Business().list({'create_user': {'department': {'name': '技术部'}, 'addresses': {'location': '广州'}}})) == 1
    assert _Business().count({'create_user': {'department': {'name': '技术部'}, 'addresses': {'location': '广州'}}}) == 1
    assert len(_Business().list({'create_user': {
        'department': {
            'name': '技术部'
        },
        'addresses': {
            'location': '北京666'
        }
    }})) == 0
    assert _Business().count({'create_user': {'department': {'name': '技术部'}, 'addresses': {'location': '北京666'}}}) == 0

    assert len(_Business().list(
        {'create_user': {
            '$and': [{
                'department': {
                    'name': '技术部'
                }
            }, {
                'addresses': {
                    'location': '广州'
                }
            }]
        }})) == 1
    assert _Business().count(
        {'create_user': {
            '$and': [{
                'department': {
                    'name': '技术部'
                }
            }, {
                'addresses': {
                    'location': '广州'
                }
            }]
        }}) == 1
    assert len(_Business().list(
        {'create_user': {
            '$and': [{
                'department': {
                    'name': '技术部'
                }
            }, {
                'addresses': {
                    'location': '北京666'
                }
            }]
        }})) == 0
    assert _Business().count(
        {'create_user': {
            '$and': [{
                'department': {
                    'name': '技术部'
                }
            }, {
                'addresses': {
                    'location': '北京666'
                }
            }]
        }}) == 0
