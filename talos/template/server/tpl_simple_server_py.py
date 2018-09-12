# coding=utf-8

TEMPLATE = u'''# coding=utf-8
"""
${pkg_name}.server.simple_server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

本模块提供开发测试用的简单服务启动能力

"""

from wsgiref.simple_server import make_server

from talos.core import config
from ${pkg_name}.server.wsgi_server import application


CONF = config.CONF


def main():
    """
    主函数，启动一个基于wsgiref的测试/开发用途的wsgi服务器

    绑定地址由配置文件提供， 监听端口由配置文件提供
    """
    bind_addr = CONF.server.bind
    port = CONF.server.port
    httpd = make_server(bind_addr, port, application)
    print("Serving on %s:%d..." % (bind_addr, port))
    httpd.serve_forever()


if __name__ == '__main__':
    main()
'''