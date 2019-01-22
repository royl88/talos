# coding=utf-8
"""
本模块提供基础的控制器功能，包括列表资源、单个资源的API调用控制

"""

from __future__ import absolute_import

import copy
import fnmatch
import logging
import re

import falcon

from talos.core import config
from talos.core import exceptions
from talos.core import utils
from talos.core.i18n import _

LOG = logging.getLogger(__name__)
CONF = config.CONF


class SimplifyMixin(object):

    def _simplify_info(self, data, fields):
        info = {}
        for f in fields:
            info[f] = data.get(f)
        return info


class Controller(object):
    name = None
    resource = None
    list_size_limit = None
    allow_methods = tuple()

    def _validate_method(self, req):
        if req.method not in self.allow_methods:
            raise falcon.HTTPMethodNotAllowed(allowed_methods=self.allow_methods, code=405,
                                              title=_("Method Not Allowed"),
                                              description=_("method that you request not allowed"))

    def _validate_data(self, req):
        if not hasattr(req, 'json'):
            raise falcon.HTTPBadRequest(title=_("JSON Required"), description=_("body malformat, json required"))

    def _build_criteria(self, req, supported_filters=None):
        """
        构造过滤条件，包括filters，offset，limit

        :param req: 请求对象
        :type req: Request
        :param supported_filters: 支持参数过滤，若设置，则只允许特定字段的过滤,
                                   ['col']意味着所有的col，col__cond查询都支持，
                                   ['col__in']意味着col仅支持in查询
                                   ['col__*']意味着col支持所有带条件查询
        :type supported_filters: list
        :returns: {'filters': filters, 'offset': offset, 'limit': limit}
        :rtype: dict
        """

        def _glob_match(pattern_filters, name):
            if pattern_filters is None or name in pattern_filters:
                return True
            for pattern_filter in pattern_filters:
                if fnmatch.fnmatch(name, pattern_filter):
                    return True
            return False
        
        def _transform_comparator(mappings, comparator):
            if CONF.strict_criteria_transform:
                return mappings.get(comparator, None)
            else:
                if comparator in mappings:
                    return mappings[comparator]
                elif comparator in mappings.values():
                    return comparator
            return None

        query_dict = {}
        reg = re.compile('^(.+)\[(\d+)\]$')
        for key, value in req.params.items():
            matches = reg.match(key)
            if matches:
                match_key, match_index = matches.groups()
                if match_key in query_dict:
                    query_dict[match_key].append(value)
                else:
                    query_dict[match_key] = [value]
            else:
                query_dict[key] = value
        # 移除[]后缀,兼容js数组形态查询
        strip_query_dict = {}
        for key, value in query_dict.items():
            if key.endswith('[]'):
                strip_query_dict[key[:-2]] = value
            else:
                strip_query_dict[key] = value
        query_dict = strip_query_dict
        filter_mapping = {'contains': 'like', 'icontains': 'ilike',  # include
                          'istartswith': 'istarts', 'startswith': 'starts',  # starts with
                          'iendswith': 'iends', 'endswith': 'ends',  # ends with
                          'in': 'in', 'notin': 'nin',  # in options
                          'notequal': 'ne', 'equal': 'eq',  # =, !=
                          'less': 'lt', 'lessequal': 'lte', 'greater': 'gt', 'greaterequal': 'gte',  # <,<=,>,>=
                          # NOTE(wujj): new in v1.2.0
                          'excludes': 'nlike', 'iexcludes': 'nilike',  # exclude
                          'notnull': 'nnull', 'null': 'null',  # !=None, None
                          }
        filters = {}
        offset = None
        limit = None
        orders = None
        fields = None

        if query_dict is None:
            return filters, offset, limit
        if '__offset' in query_dict:
            offset = int(query_dict.pop('__offset'))
        if '__limit' in query_dict:
            limit = int(query_dict.pop('__limit'))
        if '__orders' in query_dict:
            orders = query_dict.pop('__orders')
            if utils.is_list_type(orders):
                orders = [order.strip() for order in orders]
            else:
                orders = [orders.strip()]
        if '__fields' in query_dict:
            fields = query_dict.pop('__fields')
            if utils.is_list_type(fields):
                fields = [f.strip() for f in fields]
            else:
                fields = [fields.strip()]
        for key in query_dict:
            # 没有指定支持filters 或者 明确支持的filter且完全匹配
            if supported_filters is None or key in supported_filters:
                keys = key.split('__', 1)
                # key 是简单条件
                if len(keys) == 1:
                    filters[key] = query_dict[key]
                # key 是复杂条件
                else:
                    base_key, comparator = keys[0], keys[1]
                    comparator = _transform_comparator(filter_mapping, comparator)
                    if comparator:
                        if base_key in filters and isinstance(filters[base_key], dict):
                            filters[base_key].update({comparator: query_dict[key]})
                        else:
                            filters[base_key] = {comparator: query_dict[key]}
            # 用户明确支持的filter 且 传入key不在此列表中，需要组合推测是否符合用户要求
            else:
                for valid_key in supported_filters:
                    # 非复杂查询条件，
                    if not key.startswith(valid_key + '__'):
                        continue
                    base_key, comparator = key.split('__', 1)
                    comparator = _transform_comparator(filter_mapping, comparator)
                    # 支持unix shell匹配条件
                    if comparator and _glob_match(supported_filters, base_key):
                        if base_key in filters and isinstance(filters[base_key], dict):
                            filters[base_key].update({comparator: query_dict[key]})
                        else:
                            filters[base_key] = {comparator: query_dict[key]}
        return {'filters': filters, 'offset': offset, 'limit': limit, 'orders': orders, 'fields': fields}

    def make_resource(self, req):
        return self.resource()


class CollectionController(Controller, SimplifyMixin):
    """集合控制器"""
    allow_methods = ('GET', 'POST',)

    def on_get(self, req, resp, **kwargs):
        """
        处理GET请求

        :param req: 请求对象
        :type req: Request
        :param resp: 相应对象
        :type resp: Response
        """
        self._validate_method(req)
        criteria = self._build_criteria(req)
        refs = self.list(req, copy.deepcopy(criteria), **kwargs)
        count = self.count(req, copy.deepcopy(criteria), results=refs, **kwargs)
        resp.json = {'count': count, 'data': refs}

    def count(self, req, criteria, results=None, **kwargs):
        """
        根据过滤条件，统计资源

        :param req: 请求对象
        :type req: Request
        :param criteria: {'filters': filters, 'offset': offset, 'limit': limit}
        :type criteria: dict
        :param results: criteria过滤出来的结果集
        :type results: list
        :returns: 符合条件的资源数量
        :rtype: int
        """
        criteria = copy.deepcopy(criteria)
        # remove offset,limit
        filters = criteria.pop('filters', None)
        return self.make_resource(req).count(filters)

    def list(self, req, criteria, **kwargs):
        """
        根据过滤条件，获取资源

        :param req: 请求对象
        :type req: Request
        :param criteria: {'filters': dict, 'offset': None/int, 'limit': None/int, 'fields': []}
        :type criteria: dict
        :returns: 符合条件的资源
        :rtype: list
        """
        criteria = copy.deepcopy(criteria)
        # 如果用户没有设置limit并且程序中自带了size limit则使用默认limit值
        # 若都没有设置，则检测全局配置是否启用并设置
        if criteria.get('limit', None) is None:
            if self.list_size_limit is not None:
                criteria['limit'] = self.list_size_limit
            elif CONF.global_list_size_limit_enabled and CONF.global_list_size_limit is not None:
                criteria['limit'] = CONF.global_list_size_limit
        fields = criteria.pop('fields', None)
        refs = self.make_resource(req).list(**criteria)
        if fields is not None:
            refs = [self._simplify_info(ref, fields) for ref in refs]
        return refs

    def on_post(self, req, resp, **kwargs):
        """
        处理POST请求

        :param req: 请求对象
        :type req: Request
        :param resp: 相应对象
        :type resp: Response
        """
        self._validate_method(req)
        self._validate_data(req)
        resp.json = self.create(req, req.json, **kwargs)
        resp.status = falcon.HTTP_201

    def create(self, req, data, **kwargs):
        """
        创建资源

        :param req: 请求对象
        :type req: Request
        :param data: 资源的内容
        :type data: dict
        :returns: 创建后的资源信息
        :rtype: dict
        """
        return self.make_resource(req).create(data)


class ItemController(Controller, SimplifyMixin):
    """单项资源控制器"""
    allow_methods = ('GET', 'PATCH', 'DELETE')

    def on_get(self, req, resp, **kwargs):
        """
        处理POST请求

        :param req: 请求对象
        :type req: Request
        :param resp: 相应对象
        :type resp: Response
        """
        self._validate_method(req)
        ref = self.get(req, **kwargs)
        if ref is not None:
            resp.json = ref
        else:
            raise exceptions.NotFoundError(resource=self.resource.__name__)

    def get(self, req, **kwargs):
        """
        获取资源详情

        :param req: 请求对象
        :type req: Request
        :returns: 资源详情信息
        :rtype: dict
        """
        return self.make_resource(req).get(**kwargs)

    def on_patch(self, req, resp, **kwargs):
        """
        处理PATCH请求

        :param req: 请求对象
        :type req: Request
        :param resp: 相应对象
        :type resp: Response
        """
        self._validate_method(req)
        self._validate_data(req)
        ref_before, ref_after = self.update(req, req.json, **kwargs)
        if ref_after is not None:
            resp.json = ref_after
        else:
            raise exceptions.NotFoundError(resource=self.resource.__name__)

    def update(self, req, data, **kwargs):
        """
        更新资源

        :param req: 请求对象
        :type req: Request
        :param data: 资源的内容
        :type data: dict
        :returns: 更新后的资源信息
        :rtype: dict
        """

        rid = kwargs.pop('rid')
        return self.make_resource(req).update(rid, data)

    def on_delete(self, req, resp, **kwargs):
        """
        处理DELETE请求

        :param req: 请求对象
        :type req: Request
        :param resp: 相应对象
        :type resp: Response
        """
        self._validate_method(req)
        ref, details = self.delete(req, **kwargs)
        if ref:
            resp.json = {'count': ref, 'data': details}
        else:
            raise exceptions.NotFoundError(resource=self.resource.__name__)

    def delete(self, req, **kwargs):
        """
        删除资源

        :param req: 请求对象
        :type req: Request
        :returns: 删除的资源数量
        :rtype: int
        """
        return self.make_resource(req).delete(**kwargs)
