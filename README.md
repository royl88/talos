talos project[^1]
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

#### 设计数据库

略

#### 导出数据库模型

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

#### 数据库模型类的魔法类

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

#### 增删改查的资源类

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

内部查询通过组装dict来实现过滤条件，filter在表达 == 或这 in 列表时，可以直接使用一级字段即可，如name等于test：{'name': 'test'}

id在1,2,3,4内：{'id': ['1', '2', '3', '4']}

更复杂的查询需要通过嵌套dict来实现：{'字段名称': {'过滤条件': '值'}}

| 过滤条件 | 值类型       |
| -------- | ------------ |
| in       | list         |
| nin      | list         |
| eq       | 根据字段类型 |
| ne       | 根据字段类型 |
| lt       | 根据字段类型 |
| lte      | 根据字段类型 |
| gt       | 根据字段类型 |
| gte      | 根据字段类型 |
| like     | string       |
| ilike    | string       |
| starts   | string       |
| istarts  | string       |
| ends     | string       |
| iends    | string       |

#### 业务api控制类

api的模块为：cms.apps.user.api

resource处理的是DB的CRUD操作，但往往业务类代码需要有复杂的处理逻辑，并且涉及多个resource类的相互操作，因此需要封装api层来处理此类逻辑，此处我们示例没有复杂逻辑，直接沿用定义即可

```python
User = resource.User
UserPhoneNum = resource.UserPhoneNum
```

#### Collection和Item Controller

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

#### route路由映射

route模块为：cms.apps.user.route

提供了Controller后，我们还需要将其与URL路由进行映射才能调用，route模块中，必须有add_routes函数，注册app的时候会默认寻找这个函数来注册路由

```python
def add_routes(api):
    api.add_route('/v1/users', controller.CollectionUser())
    api.add_route('/v1/users/{rid}', controller.ItemUser())
```

#### 配置启动加载app

我们在引导开始时创建的项目配置文件存放在./etc中，所以我们的配置文件在./etc/cms.conf，修改

```javascript
...
"application": {
        "names": [
            "cms.apps.user"]
},
...
```

#### 启动调试或部署

在源码目录中有server包，其中simple_server是用于开发调试用，不建议在生产中使用

python simple_server.py

#### 测试API

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

- **过滤条件**

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

| 过滤条件     | 含义                                                           |
| ------------ | ------------------------------------------------------------   |
| N/A          | 精确查询，完全等于条件，如果多个此条件出现，则认为条件在列表中 |
| contains     | 模糊查询，包含条件                                             |
| icontains    | 同上，不区分大小写                                             |
| startswith   | 模糊查询，以xxxx开头                                           |
| istartswith  | 同上，不区分大小写                                             |
| endswith     | 模糊查询，以xxxx结尾                                           |
| iendswith    | 同上，不区分大小写                                             |
| in           | 精确查询，条件在列表中                                         |
| notin        | 精确查询，条件不在列表中                                       |
| equal        | 等于                                                           |
| notequal     | 不等于                                                         |
| less         | 小于                                                           |
| lessequal    | 小于等于                                                       |
| greater      | 大于                                                           |
| greaterequal | 大于等于                                                       |

- **偏移量与数量限制**

     查询返回列表时，通常需要指定偏移量以及数量限制

     eg. 

     ```bash
     __offset=10&__limit=20
     ```

     代表取偏移量10，限制20条结果

- **排序**

     排序对某些场景非常重要，可以免去客户端很多工作量

     ```bash
     __orders=name,-env_code
     ```

     多个字段排序以英文逗号间隔，默认递增，若字段前面有-减号则代表递减

           PS：我可以使用+name代表递增吗？
         
           可以，但是HTTP URL中+号实际上的空格的编码，如果传递__orders=+name,-env_code，在HTTP中实际等价于__orders=空格name,-env_code, 无符号默认递增，因此无需多传递一个+号，传递字段即可


### 进阶开发

#### 用户输入校验

用户输入的数据，不一定是完全正确的，每个数据都需要校验后才能进行存储和处理，在上面已经提到过使用ColumnValidator来进行数据校验，这里主要是解释详细的校验规则和行为

1. ColumnValidator被默认集成在ResourceBase中，所以会自动进行校验判断

2. 未定义_validate时，将不启用校验，信任所有输入数据

3. 未定义的字段在清洗阶段会被忽略

4. 校验的关键函数为ResourceBase.validate

   ```python
   @classmethod
   def validate(cls, data, situation, orm_required=False, validate=True, rule=None):
       """
       验证字段，并返回清洗后的数据
       
       * 当validate=False，不会对数据进行校验，仅返回ORM需要数据
       * 当validate=True，对数据进行校验，并根据orm_required返回全部/ORM数据
       
       :param data: 清洗前的数据
       :type data: dict
       :param situation: 当前场景
       :type situation: string
       :param orm_required: 是否ORM需要的数据(ORM即Model表定义的字段)
       :type orm_required: bool
       :param validate: 是否验证规则
       :type validate: bool
       :param rule: 规则配置
       :type rule: dict
       :returns: 返回清洗后的数据
       :rtype: dict
       """
   ```

   *validate_on为什么是填写：create:M或者update:M，因为validate按照函数名进行场景判定，在ResourceBase.create函数中，默认将situation绑定在当前函数，即 'create'，update同理，而M代表必选，O代表可选*

5. 当前快速校验规则rule_type不能满足时，请使用Validator对象，内置Validator对象不能满足需求时，可以定制自己的Validator，Validator的定义需要满足2点：

   从NullValidator中继承

   重写validate函数，函数接受一个参数，并且返回True作为通过校验，返回错误字符串代表校验失败

6. Converter同上

#### 高级DB操作[hooks, 自定义query]

##### 简单hooks

在db创建一个记录时，假设希望id是自动生成的UUID，通常这意味着我们不得不重写create函数：

```python
class User(ResourceBase):
    orm_meta = models.User
    _primary_keys = 'id'
    
    def create(self, resource, validate=True, detail=True):
        resource['id'] = uuid.uuid4().hex
        super(User, self).create(resource, validate=validate, detail=validate)
```

这样的操作对于我们而言是很笨重的，甚至create的实现比较复杂，让我们不希望到create里面去加这些不是那么关键的代码，对于这些操作，talos分成了2种场景，_before_create, _addtional_create，根据名称我们能知道，它们分别代表

create执行开始前：常用于一些数据的自动填充

create执行后但未提交：常用于强事务控制的操作，可以使用同一个事务进行操作以便一起提交或回滚

同理还有update，delete

同样的list和count都有_addtional_xxxx钩子

##### 动态hooks

以上的hooks都是类成员函数代码定义的，当使用者想要临时增加一个hook的时候呢，或者根据某个条件判断是否使用一个hook时，我们需要一种更动态的hook来支持，目前只有list和count支持此类hooks

list,count的hook的函数定义为：function(query, filters)，需要return 处理后的query

eg. self.list(hooks=[lambda q,f: return q])

##### 自定义query

在更复杂的场景下我们封装的操作函数可能无法达到目的，此时可以使用底层的SQLAlchemy Query对象来进行处理，比如在PG中INET类型的比较操作：

一个场景：我们不希望用户新增的子网信息与现有子网重叠

```python
query = self._get_query(session)
query = query.filter(self.orm_meta.cidr.op(">>")(
    subnet['cidr']) | self.orm_meta.cidr.op("<<")(subnet['cidr']))
if query.one_or_none():
    raise ConflictError()
```

#### 会话重用和事务控制

在talos中，每个ResourceBase对象都可以申请会话和事务，而且可以接受一个已有的会话和事务对象，在使用完毕后talos会自动帮助你进行回滚/提交/关闭，这得益与python的with子句

```python
u = User()
with u.transaction() as session:
    u.update(...)
    # 事务重用, 可以查询和变更操作, with子句结束会自动提交，异常会自动回滚
    UserPhone(transaction=session).delete(...)
    UserPhone(transaction=session).list(...)
with u.get_session() as session:
    # 会话重用, 可以查询
    UserPhone(session=session).list(...)
```

#### 缓存

##### 配置和使用

#### 异步任务

##### 定义异步任务

##### 异步任务配置

##### 结果回调

#### 定时任务[^ 2]

##### 静态配置定时任务：

使用最原始的celery定时任务配置，最快捷的定时任务例子：

```json
    "celery": {
        "worker_concurrency": 8,
        "broker_url": "pyamqp://test:test@127.0.0.1//",
        ...
        "beat_schedule": {
            "test_every_5s": {
                "task": "cms.workers.periodic.tasks.test_add",
                "schedule": 5,
                "args": [3,6] 
            }
        }
```

启动beat： celery -A cms.server.celery_worker beat --loglevel=DEBUG

启动worker：celery -A cms.server.celery_worker worker --loglevel=DEBUG -Q cms-dev-queue

可以看到每5s，beat会发送一个任务，worker会接收此任务进行处理，从而形成定时任务

使用过原生celery的人可能看出这里存在的问题：crontab是对象，json配置是无法传递，只能配置简单的间隔任务，确实，缺省情况下由于配置文件格式的原因无法提供更高级的定时任务配置，所以talos提供了自定义的Scheduler：TScheduler，这个调度器可以从配置文件中解析interval、crontab类型的定时任务，从而覆盖更广泛的需求，而使用也非常简单：

```json
"celery": {
    "worker_concurrency": 8,
    "broker_url": "pyamqp://test:test@127.0.0.1//",
    ...
    "beat_schedule": {
        "test_every_5s": {
            "task": "cms.workers.periodic.tasks.test_add",
            "schedule": 5,
            "args": [3,6] 
        },
        "test_every_123s": {
            "type": "interval",
            "task": "cms.workers.periodic.tasks.test_add",
            "schedule": "12.3",
            "args": [3,6] 
        },
        "test_crontab_simple": {
            "type": "crontab",
            "task": "cms.workers.periodic.tasks.test_add",
            "schedule": "*/1",
            "args": [3,6] 
        },
        "test_crontab": {
            "type": "crontab",
            "task": "cms.workers.periodic.tasks.test_add",
            "schedule": "1,13,30-45,50-59/2 *1 * * *",
            "args": [3,6] 
        }
    }
```
依然是在配置文件中定义，多了一个type参数，用于帮助调度器解析定时任务，此外还需要指定使用talos的TScheduler调度器，比如配置中指定:

```
"celery": {
    "worker_concurrency": 8,
    "broker_url": "pyamqp://test:test@127.0.0.1//",
    ...
    "beat_schedule": {...}
    "beat_scheduler": "talos.common.celery_scheduler:TScheduler"
```

或者命令行启动时指定：

启动beat： celery -A cms.server.celery_worker beat --loglevel=DEBUG -S talos.common.celery_scheduler:TScheduler 

启动worker：celery -A cms.server.celery_worker worker --loglevel=DEBUG -Q cms-dev-queue



  ##### 动态配置定时任务：

使用TScheduler预留的hooks进行动态定时任务配置：

TODO

使用官方的setup_periodic_tasks进行动态配置

  截止当前2018.11.13 celery 4.2.0在定时任务中依然存在问题，使用官方建议的on_after_configure动态配置定时器时，定时任务不会被触发：[GitHub Issue 3589](https://github.com/celery/celery/issues/3589)

  ```
  @celery.app.on_after_configure.connect
  def setup_periodic_tasks(sender, **kwargs):
      sender.add_periodic_task(3.0, test.s('add every 3s by add_periodic_task'), name='add every 3s by add_periodic_task')
  
  @celery.app.task
  def test(arg):
      print(arg)
  ```

而测试以下代码有效，推荐使用：

```
@celery.app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(3.0, test.s('add every 3s by add_periodic_task'), name='add every 3s by add_periodic_task')

@celery.app.task
def test(arg):
    print(arg)
```

- **频率限制**

- **数据库版本管理**



## 国际化i18n

### 提取待翻译

### 合并已翻译

### 翻译

### 编译发布







[^1]: 本文档基于v1.1.8版本
[^ 2]: v1.1.9版本中新增了TScheduler支持动态的定时任务以及更丰富的配置定义定时任务