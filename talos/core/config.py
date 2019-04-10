# coding=utf-8
"""
本模块提供配置文件选项定义以及载入功能，外部需统一通过本模块的CONF来读取配置信息

"""

from __future__ import absolute_import

from collections import Mapping
import copy
import json

from talos.core import utils


class ValueNotSet(object):
    """代表没有设置，需要报错以提示用户"""
    pass


class Config(Mapping):
    """"表示一组或者多组实际的配置项"""

    def __init__(self, opts):
        self._opts = opts or {}

    def from_files(self, opt_files, ignore_undefined):
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

        def _check(data, name=None):
            for key, value in data.items():
                cur_name = copy.deepcopy(name) if name else []
                cur_name.append(key)
                if isinstance(value, dict):
                    _check(value, name=cur_name)
                if isinstance(value, ValueNotSet):
                    invalid_key = '.'.join(cur_name)
                    raise ValueError("config item: %s not set" % invalid_key)

        for opt_file in opt_files:
            with open(opt_file, 'r') as f:
                _update(self._opts, json.load(f), ignore_undefined)
        _check(self._opts)

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
            if isinstance(value, dict):
                return Config(value)
            return value
        except KeyError:
            raise AttributeError("No Such Option: %s" % name)

    def __getitem__(self, key):
        """魔法函数，实现类字典访问"""
        return self._opts[key]

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

    def to_dict(self):
        return self._opts


class Configuration(object):
    """
    代理配置类，访问这个类的属性都会被转发到Config实际属性

    此外还可以重写Config函数以实现拦截(或称delegation)
    """

    def __init__(self, config):
        self._config = config

    def __repr__(self):
        return str(self._config)

    def __getattr__(self, attr):
        return getattr(self._config, attr)

    def __call__(self, config):
        self._config = config


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

    config = Config(copy.deepcopy(default_opts))
    config.from_files(config_files, ignore_undefined=ignore_undefined)
    CONF(config)


UNSET = ValueNotSet()

# 程序所需的最小配置项
CONFIG_OPTS = {
    'host': utils.get_hostname(),
    'language': 'en',
    'locale_app': UNSET,
    'locale_path': UNSET,
    'override_defalut_middlewares': False,
    'server': {
        'bind': '127.0.0.1',
        'port': 9001,
        'backlog': 2048,
    },
    'controller': {
        'list_size_limit_enabled': False,
        'list_size_limit': None,
        'criteria_key': {
            'offset': '__offset',
            'limit': '__limit',
            'orders': '__orders',
            'fields': '__fields'
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
        'connection': UNSET,
        # 'pool_size': 3,
        # 'pool_recycle': 60 * 60,
        # 'pool_timeout': 5,
        # 'max_overflow': 5,
    },
    'dbcrud': {
        'unsupported_filter_as_empty': False
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

CONF = Configuration(None)
