# coding=utf-8
"""
本模块提供通用ACL权限验证功能

"""

from __future__ import absolute_import

import fnmatch
from talos.core import utils

__all__ = ["Registry"]


class Registry(object):
    """
    ACL管理器

    - policy: 策略，可以指定从父策略继承
    - action：动作，一个操作+资源，是否允许动作可以作为一个规则被添加到策略中
    - template：模板匹配规则

    policy、action可以是字符串或对象

    - 若是对象，默认key提取函数为str，所以对象需要提供__str__方法
    (关于为何不使用hash? hash返回整数，存在不可控的碰撞情况，所以直接交给用户控制唯一性)
    - key提取函数可以通过set_fkey函数重新定义，用户提供的key提取函数必须返回一个字符串

    template是匹配模板, 默认模板匹配不同于正则表达式，遵循shell-style匹配规则

    * 模式* ，匹配任意长度字符
    * 模式? ，匹配单个字符
    * 模式[seq] ，匹配序列中的单个字符
    * 模式[!seq] ，匹配不在序列中的单个字符

    add_policy('admin', ['readonly', 'readwrite'])
    add_action('admin', 'manage', True)
    # 或者 allow('admin', 'manage')
    # 或者 deny('admin', 'manage')
    is_allowed((None, 'admin'), None, 'manage')
    is_allowed(('*', 'admin'), 'id123', 'manage')
    """

    def __init__(self):
        self._fmatch = fnmatch.fnmatchcase
        self._fkey = str
        self._policies = {}
        self._allowed = {}
        self._denied = {}

    def _match(self, params):
        """
        匹配值,模式 的匹配校验

        :param params: 值, 模式
        :type params: tuple/list
        """
        value, pattern = params
        return self._fmatch(value, pattern)

    def set_fmatch(self, func):
        """
        更改匹配值,模式 的匹配校验函数，函数返回值为bool
        :param func: 匹配校验函数, eg. func(value, pattern)
        :type func: callable
        """
        # strong ref
        self._fmatch = func

    def set_fkey(self, func):
        """
        更改policy,action的key提取函数, 函数返回类型必须为字符串
        :param func: key提取函数, eg. func(action)
        :type func: callable
        """
        # strong ref
        self._fkey = func

    def add_policy(self, policy, parents=None):
        """
        添加策略, 可以提供策略的父类策略关系.

        :param policy: 策略对象
        :param parents: 继承的父策略列表，每个元素是策略对象
        """
        parents = parents or set()
        self._policies[self._fkey(policy)] = set(
            [self._fkey(x) for x in parents])

    def add_action(self, policy, action, allow):
        """
        添加动作到策略，可以指定是否允许

        :param policy: 策略对象
        :param action: 动作对象
        :param allow: 是否允许
        :type allow: bool
        """
        if allow:
            self.allow(policy, action)
        else:
            self.deny(policy, action)

    def allow(self, policy, action):
        """
        添加一条允许的规则, 继承policy意味着操作权限也同样被继承

        :param policy: 策略对象
        :param action: 动作对象
        """
        key = self._fkey(policy)
        actions = self._allowed.setdefault(key, set())
        actions.add(self._fkey(action))

    def deny(self, policy, action):
        """
        添加一条禁用的规则，继承policy意味着操作权限也同样被继承

        :param policy: 策略对象
        :param action: 动作对象
        """
        key = self._fkey(policy)
        actions = self._denied.setdefault(key, set())
        actions.add(self._fkey(action))

    def _expand_policies(self, policies, within=True):
        """
        展开policy继承关系，返回policy生成器

        :param policies: 策略对象列表
        :type policies: list/tuple/set
        :param within: 是否包含policies列表内的policy，
            True返回  policies + sub_policies，
            False返回 sub_policies
        :type within: bool
        """
        for policy in policies:
            child_policies = self._policies.get(policy, [])
            for sub_policy in child_policies:
                yield sub_policy
            if within:
                yield policy
            for sub_policy in self._expand_policies(child_policies, within=False):
                yield sub_policy

    def is_allowed(self, template_policies, instance, action):
        """
        检查策略是否能对资源进行本操作，如果权限检查通过，返回True，否则返回False，如果没有对应的规则，则返回None

        :param template_policies: 可用的模板策略，tuple(template, policy),
                template是匹配模板对象None/string/tuple[string], 如果更改了match函数，类型为None/match参数对象/tuple[match参数对象]，
                policy是策略对象
        :param instance: 对应template的实例匹配数据，比如template='*', instance='123', 那么匹配通过
        :param action: 动作对象
        :returns: 如果明确被允许，返回True；如果明确被禁止，返回False；
                禁止优先于允许（如果一个策略允许，一个策略禁止，结果依然是禁止）；否则返回None
        :rtype: bool
        """
        policies = set()
        action_key = self._fkey(action)
        # 匹配出用户在本次context下的授权策略
        for context, policy in template_policies:
            policy_key = self._fkey(policy)
            if context is None and instance is None:
                policies.add(policy_key)
                continue
            if (context is None) ^ (instance is None) or \
                    isinstance(context, (list, tuple)) ^ isinstance(instance, (list, tuple)):
                raise ValueError(
                    'template type mismatch with instance')
            results = []
            if utils.is_string_type(context) and utils.is_string_type(instance):
                # don't map it
                results = [self._match((instance, context))]
            else:
                results = list(map(self._match, zip(instance, context)))
            if len(results) == 0 or sum(results) == len(results):
                policies.add(policy_key)

        expand_policies = set([p for p in self._expand_policies(policies)])
        # 检查是否被禁止
        for policy in expand_policies:
            actions = self._denied.get(policy, [])
            if actions and action_key in actions:
                return False
        # 检查是否被允许
        for policy in expand_policies:
            actions = self._allowed.get(policy, [])
            if actions and action_key in actions:
                return True
        return None
