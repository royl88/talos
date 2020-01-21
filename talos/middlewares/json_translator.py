# coding=utf-8
"""
本模块提供json转换中间件

"""
from __future__ import absolute_import

import json
import logging

from talos.core import exceptions
from talos.core import utils
from talos.core.i18n import _

LOG = logging.getLogger(__name__)


class JSONTranslator(object):
    """中间件，将输入数据转换为json，以及将输出数据转换为json"""

    def process_request(self, req, resp):
        """在业务逻辑之前，对每个请求提交的数据格式化为json"""
        # req.stream corresponds to the WSGI wsgi.input environ variable,
        # and allows you to read bytes from the request body.
        #
        # See also: PEP 3333
        # process when json & content_length is set
        if not (req.content_length and 'application/json' in (req.content_type or '')):
            # Nothing to do
            return

        # 修复falcon重复读取导致无法解析json问题，因此不再使用media
        body = req.stream.read(req.content_length or 0)
        if not body:
            raise exceptions.BodyParseError(msg=_('empty request body, a valid json document is required.'))
        try:
            body = body.decode('utf-8')
            LOG.debug("request body: %s", body)
            req.json = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise exceptions.BodyParseError(
                msg=_('malformed json, body was incorrect or not encoded as UTF-8.'))

    def process_response(self, req, resp, resource, *args, **kwargs):
        """在业务逻辑之后，对每个请求返回数据格式化为json"""
        if not hasattr(resp, 'json'):
            return
        resp.content_type = 'application/json'
        resp.body = json.dumps(resp.json, cls=utils.ComplexEncoder)
