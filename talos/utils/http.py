# coding=utf-8

from __future__ import absolute_import

import functools
import logging

import requests

from talos.core import exceptions


LOG = logging.getLogger(__name__)


def json_or_error(func):
    @functools.wraps(func)
    def _json_or_error(url, **kwargs):
        try:
            return func(url, **kwargs)
        except requests.ConnectionError as e:
            LOG.error('http error: %s %s, reason: %s', func.__name__.upper(), url, str(e))
            raise exceptions.CallBackError(
                message={'code': 502, 'title': 'Connection Error', 'description': 'Failed to establish a new connection'})
        except requests.Timeout as e:
            LOG.error('http error: %s %s, reason: %s', func.__name__.upper(), url, str(e))
            raise exceptions.CallBackError(
                message={'code': 504, 'title': 'Timeout Error', 'description': 'Server do not respond'})
        except requests.HTTPError as e:
            LOG.error('http error: %s %s, reason: %s', func.__name__.upper(), url, str(e))
            code = int(e.response.status_code)
            message = RestfulJson.get_response_json(e.response, default={'code': code})
            if code == 404:
                message['title'] = 'Not Found'
                message['description'] = 'The resource you request not exist'
            # 如果后台返回的数据不符合要求，强行修正
            if 'code' not in message:
                message['code'] = code
            raise exceptions.CallBackError(message=message)
        except Exception as e:
            LOG.error('http error: %s %s, reason: %s', func.__name__.upper(), url, str(e))
            message = {'code': 500, 'title': 'Server Error', 'description': str(e)}
            raise exceptions.CallBackError(message=message)
    return _json_or_error


def post(url, **kwargs):
    resp = requests.post(url, **kwargs)
    return resp


def get(url, **kwargs):
    resp = requests.get(url, **kwargs)
    return resp


def patch(url, **kwargs):
    resp = requests.patch(url, **kwargs)
    return resp


@staticmethod
def delete(url, **kwargs):
    resp = requests.delete(url, **kwargs)
    return resp


def put(url, **kwargs):
    resp = requests.put(url, **kwargs)
    return resp


class RestfulJson(object):
    @staticmethod
    def get_response_json(resp, default=None):
        try:
            return resp.json()
        except Exception as e:
            return default

    @staticmethod
    @json_or_error
    def post(url, **kwargs):
        resp = requests.post(url, **kwargs)
        resp.raise_for_status()
        return RestfulJson.get_response_json(resp)

    @staticmethod
    @json_or_error
    def get(url, **kwargs):
        resp = requests.get(url, **kwargs)
        resp.raise_for_status()
        return RestfulJson.get_response_json(resp)

    @staticmethod
    @json_or_error
    def patch(url, **kwargs):
        resp = requests.patch(url, **kwargs)
        resp.raise_for_status()
        return RestfulJson.get_response_json(resp)

    @staticmethod
    @json_or_error
    def delete(url, **kwargs):
        resp = requests.delete(url, **kwargs)
        resp.raise_for_status()
        return RestfulJson.get_response_json(resp)

    @staticmethod
    @json_or_error
    def put(url, **kwargs):
        resp = requests.put(url, **kwargs)
        resp.raise_for_status()
        return RestfulJson.get_response_json(resp)
