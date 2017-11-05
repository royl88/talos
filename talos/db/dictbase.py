# coding=utf-8
"""
本模块提供数据库模型字段遍历功能，以此为基础可以将实例转换为字典

"""

from __future__ import absolute_import

import six
from sqlalchemy.orm import object_mapper


class ModelBase(six.Iterator):
    """Model模型基类"""
    __table_initialized__ = False

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        # Don't use hasattr() because hasattr() catches any exception, not only
        # AttributeError. We want to passthrough SQLAlchemy exceptions
        # (ex: sqlalchemy.orm.exc.DetachedInstanceError).
        try:
            getattr(self, key)
        except AttributeError:
            return False
        else:
            return True

    def get(self, key, default=None):
        """获取Model属性，模仿dict行为"""
        return getattr(self, key, default)

    @property
    def _extra_keys(self):
        """
        用户扩展属性

        子类可以重写这个属性，返回一个列表，使其看起来像Model有这个属性
        """
        return []

    def __iter__(self):
        columns = list(dict(object_mapper(self).columns).keys())
        # NOTE(russellb): Allow models to specify other keys that can be looked
        # up, beyond the actual db columns.  An example would be the 'name'
        # property for an Instance.
        columns.extend(self._extra_keys)

        return ModelIterator(self, iter(columns))

    def update(self, values):
        """更新Model属性，模仿dict行为."""
        for k, v in six.iteritems(values):
            setattr(self, k, v)

    def _as_dict(self):
        """Make the model object behave like a dict.

        Includes attributes from joins.
        """
        local = dict((key, value) for key, value in self)
        joined = dict([(k, v) for k, v in six.iteritems(self.__dict__)
                       if not k[0] == '_'])
        local.update(joined)
        return local

    def iteritems(self):
        """模拟dict方法."""
        return six.iteritems(self._as_dict())

    def items(self):
        """模拟dict方法."""
        return self._as_dict().items()

    def keys(self):
        """模拟dict方法."""
        return [key for key, value in self.iteritems()]


class ModelIterator(six.Iterator):
    """Model类的列枚举辅助类，使其可以使用for . in形式访问"""

    def __init__(self, model, columns):
        self.model = model
        self.i = columns

    def __iter__(self):
        return self

    # In Python 3, __next__() has replaced next().
    def __next__(self):
        n = six.advance_iterator(self.i)
        return n, getattr(self.model, n)


class DictBase(ModelBase):
    """扩展SQLAlchemy，使行对象可以转换为字典类型"""
    attributes = []
    detail_attributes = []
    summary_attributes = []

    def list_columns(self):
        """默认list级别的属性列表，自身作为主资源时的属性值，默认不带有relationship"""
        return self.attributes or [key for key, value in self]

    def get_columns(self):
        """默认get级别的详细属性列表，即自身作为主资源且尽量详细时的属性值，默认带有relationship"""
        return self.detail_attributes or self.keys()

    def sum_columns(self):
        """默认summary级别的属性列表，即被其他资源引用时能展示的属性值，默认不带有relationship"""
        return self.summary_attributes or [key for key, value in self]

    def _convert_flat_dict(self, data, prefix=None, separator='.'):
        flat_data = {}
        for key, value in data.items():
            if isinstance(value, dict):
                if prefix and prefix.strip():
                    flat_data.update(
                        self._convert_flat_dict(
                            value,
                            prefix=prefix.strip() + separator + key,
                            separator=separator))
                else:
                    flat_data.update(
                        self._convert_flat_dict(
                            value, prefix=key, separator=separator))
            else:
                if prefix and prefix.strip():
                    flat_data[prefix.strip() + separator + key] = value
                else:
                    flat_data[key] = value
        return flat_data

    def to_dict(self, prefix=None, flat_dict=False):
        """
        将自身Model的list级别的列:值转换为dict类型返回

        :param prefix: 前缀
        :type prefix: string/None
        :param flat_dict: 是否转换为扁平结构字典，以'.'作为连接符
        :type flat_dict: bool
        :returns: 字典，对应Model的列以及值
        :rtype: dict
        """
        d = {}
        for attr in self.list_columns():
            value = getattr(self, attr)
            if isinstance(value, DictBase):
                value = value.to_summary_dict(flat_dict=flat_dict)
                if flat_dict:
                    if prefix and prefix.strip():
                        d.update(
                            self._convert_flat_dict(
                                value, prefix=prefix.strip()))
                    else:
                        d.update(self._convert_flat_dict(value))
                    continue
            if isinstance(value, (tuple, list, set)):
                if value:
                    if isinstance(value[0], DictBase):
                        values = []
                        for v in value:
                            values.append(v.to_summary_dict(flat_dict=flat_dict))
                        value = values
                else:
                    value = []
            if prefix and prefix.strip():
                d[prefix.strip() + attr] = value
            else:
                d[attr] = value
        return d

    def to_detail_dict(self, prefix=None, flat_dict=False):
        """
        将自身Model的get级别的列:值转换为dict类型返回

        :param prefix: 前缀
        :type prefix: string/None
        :param flat_dict: 是否转换为扁平结构字典，以'.'作为连接符
        :type flat_dict: bool
        :returns: 字典，对应Model的列以及值
        :rtype: dict
        """
        d = {}
        for attr in self.get_columns():
            value = getattr(self, attr)
            if isinstance(value, DictBase):  # sqlalchemy.orm.collections.InstrumentedList
                value = value.to_dict(flat_dict=flat_dict)
                if flat_dict:
                    if prefix and prefix.strip():
                        d.update(
                            self._convert_flat_dict(
                                value, prefix=prefix.strip()))
                    else:
                        d.update(self._convert_flat_dict(value))
                    continue
            if isinstance(value, (tuple, list, set)):
                if value:
                    if isinstance(value[0], DictBase):
                        values = []
                        for v in value:
                            values.append(v.to_dict(flat_dict=flat_dict))
                        value = values
                else:
                    value = []
            if prefix and prefix.strip():
                d[prefix.strip() + attr] = value
            else:
                d[attr] = value
        return d

    def to_summary_dict(self, prefix=None, flat_dict=False):
        """
        将自身Model的summary级别的列:值转换为dict类型返回

        :param prefix: 前缀
        :type prefix: string/None
        :param flat_dict: 是否转换为扁平结构字典，以'.'作为连接符
        :type flat_dict: bool
        :returns: 字典，对应Model的列以及值
        :rtype: dict
        """
        d = {}
        for attr in self.sum_columns():
            value = getattr(self, attr)
            if isinstance(value, DictBase):
                value = value.to_summary_dict(flat_dict=flat_dict)
                if flat_dict:
                    if prefix and prefix.strip():
                        d.update(
                            self._convert_flat_dict(
                                value, prefix=prefix.strip()))
                    else:
                        d.update(self._convert_flat_dict(value))
                    continue
            if isinstance(value, (tuple, list, set)):
                if value:
                    if isinstance(value[0], DictBase):
                        values = []
                        for v in value:
                            values.append(v.to_summary_dict(flat_dict=flat_dict))
                        value = values
                else:
                    value = []
            if prefix and prefix.strip():
                d[prefix.strip() + attr] = value
            else:
                d[attr] = value
        return d

    def __getitem__(self, key):
        return getattr(self, key)
