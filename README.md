talos project
=======================
项目是主要基于falcon和SQLAlemchy封装，提供常用的项目工具，便于用户编写API服务</br>
项目提供了工具talos_generator，可以自动为您生成基于talos的api应用，并且目录结构基于python标准包管理

* 基于falcon
* 国际化i18n支持
* 使用简单功能全面的RESTfult CRUD API支持
* 使用SQLAlchemy作为数据库后端
* 支持gunicorn、uwsgi、httpd启动部署方式
* 便于调试
* 快速开发
* 异步celery封装集成

首先setup.py install 安装talos,运行talos生成工具生成项目

## 项目生成：talos_generator示例

```python
> talos_generator
> 请输入项目生成目录：./
> 请输入项目名称(英)：cms
> 请输入生成类型[project,app,其他内容退出]：project
> 请输入项目版本：1.2.43432
> 请输入项目作者：Roy
> 请输入项目作者Email：roy@test.com
> 请输入项目启动配置目录：./etc [此处填写默认配置路径，相对路径是相对项目文件夹，也可以是绝对路径]
> 请输入项目DB连接串：postgresql+psycopg2://postgres:123456@127.0.0.1/testdb [SQLAlemchy的DB连接串]
### 创建项目目录：./cms
### 创建项目：cms(1.2.43432)通用文件
### 创建启动服务脚本
### 创建启动配置：./etc/cms.conf
### 创建中间件目录
### 完成
> 请输入生成类型[project,app,其他内容退出]：app [需要生成APP才能编写实际业务代码]
### 请输入app名称(英)：user
### 创建app目录：./cms/cms/apps
### 创建app脚本：user
### 完成
> 请输入生成类型[project,app,其他内容退出]：
```
</br>
项目生成后，修改配置文件，比如./etc/cms.conf的application配置，列表中加入"cms.apps.user"即可启动服务器进行调试


## 启动开发调试服务器
启动项目目录下的server/simple_server.py即可进行调试

## 生产部署
  - 源码打包

```python
pip install wheel
python setup.py bdist_wheel
pip install PROJECTNAME-VERSION-py2.py3-none-any.whl
```

  - 启动服务：

```python
Linux部署一般配置文件都会放在/etc/PROJECTNAME/下，包括PROJECTNAME.conf和gunicorn.py文件
并确保安装gunicorn[pip install gunicorn]
步骤一，导出环境变量：export PROJECTNAME_CONF=/etc/PROJECTNAME/PROJECTNAME.conf
步骤二，gunicorn --pid "/var/run/PROJECTNAME.pid" --config "/etc/PROJECTNAME/gunicorn.py" "PROJECTNAME.server.wsgi_server:application"
```

## API开发步骤
  - 设计数据库
  - 导出数据库模型:sqlacodegen DB连接串 --outfile ~/models.py [sqlacodegen需要独立安装，pip install sqlacodegen] 
  - 将导出的文件表内容复制到PORJECTNAME.db.models.py中，并为每个表设置DictBase基类继承
  - 为数据库表类生成增删改查的资源类
  - 在app中使用资源类组装业务api控制类
  - 在app中使用编写Collection和Item Controller类
  - 在app中加入route
  - 确认配置文件中设置加载app
  - 启动调试或部署
 
待补充...