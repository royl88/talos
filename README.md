talos project
=======================
项目是基于falcon封装，提供常用的项目工具，便于用户编写API服务</br>
项目提供了工具talos_generator，可以自动为您生成基于talos的api应用，并且目录结构基于python标准包管理

* 基于falcon
* 国际化i18n支持
* 使用简单功能全面的RESTfult CRUD API支持
* 使用SQLAlchemy作为数据库后端
* 支持gunicorn、uwsgi、httpd启动部署方式
* 便于调试
* 完善的测试
* 完整的文档

首先setup.py install 安装talos,运行talos生成工具生成项目

## talos_generator示例

```
> talos_generator
> 请输入项目生成目录：./
> 请输入项目名称(英)：storage
> 请输入生成类型[project,app,其他内容退出]：project
> 请输入项目版本：1.2.43432
> 请输入项目作者：Roy
> 请输入项目作者Email：roy@test.com
> 请输入项目启动配置目录：./etc
> 请输入项目DB连接串：postgresql+psycopg2://postgres:123456@127.0.0.1/testdb
### 创建项目目录：./storage
### 创建项目：storage(1.2.43432)通用文件
### 创建启动服务脚本
### 创建启动配置：./etc/storage.conf
### 创建中间件目录
### 完成
> 请输入生成类型[project,app,其他内容退出]：app
### 请输入app名称(英)：nas
### 创建app目录：./storage/storage/apps
### 创建app脚本：nas
### 完成
> 请输入生成类型[project,app,其他内容退出]：
```

</br>
