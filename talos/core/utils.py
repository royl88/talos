# coding=utf-8
"""
本模块提供各类常用单一功能集合

"""

from __future__ import absolute_import

import calendar
import collections
import datetime
import fnmatch
import hashlib
import inspect
import json
import numbers
import os
import random
import re
import socket
import sys
import traceback
import uuid

import six


class ComplexEncoder(json.JSONEncoder):
    """加强版的JSON Encoder，支持日期、日期+时间类型的转换"""
    def default(self, obj):
        # fix, 不要使用strftime，当超过1900年时会报错
        if isinstance(obj, datetime.datetime):
            return obj.isoformat(' ').split('.')[0]
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def get_hostname():
    """
    获取主机名

    :returns: 主机名
    :rtype: string
    """
    return socket.gethostname()


def encrypt_password(password, salt):
    """
    对原始密码和盐进行加密码，返回加密密文

    :param password: 原始密码
    :type password: string
    :param salt: 盐，对加密进行干扰
    :type salt: string
    :returns: 加密密文
    :rtype: string
    """
    return hashlib.sha224(ensure_bytes(password + salt)).hexdigest()


def check_password(encrypted, password, salt):
    """
    检查密文是否由原始密码和盐加密而来，返回bool

    :param encrypted: 加密密码
    :type encrypted: string
    :param password: 原始密码
    :type password: string
    :param salt: 盐，对加密进行干扰
    :type salt: string
    :returns: 是否一致
    :rtype: bool
    """
    return encrypted == encrypt_password(password, salt)


def generate_salt(length=32):
    """
    生成随机的固定长度盐

    :param length: 盐的长度
    :type length: int
    :returns: 盐
    :rtype: string
    """
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_ []{}<>~`+=,.;:/?|'
    salt = ''
    for idx in range(length):
        salt += random.choice(chars)
    return salt


def get_function_name():
    """
    获取当前函数名, 以下是收集的各项获取当前函数名称的各种方式，相对于其他处理此类操作较慢
    # coding=utf-8
    import inspect
    import sys
    import time
    import traceback

    def deeper(func, depth):
        if depth > 0:
            return deeper(func, depth - 1)
        else:
            return func()

    def no_stack():
        # do no inspection, measure the cost of deeper()
        return "deeper"

    def show_stack():
        name = inspect.stack()[1][3]
        return name


    def show_stack_zero():
        name = inspect.stack(0)[1][3]
        return name

    def show_trace():
        frame = traceback.extract_stack()[-2]
        name = getattr(frame, 'name', frame[2])
        return name

    def show_limit():
        frame = traceback.extract_stack(limit=2)[-2]
        name = getattr(frame, 'name', frame[2])
        return name

    def sys_traceback():
        frame = sys._getframe().f_back
        frame_info = traceback.extract_stack(f=frame, limit=1)[0]
        name = getattr(frame_info, 'name', frame_info[2])
        return name

    def sys_inspect():
        frame = sys._getframe().f_back
        name = inspect.getframeinfo(frame)[2]
        return name

    def inspect_inspect():
        frame = inspect.currentframe().f_back
        name = inspect.getframeinfo(frame)[2]
        return name

    def measure_time(func, repeat=1000, stack=10):
        total = 0
        name = None
        for _ in range(repeat):
            start = time.time()
            name = deeper(func, stack)
            span = time.time() - start
            total = total + span
        print(name, "repeat:{0} stack:{1} cost:{2:.2f} sec".format(repeat, stack, total))

    print('no measurement')
    measure_time(no_stack)
    measure_time(no_stack, stack=20)
    print('inspect.stack (run 10% as many times, because slow)')
    measure_time(show_stack, repeat=100)
    measure_time(show_stack, repeat=100, stack=100)
    print('inspect.stack(0) (run 10% as many times, because slow)')
    measure_time(show_stack_zero, repeat=100)
    measure_time(show_stack_zero, repeat=100, stack=100)
    print('traceback.extract_stack')
    measure_time(show_trace)
    measure_time(show_trace, stack=100)
    print('traceback.extract_stack + limit')
    measure_time(show_limit)
    measure_time(show_limit, stack=100)
    print('sys.getframe + traceback')
    measure_time(sys_traceback)
    measure_time(sys_traceback, stack=100)
    print('sys.getframe + inspect')
    measure_time(sys_inspect)
    measure_time(sys_inspect, stack=100)
    print('inspect.currentframe + inspect')
    measure_time(inspect_inspect)
    measure_time(inspect_inspect, stack=100)

    :returns: 当前函数名
    :rtype: string
    """
    frame = sys._getframe().f_back
    frame_info = traceback.extract_stack(f=frame, limit=1)[0]
    name = getattr(frame_info, 'name', frame_info[2])
    return name
    # return inspect.stack(0)[1][3]


def walk_dir(dir_path, pattern):
    """
    递归遍历文件夹，列出所有符合pattern模式的文件

    :param dir_path: 文件夹路径
    :type dir_path: str
    :param pattern: 过滤模式
    :type pattern: str
    :returns: 文件列表
    :rtype: list
    """
    result = []
    for root, dirs, files in os.walk(dir_path):
        for name in files:
            filename = os.path.join(root, name)
            if fnmatch.fnmatch(filename, pattern):
                result.append(filename)
    return result


def generate_uuid(dashed=False, version=1, lower=True):
    """
    创建一个随机的UUID

    :param dashed: 是否包含 - 字符
    :type dashed: bool
    :param version: UUID生成算法
    :type version: int
    :param lower: 是否小写(默认)
    :type lower: bool
    :returns: UUID
    :rtype: string
    """
    func = getattr(uuid, 'uuid' + str(version))
    if dashed:
        guid = str(func())
    else:
        guid = func().hex
    if lower:
        return guid
    return guid.upper()


def generate_prefix_uuid(prefix, length=16):
    """
    创建一个带指定前缀的类有序uuid标识，最小长度8时，测试碰撞概率如下
    Linux 3.10.0-693.17.1.el7.x86_64 
    length=8 100w碰撞0
    length=8 1000w碰撞0
    length=8 1500w碰撞0

    :param prefix: 前缀
    :type prefix: string
    :param length: 随机串长度
    :type length: int
    :returns: UUID
    :rtype: string
    """
    if length < 8 or length > 40:
        raise ValueError('8 <= length <= 40')
    uuid1 = uuid.uuid1().hex
    uuid4 = uuid.uuid4().hex
    uid = ''.join([prefix, uuid1[:8], uuid4[:length - 8]])
    return uid


def unixtime(dt_obj):
    """
    将DataTime对象转换为unix时间

    :param dt_obj: datetime.datetime 对象
    :type dt_obj: datetime.datetime
    :returns: unix时间
    :rtype: float
    """
    return calendar.timegm(dt_obj.utctimetuple())


def dttime(ts):
    """
    将DataTime对象转换为unix时间

    :param ts: unix时间
    :type ts: float
    :returns: datetime.datetime 对象
    :rtype: datetime.datetime
    """
    return datetime.datetime.fromtimestamp(ts)


def bool_from_string(subject, strict=False, default=False):
    """
    将字符串转换为bool值

    :param subject: 待转换对象
    :type subject: str
    :param strict: 是否只转换指定列表中的值
    :type strict: bool
    :param default: 转换失败时的默认返回值
    :type default: bool
    :returns: 转换结果
    :rtype: bool
    """
    TRUE_STRINGS = ('1', 't', 'true', 'on', 'y', 'yes')
    FALSE_STRINGS = ('0', 'f', 'false', 'off', 'n', 'no')
    if isinstance(subject, bool):
        return subject
    if not isinstance(subject, six.string_types):
        subject = six.text_type(subject)

    lowered = subject.strip().lower()

    if lowered in TRUE_STRINGS:
        return True
    elif lowered in FALSE_STRINGS:
        return False
    elif strict:
        acceptable = ', '.join("'%s'" % s for s in sorted(TRUE_STRINGS + FALSE_STRINGS))
        msg = "Unrecognized value '%(val)s', acceptable values are: %(acceptable)s" % {
            'val': subject,
            'acceptable': acceptable
        }
        raise ValueError(msg)
    else:
        return default


def is_string_type(value):
    """
    判断value是否字符类型，兼容python2、python3

    :param value: 输入值
    :type value: any
    :returns: 判断结果
    :rtype: bool
    """
    if six.PY3:
        return isinstance(value, (str, bytes))
    return isinstance(value, basestring)


def is_list_type(value):
    """
    判断value是否列表类型，兼容python2、python3

    :param value: 输入值
    :type value: any
    :returns: 判断结果
    :rtype: bool
    """
    return isinstance(value, (list, set, tuple))


def is_number_type(value):
    """
    判断value是否数字类型，int/long/float/complex

    :param value: 输入值
    :type value: any
    :returns: 判断结果
    :rtype: bool
    """
    return isinstance(value, numbers.Number)


def format_kwstring(templ, **kwargs):
    """
    格式化字符串

    :param templ: 待格式化的字符串
    :type templ: string
    :returns: 格式化后的字符串
    :rtype: string
    """
    return templ % kwargs


def ensure_unicode(value, encoding='utf-8', errors='strict'):
    """
    确保将输入值转换为unicode字符，兼容python2、python3

    :param value: 输入值
    :type value: string
    :returns: unicode字符串
    :rtype: `unicode`
    """
    if not is_string_type(value):
        raise ValueError('not string type')
    if six.PY2:
        if not isinstance(value, unicode):
            return value.decode(encoding, errors=errors)
        else:
            return value
    elif six.PY3:
        if isinstance(value, bytes):
            return value.decode(encoding, errors=errors)
        else:
            return value
    raise ValueError('can not convert to unicode')


def ensure_bytes(value, encoding='utf-8', errors='strict'):
    """
    确保将输入值转换为bytes/str字符，兼容python2中返回str、python3返回bytes

    :param value: 输入值
    :type value: string
    :returns: bytes/str字符串
    :rtype: `bytes`/`str`
    """
    if not is_string_type(value):
        raise ValueError('not string type')
    if six.PY2:
        if isinstance(value, unicode):
            return value.encode(encoding, errors=errors)
        else:
            return value
    elif six.PY3:
        if isinstance(value, str):
            return value.encode(encoding, errors=errors)
        else:
            return value
    raise ValueError('can not convert to bytes')


def get_config(data, expr, default=None):
    '''
    使用a.[b].c表达式从对象中获取值
    :param data:     对象,支持getattr的任意对象
    :type data:      any
    :param expr:     路径表达式，eg. log.path
    :type expr:      str
    :param default:  如果表达式的值不存在，则返回默认值
    :type default:   any
    '''
    names = expr.split('.')
    result = data
    for name in names:
        try:
            result = getattr(result, name)
        except AttributeError:
            result = default
            break
    return result


get_attr = get_config


def get_item(data, expr, delimiter='.', default=None):
    '''
    使用a.[b].c表达式从dict中获取值

    :param data:      数据
    :type data:       dict/list/tuple/set
    :param expr:      路径表达式，eg. log.path
    :type expr:       str
    :param delimiter: 分割符号，默认是.
    :type delimiter:  str
    :param default:   如果表达式的值不存在，则返回默认值
    :type default:    any
    '''
    class _NotExist(object):
        pass

    def _from_list(data, key, default=None):
        pattern_int = r'\[\s*(\d+)\s*\]'
        pattern_string = r'\[\s*([-_a-zA-Z0-9]+)\s*\]'
        matches = re.search(pattern_int, key)
        index = None
        value = default
        # 如果在key中找到索引访问
        if matches:
            index = int(matches.groups()[0])
            # 确认索引值在区间[0, len(data))，取值并赋值到value
            if len(data) > index:
                value = data[index]
        # 没有找到索引访问，尝试内部字典方式
        # [{'a': 1}, {'a': 2}] -> [1, 2]
        else:
            matches = re.search(pattern_string, key)
            if matches:
                inner_key = matches.groups()[0]
                inner_values = []
                for item in data:
                    inner_value = item.get(inner_key, VALUE_NOT_EXIST)
                    if inner_value != VALUE_NOT_EXIST:
                        inner_values.append(inner_value)
                if len(inner_values) > 0:
                    value = inner_values
        return value

    VALUE_NOT_EXIST = _NotExist()
    keys = expr.split(delimiter)
    value = data
    for k in keys:
        # 如果key无效，直接返回default
        if len(k) == 0:
            value = VALUE_NOT_EXIST
            break
        # 如果key无效，直接返回default
        if value == VALUE_NOT_EXIST:
            break

        # 当前value是list/tuple/str/unicode/bytes
        if isinstance(value, collections.Sequence):
            value = _from_list(value, k, default=VALUE_NOT_EXIST)
        # 当前value是dict/orderdict/counter，获取字典对应k的值，并赋值到value
        elif isinstance(value, collections.Mapping):
            value = value.get(k, VALUE_NOT_EXIST)
        # 否则直接返回default
        else:
            value = VALUE_NOT_EXIST
    if value == VALUE_NOT_EXIST:
        value = default
    return value
