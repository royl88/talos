# coding=utf-8
"""
本模块提供通用ACL权限验证功能

"""

from __future__ import absolute_import

import fnmatch

__all__ = ["Registry"]


class Registry(object):
    """
    ACL管理器

    本类提供的函数的参数对象, 必须是可key化的对象，默认key提取函数为str，key函数返回必须是字符串
    (关于为何不使用hash? hash返回整数，存在不可控的碰撞情况，所以直接交给用户控制唯一性)

    - policy: 策略，可以指定从父策略继承
    - action：动作，一个操作+资源
    - template：模板匹配规则

    """

    def __init__(self):
        self._fmatch = fnmatch.fnmatchcase
        self._fkey = str
        self._policies = {}
        self._allowed = {}
        self._denied = {}

    def _match(self, params):
        """
        匹配值与模式

        :param params: 值, 模式
        :type params: tuple
        """
        pattern, value = params
        return self._fmatch(value, pattern)

    def _normalize_string(self, datas):
        """

        :param datas:
        :type datas:
        """
        if isinstance(datas, (list, tuple)):
            template = '(' + ','.join(['%s'] * len(datas)) + ')'
            return template % datas
        else:
            return self._fkey(datas)

    def set_fmatch(self, func):
        '''
        更改匹配函数，函数返回值为bool
        :param func: 匹配校验函数, eg. func(value, pattern)
        :type func: callable
        '''
        # strong ref
        self._fmatch = func

    def set_fkey(self, func):
        '''
        更改key提取函数, 函数返回类型必须为字符串
        :param func: 匹配校验函数, eg. func(object)
        :type func: callable
        :r:
        '''
        # strong ref
        self._fkey = func

    def add_policy(self, policy, parents=None):
        """
        添加策略到管理器, 可以提供策略的父类策略关系.

        :param policy: 策略对象
        :param parents: 继承的父策略列表，每个元素是策略对象
        """
        parents = parents or set()
        self._policies[self._fkey(policy)] = set(
            [self._fkey(x) for x in parents])

    def allow(self, policy, action):
        """
        添加一条允许的规则, 继承policy意味着操作权限也同样被继承

        :param policy: 策略对象(可str化)
        :param action: 动作对象(可str化)，动作 = 操作 + 资源
        """
        key = self._fkey(policy)
        actions = self._allowed.setdefault(key, set())
        actions.add(self._normalize_string(action))

    def deny(self, policy, action):
        """
        添加一条禁用的规则，继承policy意味着操作权限也同样被继承

        :param policy: 策略对象(可str化)
        :param action: 动作对象(可str化)，动作 = 操作 + 资源
        """
        key = self._fkey(policy)
        actions = self._denied.setdefault(key, set())
        actions.add(self._fkey(action))

    def _expand_policies(self, policies, within=True):
        for policy in policies:
            child_policies = self._policies.get(policy, [])
            for sub_policy in child_policies:
                yield sub_policy
            if within:
                yield policy
            for sub_policy in self._expand_policies(child_policies, within=False):
                yield sub_policy

    def is_allowed(self, template_policies, template_instance, action):
        """
        检查策略是否能对资源进行本操作，如果权限检查通过，返回True，否则返回False，如果没有对应的规则，则返回None

        默认模板匹配不同于正则表达式，遵循shell-style匹配规则

        * 模式* ，匹配任意长度字符
        * 模式? ，匹配单个字符
        * 模式[seq] ，匹配序列中的单个字符
        * 模式[!seq] ，匹配不在序列中的单个字符

        :param template_policies: 可用的模板策略，tuple(template, policy) ,template是匹配模板对象(tuple)，policy是策略对象(可str化)，
        由于默认是shell-style匹配规则，如果模板对象是一个list对象，str化后会成为"['1', 'form']"产生不正确的结果，使用中需要注意
        :param template_instance: 对应template的实际数据对象(可str化)
        :param action: 动作对象(可str化)，动作 = 操作 + 资源
        :returns: 如果明确被允许，返回True；如果明确被禁止，返回False；否则返回None
        :rtype: bool
        """
        policies = set()
        # 匹配出用户在本次context下的授权策略
        for context, policy in template_policies:
            if context is None and template_instance is None:
                policies.add(self._fkey(policy))
                continue
            if not (isinstance(context, basestring) ^ isinstance(template_instance, basestring)) or not (isinstance(context, (list, set, tuple)) ^ isinstance(template_instance, (list, set, tuple))):
                raise ValueError(
                    'template type mismatch with template_instance')
            results = map(self._match, zip(context, template_instance))
            if len(results) == 0 or sum(results) == len(results):
                policies.add(self._fkey(policy))

        expand_policies = set([p for p in self._expand_policies(policies)])
        # 检查是否被禁止
        for policy in expand_policies:
            actions = self._denied.get(policy, [])
            if actions and self._fkey(action) in actions:
                return False
        # 检查是否被允许
        for policy in expand_policies:
            actions = self._allowed.get(policy, [])
            if actions and self._normalize_string(action) in actions:
                return True
        return None
