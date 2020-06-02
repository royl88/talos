# coding=utf-8
"""
本模块提供配置文件选项定义以及载入功能，外部需统一通过本模块的CONF来读取配置信息

"""

from __future__ import absolute_import

from collections import Mapping
import copy
import json
import functools
import re
import warnings

from mako.template import Template
from talos.core import utils

VAR_REGISTER = {}
CONFIG_RESERVED = ('set_options', 'from_files', 'iterkeys', 'itervalues', 'iteritems', 'keys', 'values', 'items', 'get', 'to_dict', '_opts',
                   '_raise_not_exist',)
NAME_RULE = re.compile('^[_a-zA-Z][_a-zA-Z0-9]*$')


def intercept(*vars):

    def _intercept(func):

        @functools.wraps(func)
        def __intercept(*args, **kwargs):
            ret = func(*args, **kwargs)
            return ret

        for var in vars:
            funcs = VAR_REGISTER.setdefault(var, [])
            funcs.append(__intercept)
        return __intercept

    return _intercept


def call_intercepters(var, value):
    funcs = VAR_REGISTER.get(var, [])
    new_value = value
    for func in funcs:
        new_value = func(new_value, value)
    return new_value


def _valid_expr(keys):
    return 'CONF.' + '.'.join([k['name'] if k.get('attr_type', True) else '["' + k['name'] + '"]' for k in keys])


def _simple_expr(keys):
    return 'CONF.' + '.'.join([k['name'] for k in keys])


def _validate(data, keys=None):
    for key, value in data.items():
        allkeys = keys[:] if keys else []
        o_key = {'name': key, 'attr_type': True}
        allkeys.append(o_key)
        if key.startswith('${') and key.endswith('}'):
            pass
        else:
            if not NAME_RULE.match(key):
                o_key['attr_type'] = False
                warnings.warn('[config] access %s instead of %s' % (_valid_expr(allkeys), _simple_expr(allkeys)), SyntaxWarning)
            if key in CONFIG_RESERVED:
                o_key['attr_type'] = False
                warnings.warn('[config] access %s instead of %s' % (_valid_expr(allkeys), _simple_expr(allkeys)), SyntaxWarning)
        if isinstance(value, Mapping):
            _validate(value, keys=allkeys)
                

class Config(Mapping):
    """
    一个类字典的属性访问配置类， 表示一组或者多组实际的配置项
    1. 当属性是标准变量命名且非预留函数名时，可直接a.b.c方式访问
    2. 否则可以使用a['b-1'].c访问(item方式访问时会返回Config对象)
    3. 当属性值刚好Config已存在函数相等时，将进行函数调用而非属性访问！！！
       保留函数名如下：set_options，from_files，iterkeys，itervalues，iteritems，keys，values，items，get，to_dict，_opts，python魔法函数
    比如{
        "my_config": {"from_files": {"a": {"b": False}}}
    }
    无法通过CONF.my_config.from_files来访问属性，需要稍作转换：CONF.my_config['from_files'].a.b 如此来获取
    """

    def __init__(self, opts, raise_not_exist=True, check_reserved=False):
        self._opts = opts or {}
        if check_reserved:
            _validate(self._opts)
        self._raise_not_exist = raise_not_exist

    def set_options(self, opts, check_reserved=False):
        self._opts = opts or {}
        if check_reserved:
            _validate(self._opts)

    def __repr__(self):
        return '<Config(%s, raise_not_exist=%s)>' % (str(self._opts), self._raise_not_exist)

    def __call__(self, opts, check_reserved=False):
        """用另外一个opts来重新初始化自己"""
        self._opts = opts or {}
        if check_reserved:
            _validate(self._opts)

    def from_files(self, opt_files, ignore_undefined, check_reserved=False):
        """
        载入配置文件，并按照顺序进行合并配置项，如果配置项合并后依然是UNSET，则抛ValueError异常提示用户

        :param opt_files: 配置文件列表
        :type opt_files: list
        :param ignore_undefined: 是否忽略为定义的配置项，True：忽略app中没有定义的用户输入项，已定义项则覆盖， False：使用用户定义项进行覆盖
        :type ignore_undefined: bool
        :raises: ValueError
        """

        def _update(data_src, data_dst, ignore_undefined):
            if ignore_undefined:
                for key, value in data_src.items():
                    if isinstance(value, dict):
                        _update(value, data_dst.get(key, {}), ignore_undefined)
                    elif key in data_dst:
                        data_src[key] = data_dst[key]
            else:
                for key, value in data_dst.items():
                    if isinstance(value, dict):
                        if key in data_src:
                            _update(data_src[key], data_dst.get(key, {}), ignore_undefined)
                        else:
                            new_value = {}
                            data_src[key] = new_value
                            _update(new_value, data_dst.get(key, {}), ignore_undefined)
                    else:
                        data_src[key] = data_dst[key]

        for opt_file in opt_files:
            with open(opt_file, 'r') as f:
                _update(self._opts, json.load(f), ignore_undefined)
        if check_reserved:
            _validate(self._opts)

    def __getattr__(self, name):
        """
        魔法函数，实现.操作符访问

        :param name: 配置项
        :type name: string
        :returns: 如果是最底层配置项，则返回配置项的值，否则返回Config对象
        :rtype: any
        :raises: KeyError
        """
        try:
            value = self._opts[name]
            if isinstance(value, Mapping):
                return Config(value)
            return value
        except KeyError:
            if self._raise_not_exist:
                raise AttributeError("No Such Option: %s" % name)

    def __getitem__(self, key):
        """魔法函数，实现类字典访问"""
        value = self._opts[key]
        if isinstance(value, Mapping):
            return Config(value)
        return value

    def __contains__(self, key):
        """魔法函数，实现in操作访问"""
        return key in self._opts

    def __iter__(self):
        """魔法函数，遍历当前配置项第一层级"""
        for key in self._opts.keys():
            yield key

    def __len__(self):
        """魔法函数，实现len访问"""
        return len(self._opts)

    def iterkeys(self):
        'D.iterkeys() -> an iterator over the keys of D'
        return iter(self._opts)

    def itervalues(self):
        'D.itervalues() -> an iterator over the values of D'
        for key in self._opts:
            yield self._opts[key]

    def iteritems(self):
        'D.iteritems() -> an iterator over the (key, value) items of D'
        for key in self._opts:
            yield (key, self._opts[key])

    def keys(self):
        "D.keys() -> list of D's keys"
        return list(self._opts)

    def items(self):
        "D.items() -> list of D's (key, value) pairs, as 2-tuples"
        return [(key, self._opts[key]) for key in self._opts]

    def values(self):
        "D.values() -> list of D's values"
        return [self._opts[key] for key in self._opts]

    def get(self, key, default=None):
        'D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.'
        try:
            return self._opts[key]
        except KeyError:
            return default

    def to_dict(self):
        return self._opts


def setup(path, default_opts=None, dir_path=None, ignore_undefined=False):
    """
    载入配置文件

    :param path: 配置文件路径
    :type path: str
    :param dir_path: 额外配置文件文件夹，会与配置文件信息进行合并
    :type dir_path: str
    """
    default_opts = default_opts or CONFIG_OPTS
    config_files = []
    config_files.append(path)
    if dir_path:
        for filename in utils.walk_dir(dir_path, '*.conf'):
            config_files.append(filename)

    ref = Config(copy.deepcopy(default_opts))
    ref.from_files(config_files, ignore_undefined=ignore_undefined)
    if ref.variables.to_dict():
        context = {}
        for k, v in ref.variables.items():
            context[k] = call_intercepters(k, v)
        opts = ref.to_dict()
        s_opts = json.dumps(opts)
        tpl = Template(s_opts, strict_undefined=True)
        ref = Config(json.loads(tpl.render(**context)))
    CONF(ref.to_dict(), check_reserved=True)


# 程序所需的最小配置项
CONFIG_OPTS = {
    'host': utils.get_hostname(),
    'language': 'en',
    'locale_app': 'talos',
    'locale_path': './etc/locale',
    'override_defalut_middlewares': False,
    'server': {
        'bind': '127.0.0.1',
        'port': 9001,
        'backlog': 2048,
    },
    "variables": {
    },
    'controller': {
        'list_size_limit_enabled': False,
        'list_size_limit': None,
        'criteria_key': {
            'offset': '__offset',
            'limit': '__limit',
            'orders': '__orders',
            'fields': '__fields',
            'filter_delimiter': '__'
        }
    },
    'log': {
        'gunicorn_access': './access.log',
        'gunicorn_error': './error.log',
        "log_console": True,
        'path': './server.log',
        'level': 'INFO',
        'format_string': '%(asctime)s.%(msecs)03d %(process)d %(levelname)s %(name)s:%(lineno)d [-] %(message)s',
        'date_format_string': '%Y-%m-%d %H:%M:%S',
    },
    'db': {
        'connection': None,
        # 'pool_size': 3,
        # 'pool_recycle': 60 * 60,
        # 'pool_timeout': 5,
        # 'max_overflow': 5,
    },
    'dbs': {
    },
    'dbcrud': {
        'unsupported_filter_as_empty': False,
        'dynamic_relationship': True,
        'dynamic_load_method': 'joinedload',
        'detail_relationship_as_summary': False,
    },
    'cache': {
        'type': 'dogpile.cache.memory',
        'expiration_time': 60
    },
    'application': {
        'names': []
    },
    'rate_limit': {
        'enabled': False,
        'storage_url': 'memory://',
        'strategy': 'fixed-window',
        'global_limits': None,
        'per_method': True,
        'header_reset': 'X-RateLimit-Reset',
        'header_remaining': 'X-RateLimit-Remaining',
        'header_limit': 'X-RateLimit-Limit',
    },
    'celery': {
        'talos_on_user_schedules_changed': [],
        'talos_on_user_schedules': []
    }

}

CONF = Config(None)
