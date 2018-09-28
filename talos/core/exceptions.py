# coding=utf-8
"""
本模块提供异常信息封装

"""

from __future__ import absolute_import

from talos.core.i18n import _


class Error(Exception):
    """异常基类"""
    code = 500

    def __init__(self, message=None, **kwargs):
        if message:
            self.message = message
        else:
            self._build_message(**kwargs)
        super(Error, self).__init__(self.message)

    def _build_message(self, **kwargs):
        self.message = self.message_format % kwargs

    def __str__(self):
        return self.message

    @property
    def message_format(self):
        return _('Unknown Error')

    @property
    def title(self):
        return None


class CallBackError(Error):
    """接收并转换Restful错误异常"""

    def __init__(self, message):
        self._message = message
        if isinstance(message, dict):
            self.message = message.get('description', 'Unknown')
            self.code = message.get('code', 500)
        Exception.__init__(self, message)

    @property
    def title(self):
        if isinstance(self._message, dict):
            return self._message.get('title', 'Unknown')
        else:
            return self._message

    def __str__(self):
        if isinstance(self._message, dict):
            return self._message.get('description', 'Unknown')
        else:
            return self._message


class CriticalError(Error):
    """重大错误异常"""
    code = 500

    @property
    def title(self):
        return _('Server Error')

    @property
    def message_format(self):
        return _('detail: %(msg)s')


class DBError(Error):
    """DB错误异常"""
    code = 400

    @property
    def title(self):
        return _('DB Error')

    @property
    def message_format(self):
        return _('detail: %(msg)s')


class BodyParseError(Error):
    """解析错误异常"""
    code = 400

    @property
    def title(self):
        return _('HTTP Body Error')

    @property
    def message_format(self):
        return _('detail: body parse error: %(msg)s')


class ValidationError(Error):
    """验证错误异常"""
    code = 400

    @property
    def title(self):
        return _('Validation Error')

    @property
    def message_format(self):
        return _('detail: column %(attribute)s validate failed, because: %(msg)s')


class NotEnoughError(Error):
    """资源不足异常"""
    code = 400

    @property
    def title(self):
        return _('Resource NotEnough')

    @property
    def message_format(self):
        return _('detail: %(resource)s not enough')


class FieldRequired(ValidationError):
    """验证错误，字段缺失异常"""
    code = 400

    @property
    def title(self):
        return _('Field Missing')

    @property
    def message_format(self):
        return _('column: %(attribute)s must be specific')


class LoginError(Error):
    """认证错误异常"""
    code = 401

    @property
    def title(self):
        return _('Unauthorized')

    @property
    def message_format(self):
        return _('detail: ops, username or password error, login deny')


class AuthError(Error):
    """认证错误异常"""
    code = 401

    @property
    def title(self):
        return _('Unauthorized')

    @property
    def message_format(self):
        return _('detail: you are unauthenticated, login needed')


class ForbiddenError(Error):
    """认证错误异常"""
    code = 403

    @property
    def title(self):
        return _('Forbidden')

    @property
    def message_format(self):
        return _('detail: you are not allow to perfrom this action')


class NotFoundError(Error):
    """资源不存在异常"""
    code = 404

    @property
    def title(self):
        return _('Not Found')

    @property
    def message_format(self):
        return _('detail: the resource(%(resource)s) you request not found')


class MethodForbiddenError(Error):
    """HTTP方法不允许访问"""
    code = 405

    @property
    def title(self):
        return _('Method Not Allowed')

    @property
    def message_format(self):
        return _('detail: method you request is not allow to perfrom')


class ConflictError(Error):
    """约束冲突错误异常"""
    code = 409

    @property
    def title(self):
        return _('Conflict')

    @property
    def message_format(self):
        return _('detail: %(msg)s')