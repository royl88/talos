# coding=utf-8

import os
import os.path
import platform
import re
import shutil
import sys

from mako.template import Template
import six


if six.PY2:
    reload(sys)
    if platform.system() == 'Linux':
        sys.setdefaultencoding('UTF-8')
    else:
        sys.setdefaultencoding('GBK')
else:
    raw_input = input


def mkdir(dir_path):
    try:
        os.makedirs(dir_path)
    except:
        pass


PYTHON_CODING = '# coding=utf-8'
DEFAULT_VAR_RULE = r'^[a-zA-Z][_a-zA-Z0-9]*$'


def input_var_with_check(prompt, rule=None, max_try=3):
    rule = rule or DEFAULT_VAR_RULE
    content = raw_input(prompt)
    counter = 1
    while not re.match(rule, content):
        if counter > max_try:
            sys.exit(1)
        content = raw_input(prompt)
        max_try += 1
    return content


def render(source_code, output_file, **kwargs):
    with open(output_file, 'wb') as f_target:
        kwargs['sys_default_coding'] = '# coding=utf-8'
        content = Template(source_code, output_encoding='utf-8').render(**kwargs)
        f_target.write(content)


def get_template(name):
    mod_name = 'talos.template.' + name
    __import__(mod_name)
    mod = sys.modules[mod_name]
    return mod.TEMPLATE


def initialize_package(dest_path, pkg_name, author, author_email, version):
    src_dir = os.path.join(dest_path, pkg_name)
    mkdir(src_dir)
    render(get_template('tpl_init_py'),
           os.path.join(src_dir, '__init__.py'),
           author=author, coding=PYTHON_CODING)
    render(get_template('tpl_LICENSE'),
           os.path.join(dest_path, 'LICENSE'),
           author=author)
    render(get_template('tpl_MANIFEST_in'),
           os.path.join(dest_path, 'MANIFEST.in'))
    render(get_template('tpl_README_md'),
           os.path.join(dest_path, 'README.md'))
    render(get_template('tpl_requirements_txt'),
           os.path.join(dest_path, 'requirements.txt'))
    render(get_template('tpl_setup_cfg'),
           os.path.join(dest_path, 'setup.cfg'),
           pkg_name=pkg_name, author=author, author_email=author_email)
    render(get_template('tpl_setup_py'),
           os.path.join(dest_path, 'setup.py'),
           pkg_name=pkg_name, author=author, author_email=author_email, coding=PYTHON_CODING)
    render(get_template('tpl_tox_ini'),
           os.path.join(dest_path, 'tox.ini'))
    render(get_template('tpl_VERSION'),
           os.path.join(dest_path, 'VERSION'),
           version=version)


def initialize_server(dest_path, pkg_name, config_file, config_dir):
    config_file_fixed = config_file.replace('\\', '/')
    config_dir_fixed = config_dir.replace('\\', '/')
    server_dir = os.path.join(dest_path, pkg_name, 'server')
    mkdir(server_dir)
    render(get_template('server.tpl_init_py'),
           os.path.join(server_dir, '__init__.py'),
           coding=PYTHON_CODING)
    render(get_template('server.tpl_simple_server_py'),
           os.path.join(server_dir, 'simple_server.py'),
           pkg_name=pkg_name, coding=PYTHON_CODING)
    render(get_template('server.tpl_wsgi_server_py'),
           os.path.join(server_dir, 'wsgi_server.py'),
           pkg_name=pkg_name, config_file=config_file_fixed, config_dir=config_dir_fixed, coding=PYTHON_CODING)
    render(get_template('server.tpl_celery_worker_py'),
           os.path.join(server_dir, 'celery_worker.py'),
           pkg_name=pkg_name, config_file=config_file_fixed, config_dir=config_dir_fixed, coding=PYTHON_CODING)


def initialize_etc(dest_path, pkg_name, config_file, config_dir, db_connection):
    etc_dir = os.path.join(dest_path, 'etc')
    mkdir(etc_dir)
    locale_dir = os.path.join(dest_path, 'etc', 'locale', 'en', 'LC_MESSAGES')
    mkdir(locale_dir)

    render(get_template('etc.locale.en.LC_MESSAGES.tpl_project_po'),
           os.path.join(locale_dir, pkg_name + '.po'))
    render(get_template('etc.tpl_gunicorn_py'),
           os.path.join(etc_dir, 'gunicorn.py'),
           pkg_name=pkg_name, config_file=config_file, config_dir=config_dir, coding=PYTHON_CODING)
    render(get_template('etc.tpl_project_conf'),
           os.path.join(etc_dir, pkg_name + '.conf'),
           pkg_name=pkg_name, db_connection=db_connection)


def initialize_alembic(dest_path, pkg_name, db_connection):
    alembic_dir = os.path.join(dest_path, 'alembic')
    mkdir(alembic_dir)
    migration_dir = os.path.join(dest_path, 'alembic', 'migration')
    mkdir(migration_dir)

    render(get_template('alembic.tpl_alembic_ini'),
           os.path.join(alembic_dir, 'alembic.ini'),
           db_connection=db_connection)
    render(get_template('alembic.migration.tpl_env_py'),
           os.path.join(migration_dir, 'env.py'),
           pkg_name=pkg_name, coding=PYTHON_CODING)
    render(get_template('alembic.migration.tpl_README'),
           os.path.join(migration_dir, 'README'),
           pkg_name=pkg_name, coding=PYTHON_CODING)
    render(get_template('alembic.migration.tpl_script_py'),
           os.path.join(migration_dir, 'script.py.mako'),
           pkg_name=pkg_name, coding=PYTHON_CODING)


def initialize_middlewares(dest_path, pkg_name):
    middlewares_dir = os.path.join(dest_path, pkg_name, 'middlewares')
    mkdir(middlewares_dir)
    render(get_template('middlewares.tpl_init_py'),
           os.path.join(middlewares_dir, '__init__.py'),
           coding=PYTHON_CODING)


def initialize_database(dest_path, pkg_name):
    db_dir = os.path.join(dest_path, pkg_name, 'db')
    mkdir(db_dir)
    render(get_template('db.tpl_init_py'),
           os.path.join(db_dir, '__init__.py'),
           coding=PYTHON_CODING)
    render(get_template('db.tpl_models_py'),
           os.path.join(db_dir, 'models.py'),
           coding=PYTHON_CODING)


def initialize_app(dest_path, pkg_name, app_name):
    if not os.path.exists(os.path.join(dest_path, '__init__.py')):
        render(get_template('tpl_init_py'),
               os.path.join(dest_path, '__init__.py'),
               coding=PYTHON_CODING)
    app_dir = os.path.join(dest_path, app_name)
    mkdir(app_dir)
    render(get_template('apps.tpl_init_py'),
           os.path.join(app_dir, '__init__.py'),
           pkg_name=pkg_name, app_name=app_name, coding=PYTHON_CODING)
    render(get_template('apps.tpl_app_api_py'),
           os.path.join(app_dir, 'api.py'),
           pkg_name=pkg_name, app_name=app_name, coding=PYTHON_CODING)
    render(get_template('apps.tpl_app_controller_py'),
           os.path.join(app_dir, 'controller.py'),
           pkg_name=pkg_name, app_name=app_name, coding=PYTHON_CODING)
    render(get_template('apps.tpl_route_py'),
           os.path.join(app_dir, 'route.py'),
           pkg_name=pkg_name, app_name=app_name, coding=PYTHON_CODING)


def create_project(dest_path, name, version, author, author_email, config_dir, db_connection=''):
    dest_path = os.path.join(dest_path, name)
    mkdir(dest_path)
    print(u"### 创建项目目录：%s" % dest_path)
    config_file = os.path.join(config_dir, name + '.conf')
    config_dir = config_file + '.d'
    # 初始化python标准包文件
    initialize_package(dest_path, name, author, author_email, version)
    print(u"### 创建项目：%s(%s)通用文件 " % (name, version))
    # 初始化server目录
    initialize_server(dest_path, name, config_file, config_dir)
    print(u"### 创建启动服务脚本")
    # 初始化etc目录
    initialize_etc(dest_path, name, config_file, config_dir, db_connection)
    print(u"### 创建启动配置：%s" % config_file)
    # 初始化alembic目录
    # 初始化DB目录
    initialize_database(dest_path, name)
    print(u"### 创建数据库支持脚本")
    initialize_alembic(dest_path, name, db_connection)
    print(u"### 创建数据库迁移脚本")
    if not db_connection:
        print(u"### 数据库连接串无效, 如果需要数据库版本管理功能支持，您需要手动修改alembic/alembic.ini sqlalchemy.url值")
    # 初始化middlewares目录
    initialize_middlewares(dest_path, name)
    print(u"### 创建中间件目录")
    print(u"### 完成")


def create_app(dest_path, pkg_name, name):
    dest_path = os.path.join(dest_path, pkg_name, pkg_name, 'apps')
    mkdir(dest_path)
    print(u"### 创建app目录：%s" % dest_path)
    # 初始化app目录
    initialize_app(dest_path, pkg_name, name)
    print(u"### 创建app脚本：%s" % name)
    print(u"### 完成")


def generate():
    dest_path = input_var_with_check(u'请输入项目生成目录：', rule='.*')
    pkg_name = input_var_with_check(u'请输入项目名称(英)：')
    while True:
        gen_type = raw_input(u'请输入生成类型[project,app,其他内容退出]：')
        if gen_type.lower() == 'project':
            version = input_var_with_check(u'请输入项目版本：', rule='.*')
            author = input_var_with_check(u'请输入项目作者：', rule='.*')
            author_email = input_var_with_check(u'请输入项目作者Email：', rule='.*')
            config_path = input_var_with_check(u'请输入项目启动配置目录：', rule='.*')
            db_conn = input_var_with_check(u'请输入项目DB连接串：', rule='.*')
            create_project(dest_path, pkg_name, version, author, author_email, config_path, db_conn)
        elif gen_type.lower() == 'app':
            app_name = input_var_with_check(u'请输入app名称(英)：')
            create_app(dest_path, pkg_name, app_name)
        else:
            sys.exit(0)
