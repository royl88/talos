# coding=utf-8
"""
本模块提供数据库模型字段遍历功能，以此为基础可以将实例转换为字典

"""

from __future__ import absolute_import

import six
from sqlalchemy.orm import object_mapper
from sqlalchemy.orm import RelationshipProperty


class DictBase(object):
    """扩展SQLAlchemy，使行对象可以转换为字典类型"""
    attributes = []
    detail_attributes = []
    summary_attributes = []

    def __iter__(self):
        """使其可以使用for . in形式访问"""
        for key, value in dict(object_mapper(self).columns).items():
            yield (key, value)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def update(self, values):
        """更新Model属性，模仿dict行为."""
        for k, v in six.iteritems(values):
            setattr(self, k, v)

    def all_columns_as_dict(self):
        columns = dict(object_mapper(self).columns)
        columns.update(dict(object_mapper(self).relationships))
        return columns

    def list_columns(self):
        """默认list级别的属性列表，自身作为主资源时的属性值，默认不带有relationship"""
        return self.attributes or [key for key, value in self]

    def get_columns(self):
        """默认get级别的详细属性列表，即自身作为主资源且尽量详细时的属性值，默认带有relationship"""
        return self.detail_attributes or self.all_columns_as_dict().keys()

    def sum_columns(self):
        """默认summary级别的属性列表，即被其他资源引用时能展示的属性值，默认不带有relationship"""
        return self.summary_attributes or [key for key, value in self]

    def list_relationship_columns(self):
        return [k for k, v in self.all_columns_as_dict().items() if isinstance(v, RelationshipProperty)]

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

    def to_detail_dict(self, prefix=None, flat_dict=False, child_as_summary=False):
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
                if child_as_summary:
                    value = value.to_summary_dict(flat_dict=flat_dict)
                else:
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
                            if child_as_summary:
                                values.append(v.to_summary_dict(flat_dict=flat_dict))
                            else:
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
