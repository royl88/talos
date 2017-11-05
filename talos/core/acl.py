# coding=utf-8
"""
本模块提供通用ACL权限验证功能

"""

from __future__ import absolute_import

import fnmatch


__all__ = ["Registry"]


def normalize_string(datas):
    if isinstance(datas, (list, tuple)):
        template = '(' + ','.join(['%s'] * len(datas)) + ')'
        return template % datas
    else:
        return str(datas)


class Registry(object):
    """
    ACL管理器

    本类提供的函数的参数对象, 必须是可__str__化的对象(包含字符串对象),字符串化提供对象唯一标识
    (关于为何不使用hash? hash返回整数，存在不可控的碰撞情况，所以直接交给用户控制唯一性)

    """

    def __init__(self):
        self._policies = {}
        self._allowed = {}
        self._denied = {}

    def _make_key(self, *args):
        return ':'.join(tuple([str(item) for item in args]))

    def _match(self, value, pattern):
        return fnmatch.fnmatchcase(value, pattern)

    def add_policy(self, policy, parents=None):
        """
        添加策略到管理器, 可以提供策略的父类策略关系.

        :param policy: 策略对象(可str化)
        :param parents: 继承的父策略列表，每个元素是策略对象(可str化)
        """
        parents = parents or set()
        self._policies[str(policy)] = set([str(x) for x in parents])

    def allow(self, policy, action):
        """
        添加一条允许的规则, 继承policy意味着操作权限也同样被继承

        :param policy: 策略对象(可str化)
        :param action: 动作对象(可str化)，动作 = 操作 + 资源
        """
        key = str(policy)
        actions = self._allowed.setdefault(key, set())
        actions.add(normalize_string(action))

    def deny(self, policy, action):
        """
        添加一条禁用的规则，继承policy意味着操作权限也同样被继承

        :param policy: 策略对象(可str化)
        :param action: 动作对象(可str化)，动作 = 操作 + 资源
        """
        key = str(policy)
        actions = self._denied.setdefault(key, set())
        actions.add(str(action))

    def expand_policies(self, policies, within=True):
        for policy in policies:
            child_policies = self._policies.get(policy, [])
            for sub_policy in child_policies:
                yield sub_policy
            if within:
                yield policy
            for sub_policy in self.expand_policies(child_policies, within=False):
                yield sub_policy

    def is_allowed(self, template_policies, template_instance, action):
        """
        检查策略是否能对资源进行本操作，如果权限检查通过，返回True，否则返回False，如果没有对应的规则，则返回None

        模板不同于正则表达式，遵循shell-style匹配规则

        * 模式* ，匹配任意长度字符
        * 模式? ，匹配单个字符
        * 模式[seq] ，匹配序列中的单个字符
        * 模式[!seq] ，匹配不在序列中的单个字符

        :param template_policies: 可用的模板策略，tuple(template, policy) ,template是匹配模板对象(tuple)，policy是策略对象(可str化)，
        由于是shell-style匹配规则，如果模板对象是一个list对象，str化后会成为"['1', 'form']"产生不正确的结果，使用中需要注意
        :param template_instance: 对应template的实际数据对象(可str化)
        :param action: 动作对象(可str化)，动作 = 操作 + 资源
        :returns: 如果明确被允许，返回True；如果明确被禁止，返回False；否则返回None
        :rtype: bool
        """
        policies = set()
        # 匹配出用户在本次context下的授权策略
        for context, policy in template_policies:
            context = normalize_string(context)
            template_instance = normalize_string(template_instance)
            pattern = self._make_key(context, str(policy))
            value = self._make_key(str(template_instance), str(policy))
            if self._match(value, pattern):
                policies.add(str(policy))
        expand_policies = set([p for p in self.expand_policies(policies)])
        # 检查是否被禁止
        for policy in expand_policies:
            actions = self._denied.get(policy, [])
            if actions and str(action) in actions:
                return False
        # 检查是否被允许
        for policy in expand_policies:
            actions = self._allowed.get(policy, [])
            if actions and normalize_string(action) in actions:
                return True
        return None
