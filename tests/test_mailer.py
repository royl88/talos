# coding=utf-8

from __future__ import absolute_import

import logging
import pytest
from talos.common import mailer

LOG = logging.getLogger(__name__)


class TMockCookie(object):

    def __init__(self, cookie=None):
        self.cookie = cookie


def test_msg_probe():
    body = '''## type = html
## coding = utf-8
正式邮件内容'''
    assert mailer.msg_probe(body) == ('html', 'utf8')
    body = '''## coding = gbk
## type = html
正式邮件内容'''
    assert mailer.msg_probe(body) == ('html', 'gbk')


def test_msg_render():
    body = '''## type = html
## coding = gbk
正式邮件内容:${name}'''
    with pytest.raises(NameError, match='name'):
        mailer.render(body) == u'正式邮件内容:${name}'
    assert mailer.render(body, name='test') == u'正式邮件内容:test'


def test_to_address_list():
    assert mailer.to_address_list(['x@xx.com ',
                            'xx@xx.com , xxx@xx.com ',
                            ['xxxx@xx.com ', ' xxxxx@xx.com , xxxxxx@xx.com']]) == ['x@xx.com',
                                                                                 'xx@xx.com',
                                                                                 'xxx@xx.com',
                                                                                 'xxxx@xx.com',
                                                                                 'xxxxx@xx.com',
                                                                                 'xxxxxx@xx.com']
    assert mailer.to_address_list(['x@xx.com ',
                                   ['xx@xx.com ', ' xxx@xx.com , xxxx@xx.com']],
                                   recursive=False) == ['x@xx.com',
                                                       'xx@xx.com ',
                                                       ' xxx@xx.com , xxxx@xx.com']
    assert mailer.to_address_list('x@xx.com , xx@xx.com , xxx@xx.com',
                                   recursive=True) == ['x@xx.com',
                                                       'xx@xx.com',
                                                       'xxx@xx.com']
    assert mailer.to_address_list('x@xx.com , xx@xx.com , xxx@xx.com',
                                   recursive=False) == ['x@xx.com',
                                                       'xx@xx.com',
                                                       'xxx@xx.com']


def test_send_mail(mocker):
    mocker.patch('smtplib.SMTP')
    body = '''## type = html
## coding = utf-8
正式邮件内容'''
    m = mailer.Mailer('127.0.0.1', 'tset', '123')
    body_type, body_coding = mailer.msg_probe(body)
    assert m.mail_to('test_subject',
              body,
              'roy@test.com',
              ['roy@example1.com'],
              ['roy@example2.com'],
              ['roy@example3.com'],
              attachments=['./tests/unittest.conf', 
                           './tests/test_mail_attach_1.png', 
                           './tests/test_mail_attach_2.m4a'],
              message_type=body_type,
              message_charset=body_coding) is True

    assert m.mail_to('test_subject',
              body,
              'roy@test.com',
              ['roy@example1.com'] * 30,
              ['roy@example2.com'] * 30,
              ['roy@example3.com'] * 30,
              max_recevier=12,
              attachments=['./tests/unittest.conf',
                           './tests/test_mail_attach_1.png',
                           './tests/test_mail_attach_2.m4a'],
              message_type=body_type,
              message_charset=body_coding) is True
