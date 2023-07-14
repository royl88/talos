# coding=utf-8
"""
本模块提供python3导入兼容

"""

from __future__ import absolute_import
import six

if six.PY2:
    from collections import Mapping
else:
    from collections.abc import Mapping

if six.PY2:
    from collections import Sequence
else:
    from collections.abc import Sequence