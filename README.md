talos project
=======================

[TOC]



## 特性

https://gitee.com/wu.jianjun/talos/tree/master/release

项目是主要基于falcon和SQLAlemchy封装，提供常用的项目工具，便于用户编写API服务
项目提供了工具talos_generator，可以自动为您生成基于talos的api应用，并且目录结构基于python标准包管理

* 基于falcon，高效
* 使用SQLAlchemy作为数据库后端，快速切换数据库
* 项目生成工具
* 迅捷的开发
* 简洁而全面的RESTfult CRUD API支持
* 便于调试
* 异步celery封装集成
* 频率限制
* 国际化i18n支持
* SMTP邮件、AD域、CSV导出、缓存等常用模块集成
* 通用的wsgi启动部署方式

首先setup.py install 安装talos,运行talos生成工具生成项目



## 项目生成

安装talos后，会生成talos_generator工具，此工具可以为用户快速生成业务代码框架

```bash
> talos_generator
> 请输入项目生成目录：./
> 请输入项目名称(英)：cms
> 请输入生成类型[project,app,其他内容退出]：project
> 请输入项目版本：1.2.4
> 请输入项目作者：Roy
> 请输入项目作者Email：roy@test.com
> 请输入项目启动配置目录：./etc #此处填写默认配置路径，相对路径是相对项目文件夹，也可以是绝对路径
> 请输入项目DB连接串：postgresql+psycopg2://postgres:123456@127.0.0.1/testdb [SQLAlemchy的DB连接串]
### 创建项目目录：./cms
### 创建项目：cms(1.2.4)通用文件
### 创建启动服务脚本
### 创建启动配置：./etc/cms.conf
### 创建中间件目录
### 完成
> 请输入生成类型[project,app,其他内容退出]：app # 生成的APP用于编写实际业务代码，或手动编写
### 请输入app名称(英)：user
### 创建app目录：./cms/cms/apps
### 创建app脚本：user
### 完成
> 请输入生成类型[project,app,其他内容退出]：
```

项目生成后，修改配置文件，比如**./etc/cms.conf的application.names配置，列表中加入"cms.apps.user"即可启动服务器进行调试**




## 开发调试
启动项目目录下的server/simple_server.py即可进行调试



## 生产部署
  - 源码打包

```bash
pip install wheel
python setup.py bdist_wheel
pip install cms-1.2.4-py2.py3-none-any.whl
```

  - 启动服务：

```bash
# Linux部署一般配置文件都会放在/etc/cms/下，包括cms.conf和gunicorn.py文件
# 并确保安装gunicorn
pip install gunicorn
# 步骤一，导出环境变量：
export cms_CONF=/etc/cms/cms.conf
# 步骤二，
gunicorn --pid "/var/run/cms.pid" --config "/etc/cms/gunicorn.py" "cms.server.wsgi_server:application"
```



## API开发引导

### 基础开发步骤

  1. ##### 设计数据库

     略

  2. ##### 导出数据库模型

     项目中使用的是SQLAlchemy，使用表操作需要将数据库导出为python对象定义，这样做的好处是

     1. 确定表结构，形成应用代码与数据库之间的版本对应
     2. 便于编程中表达数据库操作，而并非使用字符串

     ```bash
     pip install sqlacodegen
     sqlacodegen postgresql+psycopg2://postgres:123456@127.0.0.1/testdb --outfile models.py
     ```

     生成的models.py内容大致如下：

     ```python
     # coding=utf-8
     
     from __future__ import absolute_import
     
     from sqlalchemy import String
     from sqlalchemy.ext.declarative import declarative_base
     
     Base = declarative_base()
     metadata = Base.metadata
     
     class User(Base):
         __tablename__ = 'user'
     
         id = Column(String(36), primary_key=True)
         name = Column(String(63), nullable=False)
     ```

     当然这个导出操作如果在足够熟悉的情况下可以手动编写，不需要导出工具

  3. ##### 数据库模型类的魔法类

     将导出的文件表内容复制到cms.db.models.py中，并为每个表设置DictBase基类继承

     models.py文件中，每个表对应着一个class，这使得我们在开发业务处理代码时能明确表对应的处理，但在接口返回中，我们通常需要转换为json，因而，我们需要为models.py中的每个表的类增加一个继承关系，以便为它提供转换的支持

     处理完后的models.py文件如下：

     ```python
     # coding=utf-8
     
     from __future__ import absolute_import
     
     from sqlalchemy import String
     from sqlalchemy.ext.declarative import declarative_base
     from talos.db.dictbase import DictBase
     
     Base = declarative_base()
     metadata = Base.metadata
     
     class User(Base, DictBase):
         __tablename__ = 'user'
     
         id = Column(String(36), primary_key=True)
         name = Column(String(63), nullable=False)
     
     class UserPhoneNum(Base, DictBase):
         __tablename__ = 'user_phone'
     
         user_id = Column(String(63), nullable=False, primary_key=True)
         phone = Column(String(63), nullable=False, primary_key=True)
         description = Column(String(255), nullable=True)
     ```

     继承了这个类之后，不仅提供了转换接口json的能力，还提供了字段提取的能力，此项稍后再说明，此处不定义，则意味着默认使用表的所有字段

  4. ##### 增删改查的资源类

     在cms.db中新增resource.py文件，内容如下：

     ```python
     # coding=utf-8
     
     from __future__ import absolute_import
     
     from talos.db.crud import ResourceBase
     
     from cms.db import models
     
     
     class User(ResourceBase):
         orm_meta = models.User
         _primary_keys = 'id'
     
     
     class UserPhoneNum(ResourceBase):
         orm_meta = models.UserPhoneNum
         _primary_keys = ('user_id', 'phone')
     ```

     完成此项定义后，我们可以使用resource.User来进行用户表的增删改查，而这些功能都是ResourceBase默认提供的能力

     可以看到我们此处定义了orm_meta和_primary_keys两个类属性，除此以外还有更多类属性可以帮助我们快速配置应用逻辑

     | 类属性          | 默认值 | 描述                                                         |
     | --------------- | ------ | ------------------------------------------------------------ |
     | orm_meta        | None   | 资源操作的SQLAlchmey Model类[表]                             |
     | _primary_keys   | 'id'   | 表对应的主键列，单个主键时，使用字符串，多个联合主键时为字符串列表，这个是业务主键，意味着你可以定义和数据库主键不一样的字段（前提是你要确定这些字段是有唯一性的） |
     | _default_filter | {}     | 默认过滤查询，常用于软删除，比如数据删除我们在数据库字段中标记为is_deleted=True，那么我们再次list，get，update，delete的时候需要默认过滤这些数据的，等价于默认带有where is_delete = True |
     | _default_order  | []     | 默认排序，查询资源时被应用，('name', '+id', '-status'), +表示递增，-表示递减，默认递增 |
     | _validate       | []     | 数据输入校验规则，为talos.db.crud.ColumnValidator对象列表    |
     一个_validate示例如下：

     ```python
        ColumnValidator(field='id',
                        validate_on=['create:M']),
        ColumnValidator(field='name',
                        rule='1, 63',
                        rule_type='length',
                        validate_on=['create:M', 'update:O']),
        ColumnValidator(field='enabled',
                        rule=validator.InValidator(['true', 'false', 'True', 'False'])
                        converter=converter.BooleanConverter(),
                        validate_on=['create:M', 'update:O']),
     ```

     ColumnValidator可以定义的属性如下：

     | 属性         | 类型                                           | 描述                                                         |
     | ------------ | ---------------------------------------------- | ------------------------------------------------------------ |
     | field        | 字符串                                         | 字段名称                                                     |
     | rule         | validator对象 或 校验类型rule_type所需要的参数 | 当rule是validator类型对象时，忽略 rule_type参数              |
     | rule_type    | 字符串                                         | 用于快速定义校验规则，默认regex，可选类型有callback，regex，email，phone，url，length，in，notin，integer，float，type |
     | validate_on  | 数组                                           | 校验场景和必要性, eg. ['create: M', 'update:O']，表示此字段在create函数中为必要字段，update函数中为可选字段 |
     | error_msg    | 字符串                                         | 错误提示信息，默认为'%(result)s'，即validator返回的报错信息，用户可以固定字符串或使用带有%(result)s的模板字符串 |
     | converter    | converter对象                                  | 数据转换器，当数据被校验后，可能需要转换为固定类型后才能进行编程处理，转换器可以为此提供自动转换，比如用户输入为'2018-01-01 01:01:01'字符串时间，程序需要为Datetime类型，则可以使用DateTimeConverter进行转换 |
     | orm_required | 布尔值                                         | 控制此字段是否会被传递到数据库SQL中去                        |
     | aliases      | 数组                                           | 字段的别名                                                   |
     | nullable     | 布尔值                                         | 控制此字段是否可以为None                                     |

     CRUD使用方式:

     ```python
     resource.User().create({'id': '1', 'name': 'test'})
     resource.User().list()
     resource.User().list({'name': 'test'})
     resource.User().list({'name': {'ilike': 'na'}}, offset=0, limit=5)
     resource.User().count()
     resource.User().count({'name': 'test'})
     resource.User().count({'name': {'ilike': 'na'}})
     resource.User().get('1')
     resource.User().update('1', {'name': 'test1'})
     resource.User().delete('1')
     resource.UserPhoneNum().get(('1', '10086'))
     resource.UserPhoneNum().delete(('1', '10086'))
     ```

  5. ##### 业务api控制类

     api的模块为：cms.apps.user.api

     resource处理的是DB的CRUD操作，但往往业务类代码需要有复杂的处理逻辑，并且涉及多个resource类的相互操作，因此需要封装api层来处理此类逻辑，此处我们示例没有复杂逻辑，直接沿用定义即可

     ```python
     User = resource.User
     UserPhoneNum = resource.UserPhoneNum
     ```

  6. ##### Collection和Item Controller

     Controller模块为：cms.apps.user.controller

     Controller被设计分类为Collection和Item 2种，分别对应RESTFul的URL操作，我们先看一个常见的URL设计和操作

     ```bash
     POST   /v1/users    创建用户
     GET    /v1/users    查询用户列表
     PATCH  /v1/users/1  更新用户1的信息
     DELETE /v1/users/1  删除用户1的信息
     GET    /v1/users/1  获取用户1的详情
     ```

     根据当前的URL规律我们可以吧创建和查询列表作为一个封装（CollectionController），而更新，删除，获取详情作为一个封装（ItemController），而同样的，对于这样的标准操作，talos同样提供了魔法般的定义

     ```python
     class CollectionUser(CollectionController):
         name = 'cms.users'
         resource = api.User
     
     
     class ItemUser(ItemController):
         name = 'cms.user'
         resource = api.User
     ```

  7. ##### route路由映射

     route模块为：cms.apps.user.route

     提供了Controller后，我们还需要将其与URL路由进行映射才能调用，route模块中，必须有add_routes函数，注册app的时候会默认寻找这个函数来注册路由

     ```python
     def add_routes(api):
         api.add_route('/v1/users', controller.CollectionUser())
         api.add_route('/v1/users/{rid}', controller.ItemUser())
     ```

  8. ##### 配置启动加载app

     我们在引导开始时创建的项目配置文件存放在./etc中，所以我们的配置文件在./etc/cms.conf，修改

     ```javascript
     ...
     "application": {
             "names": [
                 "cms.apps.user"]
     },
     ...
     ```

  9. ##### 启动调试或部署

     在源码目录中有server包，其中simple_server是用于开发调试用，不建议在生产中使用

     python simple_server.py

10. ##### 测试API

    启动后我们的服务已经可以对外输出啦！

    那么我们的API到底提供了什么样的能力呢？我们以user作为示例展示

    创建

    ```
    POST /v1/users
    Content-Type: application/json;charset=UTF-8
    Host: 127.0.0.1:9002
    
    {
        "id": "1",
        "name": "test"
    }
    ```

    查询列表

    ```
    GET /v1/users
    Host: 127.0.0.1:9002
    
    {
        "count": 1,
        "data": [
            {
                "id": "1",
                "name": "test"
            }
        ]
    }
    ```

    关于查询列表，我们提供了强大的查询能力，可以满足大部分的查询场景

    获取列表(查询)的接口可以使用Query参数过滤，使用过滤字段=xxx 或 字段__查询条件=xxx方式传递

    1. - 过滤条件

         eg.

         ```bash
         # 查询name字段等于abc
         name=abc
         # 查询name字段包含abc
         name__icontains=abc
         # 查询name字段在列表[a, b, c]值内
         name=a&name=b&name=c 
         # 或 
         name__in=a&name__in=b&name__in=c
         # 查询name字段在列表值内
         name[0]=a&name[1]=b&name[2]=c 
         # 或 
         name__in[0]=a&name__in[1]=b&name__in[2]=c
         ```

         支持的查询过滤条件如下：

         | 过滤条件     | 含义                                                         |
         | ------------ | ------------------------------------------------------------ |
         | N/A          | 精确查询，完全等于条件，如果多个此条件出现，则认为条件在列表中 |
         | contains     | 模糊查询，包含条件                                           |
         | icontains    | 同上，不区分大小写                                           |
         | startswith   | 模糊查询，以xxxx开头                                         |
         | istartswith  | 同上，不区分大小写                                           |
         | endswith     | 模糊查询，以xxxx结尾                                         |
         | iendswith    | 同上，不区分大小写                                           |
         | in           | 精确查询，条件在列表中                                       |
         | notin        | 精确查询，条件不在列表中                                     |
         | equal        | 等于                                                         |
         | notequal     | 不等于                                                       |
         | less         | 小于                                                         |
         | lessequal    | 小于等于                                                     |
         | greater      | 大于                                                         |
         | greaterequal | 大于等于                                                     |

    2. - 偏移量与数量限制

         查询返回列表时，通常需要指定偏移量以及数量限制

         eg. 

         ```bash
         __offset=10&__limit=20
         ```

         代表取偏移量10，限制20条结果

    3. - 排序

         排序对某些场景非常重要，可以免去客户端很多工作量

         ```bash
         __orders=name,-env_code
         ```

         多个字段排序以英文逗号间隔，默认递增，若字段前面有-减号则代表递减

       	      PS：我可以使用+name代表递增吗？
        
       	      可以，但是HTTP URL中+号实际上的空格的编码，如果传递__orders=+name,-env_code，在HTTP中实际等价于__orders=空格name,-env_code, 无符号默认递增，因此无需多传递一个+号，传递字段即可


### 进阶开发

- 用户输入校验
- 高级DB操作[hooks, 自定义query]
- 会话重用和事务控制
- 缓存
- 异步任务
- 频率限制
- 数据库版本管理



## 国际化i18n