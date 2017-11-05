# coding=utf-8
"""
本模块提供SMTP邮件发送功能

"""

from __future__ import absolute_import

from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import re
import smtplib

from mako.template import Template

from talos.core import utils


LOG = logging.getLogger(__name__)
COMMASPACE = ', '
SEMICOLONSPACE = '; '


def msg_probe(body):
    """
    检测body类型

    :param body: 内容模板
        | ## type = text/plain/html, 默认plain
        | ## coding = gbk/gb2312/utf-8/utf8, 默认utf8
        | 正式邮件内容
    :type body: str
    :returns: (type, coding)元组
    :rtype: tuple
    """
    default_type = 'plain'
    default_charset = 'gbk'
    mime_type = {'text': 'plain', 'plain': 'plain', 'html': 'html'}
    mime_charset = {'gbk': 'gbk', 'gb2312': 'gbk', 'utf-8': 'utf8', 'utf8': 'utf8'}
    rule = r'^\s*##\s*(type|coding)[ ]*=[ ]*([^\s]+)(\s*##\s*(type|coding)[ ]*=[ ]*([^\s]+))?'
    match = re.search(rule, body)
    if match:
        match_key, match_value = match.group(1, 2)
        if match_key and 'type' == match_key.lower():
            default_type = match_value
        elif match_key and 'coding' == match_key.lower():
            default_charset = match_value
        match_key, match_value = match.group(4, 5)
        if match_key and 'type' == match_key.lower():
            default_type = match_value
        elif match_key and 'coding' == match_key.lower():
            default_charset = match_value
    return (mime_type.get(default_type.lower(), 'plain'), mime_charset.get(default_charset.lower(), 'utf8'))


def render(text, **kwargs):
    """
    渲染邮件模板

    :param text: 邮件模板内容
    :type text: str
    :returns: 邮件内容
    :rtype: str
    """
    templ = Template(text)
    return templ.render(**kwargs)


def to_address_string(iterable):
    """
    多个邮件地址需要拼接为RFC标准文本，本函数提供邮件地址拼接函数

    :param iterable: 邮件地址列表
    :type iterable: list
    :returns: 拼接后的邮件地址
    :rtype: str
    """
    return COMMASPACE.join(iterable)


def to_address_list(address, recursive=True):
    """
    将邮件地址字符串标准化为列表

    :param address: 邮件地址
        支持['xx@xx.com','xx@xx.com','xx@xx.com']
        或'xx@xx.com, xx@xx.com,xx@xx.com, xx@xx.com'
        或['xx@xx.com','xx@xx.com, xx@xx.com,xx@xx.com, xx@xx.com']形式
    :type address: str/list
    :param recursive: 是否递归转换
    :type recursive: bool
    :returns: 邮件地址列表
    :rtype: list
    """
    addrs = []
    inner_addrs = []
    if utils.is_string_type(address):
        if COMMASPACE.strip() in address:
            addrs = address.split(COMMASPACE.strip())
        else:
            addrs = address.split(SEMICOLONSPACE.strip())
    else:
        addrs = address
        for n in range(len(addrs)):
            if recursive:
                inner_addrs.extend(to_address_list(addrs[n].strip(), recursive=False))
                addrs[n] = None
    addrs = [ad.strip() for ad in addrs if ad]
    addrs.extend(inner_addrs)
    return addrs


class Mailer(object):
    """邮件操作类"""

    def __init__(self, host=None, username=None, password=None):
        """
        初始化Mailer对象

        :param host: SMTP服务host信息，host格式可以是host 或 host:port
        :type host: str
        :param username: SMTP服务认证用户
        :type username: str
        :param password: SMTP服务用户密码
        :type password: str
        """
        self.host = host
        self.username = username
        self.password = password

    def mail_to(self,
                mail_from,
                mail_to,
                mail_cc,
                subject,
                message,
                mail_bcc=None,
                attchments=None,
                message_type='plain',
                message_charset='utf8',
                max_recevier=None):
        """

        :param mail_from: 发件人邮件地址
        :type mail_from: str
        :param mail_to: 收件人，地址字符串为元素的列表
        :type mail_to: list
        :param mail_cc: 抄送人，地址字符串为元素的列表 or None
        :type mail_cc: list
        :param subject: 邮件主题
        :type subject: str
        :param message: 邮件内容
        :type message: str
        :param mail_bcc: 秘密抄送，地址字符串为元素的列表 or None
        :type mail_bcc: list
        :param attchments: 附件列表
        :type attchments: str/list
        :param message_type: 邮件内容格式，如text，html
        :type message_type: str
        :param message_charset: 邮件内容编码，如utf8，gbk
        :type message_charset: str
        :param max_recevier: 每次最大发送人数量，如果设置，会进行分批发送
        :type max_recevier: int
        :returns: 是否发送成功
        :rtype: bool
        """
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = mail_from
        fix_mail_to = []
        msg['To'] = to_address_string(mail_to)
        fix_mail_to.extend(mail_to)
        if mail_cc:
            msg['Cc'] = to_address_string(mail_cc)
            fix_mail_to.extend(mail_cc)
        if mail_bcc:
            msg['Bcc'] = to_address_string(mail_bcc)
            fix_mail_to.extend(mail_bcc)
        message = utils.ensure_unicode(message)
        body = MIMEText(message, _subtype=message_type, _charset=message_charset)
        msg.attach(body)
        attchments = attchments or []
        if utils.is_string_type(attchments):
            attchments = [attchments]
        for filename in attchments:
            with open(filename, 'rb') as f:
                if filename.endswith('.jpg') or filename.endswith('.png') or filename.endswith('.gif')\
                   or filename.endswith('.jpeg'):
                    attchment = MIMEImage(f.read())
                    attchment['Content-ID'] = os.path.basename(filename).split('.')[0]
                    msg.attach(attchment)
                else:
                    attchment = MIMEText(f.read(), 'base64', message_charset)
                    attchment['Content-Type'] = 'application/octet-stream'
                    attchment['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(filename)
                    msg.attach(attchment)
        try:
            smtp = smtplib.SMTP()
            smtp.connect(self.host)
            if self.username is not None and self.password is not None:
                smtp.login(self.username, self.password)
            LOG.info('email as string: %s', msg.as_string())
            if max_recevier and len(fix_mail_to) > max_recevier:
                ranger = range(len(fix_mail_to))[::max_recevier]
                for n in range(len(ranger) - 1):
                    LOG.info('sending email to : %s', fix_mail_to[ranger[n]:ranger[n + 1]])
                    result = smtp.sendmail(mail_from, fix_mail_to[ranger[n]:ranger[n + 1]], msg.as_string())
                    if len(result) > 0:
                        LOG.error('failed to mail recipient: %s', result)
                if len(fix_mail_to) % max_recevier != 0:
                    # recipient left
                    LOG.info('sending email to : %s', fix_mail_to[ranger[-1]:])
                    result = smtp.sendmail(mail_from, fix_mail_to[ranger[-1]:], msg.as_string())
                    if len(result) > 0:
                        LOG.error('failed to email recipient: %s', result)
            else:
                result = smtp.sendmail(mail_from, fix_mail_to, msg.as_string())
                if len(result) > 0:
                    LOG.error('failed to email recipient: %s', result)
            smtp.quit()
            return True
        except smtplib.SMTPException as e:
            LOG.error('email exception raised: %s', str(e))
            return False
