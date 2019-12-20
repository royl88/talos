# coding=utf-8
"""
talos.core.xmlutils
~~~~~~~~~~~~~~~~~~~

本模块提供dict/list的python通用数据 对 xml序列化支持

test = {'a': 1, 'b': 1.2340932, 'c': True, 'd': None, 'e': 'hello <world />', 'f': {
    'k': 'v', 'm': 'n'}, 'g': [1, '2', False, None, {'k': 'v', 'm': [1, 2, 3]}],
    'h': et.Element('root')}
start = time.time()
print toxml(test, attr_type=True,
                hooks={'etree': {'render': lambda x: x.tag, 'hit': lambda x: isinstance(x, et.Element)}})
end = time.time()
print 'cost:', end - start

> cost: 0.0019998550415

"""
import collections
import datetime
import decimal
from xml.etree import ElementTree as et


# python 3 doesn't have a unicode type
try:
    unicode
except:
    unicode = str

# python 3 doesn't have a long type
try:
    long
except:
    long = int


def get_typename(v):
    return type(v).__name__


def default_render(v):
    return str(v)


def is_dict(v):
    return isinstance(v, dict)


def is_list(v):
    return isinstance(v, (list, tuple, set))


def default_type_hooks():
    def _bool_render(v):
        return str(v)

    def _string_render(v):
        return v

    def _int_render(v):
        return str(v)

    def _float_render(v):
        return str(v)

    def _decimal_render(v):
        return str(float(v))

    def _none_render(v):
        return ''

    def _datetime_render(v):
        return v.isoformat(' ')

    def _date_render(v):
        return v.isoformat()

    hooks = collections.OrderedDict()
    # bool必须为第一位，否则会被int覆盖
    hooks['bool'] = {'render': _bool_render, 'hit': lambda v: isinstance(v, bool)}
    hooks['str'] = {'render': _string_render, 'hit': lambda v: isinstance(v, (str, unicode))}
    # int,float不使用isinstance(v, numbers.Number), 判断顺序会导致不可知问题
    hooks['int'] = {'render': _int_render, 'hit': lambda v: isinstance(v, (int, long))}
    hooks['float'] = {'render': _float_render, 'hit': lambda v: isinstance(v, float)}
    hooks['decimal'] = {'render': _decimal_render, 'hit': lambda v: isinstance(v, decimal.Decimal)}
    hooks['null'] = {'render': _none_render, 'hit': lambda v: v is None}
    hooks['datetime'] = {'render': _datetime_render, 'hit': lambda v: isinstance(v, datetime.datetime)}
    hooks['date'] = {'render': _date_render, 'hit': lambda v: isinstance(v, datetime.date)}

    return hooks


def toxml(obj, root_tag='root', attr_type=True, hooks=None, list_item_tag='item'):
    """
    将python的dict/list数据转换为xml，内置多种常用数据序列化输出，其他格式默认按照str(v)方式渲染
    另外提供了hooks能力，可自定义类型的处理方式

    :param obj: 需要格式化为xml的数据，可以是dict或list，obj数据中可以嵌套其他各种类型的数据
    :type obj: list/dict
    :param root_tag: xml根节点的名称，默认为root
    :type root_tag: str
    :param attr_type: 是否以属性标识出原始数据类型，默认True
    :type attr_type: bool
    :param hooks: 类型转换钩子，数据格式示例如下：{'etree': {'render': func(v), 'hit': type_func(v)}}

                   render: 数据转换函数，输出必须是字符串

                   hit： 数据的类型判定函数,输出为bool值，若hit判断返回为True，则使用render进行此类渲染

                   默认数据类型及转换方式/顺序对应如下：

                   - hit          render
                   - bool         str
                   - str,unicode  raw
                   - int,long     str
                   - float        str
                   - Decimal      str
                   - None         empty
                   - datetime     isoformat
                   - date         isoformat
                   - other        str
    :type hooks: dict
    :param list_item_tag: 列表默认xml标签名称，默认为item
    :type list_item_tag: str
    """

    type_hooks = default_type_hooks()
    type_hooks.update(hooks or {})
    type_judements = []
    for typename, data in type_hooks.items():
        type_judements.append((data['hit'], typename))

    def _get_render(v):
        for jude, typename in type_judements:
            if jude(v) is True:
                return type_hooks.get(typename)['render'], typename
        return default_render, get_typename(v)

    def _dict_to_etree(element, obj, attr_type):
        if attr_type:
            element.attrib['type'] = 'dict'
        for k, v in obj.items():
            sub_element = et.SubElement(element, default_render(k))
            if is_dict(v):
                _dict_to_etree(sub_element, v, attr_type)
            elif is_list(v):
                _list_to_etree(sub_element, v, attr_type)
            else:
                _normal_to_etree(sub_element, v, attr_type)

    def _list_to_etree(element, obj, attr_type):
        if attr_type:
            element.attrib['type'] = 'list'
        for v in obj:
            sub_element = et.SubElement(element, list_item_tag)
            if is_dict(v):
                _dict_to_etree(sub_element, v, attr_type)
            elif is_list(v):
                _list_to_etree(sub_element, v, attr_type)
            else:
                _normal_to_etree(sub_element, v, attr_type)

    def _normal_to_etree(element, obj, attr_type):
        render, typename = _get_render(obj)
        element.text = render(obj)
        if attr_type:
            element.attrib['type'] = typename

    root = et.Element(root_tag)
    if is_dict(obj):
        _dict_to_etree(root, obj, attr_type)
    elif is_list(obj):
        _list_to_etree(root, obj, attr_type)
    else:
        _normal_to_etree(root, obj, attr_type)
    return u'<?xml version="1.0" encoding="UTF-8" ?>'.encode('utf-8') + et.tostring(root, 'utf-8')
