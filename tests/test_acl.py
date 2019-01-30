# coding=utf-8
import pytest

from talos.core import acl

# list_user：列出所有用户
# create_user：创建用户
# update_user：更新用户
# delete_user：删除用户
# list_me：获取个人信息
# update_me：创建用户
# disable_me：禁用自身用户
# spec_allow：测试嵌套的可通过权限
ACL_POLICY_1 = {
    'admin': {'parents': ['readonly', 'readwrite'], 'rules': [('list_user', True), ('create_user', True), ('update_user', True), ('delete_user', True)]},
    'readonly': {'parents': None, 'rules': [('list_me', True)]},
    'readwrite': {'parents': ['spec'], 'rules': [
        ('update_me', True),
        ('disable_me', False)]},
    'spec': {'parents': None, 'rules': [
        ('spec_allow', True)]}
}


class PolicyProxy(object):

    def __init__(self, name):
        self._name = name

    def __str__(self):
        return self._name


class ActionProxy(object):

    def __init__(self, name):
        self._name = name

    def __str__(self):
        return self._name


def build_acl(data):
    access = acl.Registry()
    for p, v in data.items():
        parents = v.get('parents', None)
        rules = v.get('rules', [])
        access.add_policy(p, parents)
        for n, a in rules:
            if a:
                access.allow(p, n)
            else:
                access.deny(p, n)
    return access


def build_object_acl(data):
    access = acl.Registry()
    for p, v in data.items():
        parents = v.get('parents', None)
        if parents:
            parents = [PolicyProxy(parent) for parent in parents]
        rules = v.get('rules', [])
        access.add_policy(PolicyProxy(p), parents)
        for n, a in rules:
            if a:
                access.allow(PolicyProxy(p), ActionProxy(n))
            else:
                access.deny(PolicyProxy(p), ActionProxy(n))
    return access


def test_allow():
    access = build_acl(ACL_POLICY_1)
    assert access.is_allowed(
        [('*', 'admin')], 'a', 'list_user') is True
    assert access.is_allowed(
        [('a[123]b', 'admin')], 'a3b', 'list_user') is True
    assert access.is_allowed(
        [('*', 'admin')], 'a', 'create_user') is True
    assert access.is_allowed(
        [('*', 'admin')], 'a', 'update_user') is True
    assert access.is_allowed(
        [('*', 'admin')], 'a', 'delete_user') is True
    assert access.is_allowed(
        [('*', 'admin')], 'a', 'list_me') is True
    assert access.is_allowed(
        [('*', 'admin')], 'a', 'update_me') is True
    assert access.is_allowed(
        [('*', 'admin')], 'a', 'spec_allow') is True
    assert access.is_allowed(
        [('a', 'admin')], 'a', 'spec_allow') is True
    assert access.is_allowed(
        [(('a', '*'), 'admin')], ('a', '1'), 'spec_allow') is True
    assert access.is_allowed(
        [(('a', '1'), 'readonly'), (('a', '2'), 'admin')], ('a', '2'), 'spec_allow') is True
    assert access.is_allowed(
        [(('a', '1'), 'readonly'), (('a', '2'), 'spec')], ('a', '2'), 'spec_allow') is True
    assert access.is_allowed(
        [('*', 'spec')], '', 'spec_allow') is True


def test_deny():
    access = build_acl(ACL_POLICY_1)
    assert access.is_allowed(
        [('*', 'admin')], '', 'disable_me') is False
    assert access.is_allowed(
        [('*', 'readwrite')], '', 'disable_me') is False


def test_none():
    access = build_acl(ACL_POLICY_1)
    assert access.is_allowed(
        [('a[123]b', 'admin')], 'a3', 'list_user') is None
    assert access.is_allowed(
        [('a', 'admin')], 'b', 'spec_allow') is None
    assert access.is_allowed(
        [('a', 'readonly')], 'a', 'spec_allow') is None
    assert access.is_allowed(
        [(('a', '1'), 'admin')], ('a', '2'), 'spec_allow') is None
    assert access.is_allowed(
        [(('a', '1'), 'admin'), (('a', '2'), 'readonly')], ('a', '2'), 'spec_allow') is None
    assert access.is_allowed(
        [('*', 'readwrite')], '', 'undefined') is None


def test_object_allow():
    access = build_object_acl(ACL_POLICY_1)
    assert access.is_allowed(
        [('*', PolicyProxy('admin'))], 'a', ActionProxy('list_user')) is True
    assert access.is_allowed(
        [('a[123]b', PolicyProxy('admin'))], 'a3b', ActionProxy('list_user')) is True
    assert access.is_allowed(
        [('*', PolicyProxy('admin'))], 'a', ActionProxy('create_user')) is True
    assert access.is_allowed(
        [('*', PolicyProxy('admin'))], 'a', ActionProxy('update_user')) is True
    assert access.is_allowed(
        [('*', PolicyProxy('admin'))], 'a', ActionProxy('delete_user')) is True
    assert access.is_allowed(
        [('*', PolicyProxy('admin'))], 'a', ActionProxy('list_me')) is True
    assert access.is_allowed(
        [('*', PolicyProxy('admin'))], 'a', ActionProxy('update_me')) is True
    assert access.is_allowed(
        [('*', PolicyProxy('admin'))], 'a', ActionProxy('spec_allow')) is True
    assert access.is_allowed(
        [('a', PolicyProxy('admin'))], 'a', ActionProxy('spec_allow')) is True
    assert access.is_allowed(
        [(('a', '*'), PolicyProxy('admin'))], ('a', '1'), ActionProxy('spec_allow')) is True
    # mix policy type
    assert access.is_allowed(
        [(('a', '1'), PolicyProxy('readonly')), (('a', '2'), 'admin')], ('a', '2'), ActionProxy('spec_allow')) is True
    assert access.is_allowed(
        [(('a', '1'), PolicyProxy('readonly')), (('a', '2'), PolicyProxy('spec'))], ('a', '2'), ActionProxy('spec_allow')) is True
    assert access.is_allowed(
        [('*', PolicyProxy('spec'))], '', ActionProxy('spec_allow')) is True


def test_object_deny():
    access = build_object_acl(ACL_POLICY_1)
    assert access.is_allowed(
        [('*', PolicyProxy('admin'))], '', ActionProxy('disable_me')) is False
    assert access.is_allowed(
        [('*', PolicyProxy('readwrite'))], '', ActionProxy('disable_me')) is False


def test_object_none():
    access = build_object_acl(ACL_POLICY_1)
    assert access.is_allowed(
        [('a[123]b', PolicyProxy('admin'))], 'a3', ActionProxy('list_user')) is None
    assert access.is_allowed(
        [('a', PolicyProxy('admin'))], 'b', ActionProxy('spec_allow')) is None
    assert access.is_allowed(
        [('a', PolicyProxy('readonly'))], 'a', ActionProxy('spec_allow')) is None
    assert access.is_allowed(
        [(('a', '1'), PolicyProxy('admin'))], ('a', '2'), ActionProxy('spec_allow')) is None
    assert access.is_allowed(
        [(('a', '1'), PolicyProxy('admin')), (('a', '2'), PolicyProxy('readonly'))], ('a', '2'), ActionProxy('spec_allow')) is None
    assert access.is_allowed(
        [('*', PolicyProxy('readwrite'))], '', ActionProxy('undefined')) is None


def test_error():
    access = build_object_acl(ACL_POLICY_1)
    with pytest.raises(ValueError):
        access.is_allowed(
            [('*', 'admin')], None, 'anything')
    with pytest.raises(ValueError):
        access.is_allowed(
            [('*', PolicyProxy('admin'))], None, ActionProxy('anything'))
    with pytest.raises(ValueError):
        access.is_allowed(
            [(('t1', 't2'), PolicyProxy('admin'))], None, ActionProxy('anything'))
    with pytest.raises(ValueError):
        access.is_allowed(
            [(None, PolicyProxy('admin'))], '', ActionProxy('anything'))
    with pytest.raises(ValueError):
        access.is_allowed(
            [(None, PolicyProxy('admin'))], ('i1', 'i2'), ActionProxy('anything'))
    with pytest.raises(ValueError):
        access.is_allowed(
            [(('t1', 't2'), PolicyProxy('admin'))], 'i1', ActionProxy('anything'))
    with pytest.raises(ValueError):
        access.is_allowed(
            [('t1', PolicyProxy('admin'))], ('i1', 'i2'), ActionProxy('anything'))


def test_none_pass():
    access = build_object_acl(ACL_POLICY_1)
    assert access.is_allowed(
        [(None, PolicyProxy('admin'))], None, ActionProxy('list_user')) is True
    assert access.is_allowed(
        [(None, PolicyProxy('admin'))], None, ActionProxy('disable_me')) is False
    assert access.is_allowed(
        [(None, PolicyProxy('admin'))], None, ActionProxy('undefined')) is None
