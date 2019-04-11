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
* 快速RESTfult CRUD API开发
* filters，pagination，orders支持
* validation数据校验
* 异步任务集成[celery]
* 定时任务集成[celery]
* 频率限制
* 国际化i18n支持
* SMTP邮件、AD域、CSV导出、缓存等常用模块集成

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

更复杂的查询需要通过嵌套dict来实现[^ 5]：

- 简单组合：{'字段名称': {'过滤条件1': '值', '过滤条件2': '值'}}

- 简单$or+组合查询：{'$or': [{'字段名称': {'过滤条件': '值'}}, {'字段名称': {'过滤条件1': '值', '过滤条件2': '值'}}]}

- 简单$and+组合查询：{'$and': [{'字段名称': {'过滤条件': '值'}}, {'字段名称': {'过滤条件1': '值', '过滤条件2': '值'}}]}

- 复杂$and+$or+组合查询：

  {'$and': [

  ​               {'$or': [{'字段名称': '值'}, {'字段名称': {'过滤条件1': '值', '过滤条件2': '值'}}]}, 

  ​               {'字段名称': {'过滤条件1': '值', '过滤条件2': '值'}}

  ]}

| 过滤条件 | 值类型          | 含义                                                           |
| -------- | --------------- | -------------------------------------------------------------- |
| like      | string         | 模糊查询，包含条件                                          |
| ilike     | string         | 同上，不区分大小写                                             |
| starts    | string         | 模糊查询，以xxxx开头                                           |
| istarts   | string         | 同上，不区分大小写                                             |
| ends      | string         | 模糊查询，以xxxx结尾                                           |
| iends     | string         | 同上，不区分大小写                                             |
| in        | list           | 精确查询，条件在列表中                                         |
| nin       | list           | 精确查询，条件不在列表中                                       |
| eq        | 根据字段类型   | 等于                                                           |
| ne        | 根据字段类型   | 不等于                                                         |
| lt        | 根据字段类型   | 小于                                                           |
| lte       | 根据字段类型   | 小于等于                                                       |
| gt        | 根据字段类型   | 大于                                                           |
| gte       | 根据字段类型   | 大于等于                                                       |
| nlike     | string         | 模糊查询，不包含                                               |
| nilike    | string         | 同上，不区分大小写                                             |
| null      | 任意           | 是NULL，等同于{'eq': None}，null主要提供HTTP API中使用                   |
| nnull     | 任意           | 不是NULL，等同于{'ne': None}，nnull主要提供HTTP API中使用                  |

过滤条件可以根据不同的数据类型生成不同的查询语句，varchar类型的in是 IN ('1', '2') , inet类型的in是<<=cidr

一般类型的eq是col='value'，bool类型的eq是col is TRUE，详见talos.db.filter_wrapper

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

获取**列表(查询)的接口**可以使用Query参数过滤，使用过滤字段=xxx 或 字段__查询条件=xxx方式传递

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

     同时支持全拼条件和缩写条件查询：


| 全拼条件     | 缩写条件 | 含义                                                         |
| ------------ | -------- | ------------------------------------------------------------ |
| N/A          |          | 精确查询，完全等于条件，如果多个此条件出现，则认为条件在列表中 |
| contains     | like     | 模糊查询，包含条件                                           |
| icontains    | ilike    | 同上，不区分大小写                                           |
| startswith   | starts   | 模糊查询，以xxxx开头                                         |
| istartswith  | istarts  | 同上，不区分大小写                                           |
| endswith     | ends     | 模糊查询，以xxxx结尾                                         |
| iendswith    | iends    | 同上，不区分大小写                                           |
| in           | in       | 精确查询，条件在列表中                                       |
| notin        | nin      | 精确查询，条件不在列表中                                     |
| equal        | eq       | 等于                                                         |
| notequal     | ne       | 不等于                                                       |
| less         | lt       | 小于                                                         |
| lessequal    | lte      | 小于等于                                                     |
| greater      | gt       | 大于                                                         |
| greaterequal | gte      | 大于等于                                                     |
| excludes     | nlike    | 模糊查询，不包含                                             |
| iexcludes    | nilike   | 同上，不区分大小写                                           |
| null         | null     | 是NULL                                                       |
| notnull      | nnull    | 不是NULL                                                     |
| hasany       | hasany   | *JSONB专用*   包含任意key，如['a','b', 'c'] hasany ['a','d'] |
| hasall       | hasall   | *JSONB专用*   包含所有key，如['a','b', 'c'] hasall ['a','c'] |
| within       | within   | *JSONB专用*   被指定json包含在内                             |
| nwithin      | nwithin  | *JSONB专用*   不被指定json包含在内                           |
| include      | include  | *JSONB专用*   包含指定的json                                 |
| ninclude     | ninclude | *JSONB专用*   不包含指定的json                               |



字段支持：普通column字段、relationship字段(single or list)、JSONB[^ 4]

假设有API对应如下表字段

```python
class User(Base, DictBase):
    __tablename__ = 'user'

    id = Column(String(36), primary_key=True)
    name = Column(String(36), nullable=False)
    department_id = Column(ForeignKey(u'department.id'), nullable=False)
    items = Column(JSONB, nullable=False)

    department = relationship(u'Department', lazy=False)
    addresses = relationship(u'Address', lazy=False, back_populates=u'user', uselist=True, viewonly=True)
    
class Address(Base, DictBase):
    __tablename__ = 'address'

    id = Column(String(36), primary_key=True)
    location = Column(String(36), nullable=False)
    user_id = Column(ForeignKey(u'user.id'), nullable=False)
    items = Column(JSONB, nullable=False)

    user = relationship(u'User', lazy=True)
    
class Department(Base, DictBase):
    __tablename__ = 'department'

    id = Column(String(36), primary_key=True)
    name = Column(String(36), nullable=False)
    user_id = Column(ForeignKey(u'user.id'), nullable=False)
```

可以这样构造过滤条件

/v1/users?name=小明

/v1/users?department.name=业务部

/v1/users?addresses.location__icontains=广东省

/v1/users?addresses.items.key__icontains=temp

/v1/users?items.0.age=60 # items = [{"age": 60, "sex": "male"}, {...}]

/v1/users?items.age=60 # items = {"age": 60, "sex": "male"}

> v1.2.0  起不支持的column或condition会触发ResourceBase._unsupported_filter(query, idx, name, op, value)函数，函数默认返回参数query以忽略未支持的过滤(兼容以前版本行为)，用户可以自行重载函数以实现自定义行为
>
> v1.2.2  unsupported_filter会默认构造一个空查询集，即不支持的column或condition会致使返回空结果




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

     ```
       PS：我可以使用+name代表递增吗？
     
       可以，但是HTTP URL中+号实际上的空格的编码，如果传递__orders=+name,-env_code，在HTTP中实际等价于__orders=空格name,-env_code, 无符号默认递增，因此无需多传递一个+号，传递字段即可
     ```

- **字段选择**

     接口返回中，如果字段信息太多，会导致传输缓慢，并且需要客户端占用大量内存处理

     ```bash
     __fields=name,env_code
     ```

     可以指定返回需要的字段信息，或者干脆不指定，获取所有服务器支持的字段


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

默认配置为进程内存，超时60秒

```python
'cache': {
        'type': 'dogpile.cache.memory',
        'expiration_time': 60
}
```

缓存后端支持取决于dogpile模块，可以支持常见的memcache，redis等

如：redis

```python
"cache": {
        "type": "dogpile.cache.redis",
        "expiration_time": 6,
        "arguments": {
            "host": "127.0.0.1",
            "password": "football",
            "port": 1234,
            "db": 0,
            "redis_expiration_time": 60,
            "distributed_lock": true
        }
    }
```

使用方式

```python
from talos.common import cache

cache.get(key, exipres=None)
cache.set(key, value)
cache.validate(value)
cache.get_or_create(key, creator, expires=None)
cache.delete(key)
```



#### 异步任务

##### 定义异步任务

建立workers.app_name.task.py用于编写远程任务
建立workers.app_name.callback.py用于编写远程回调
task.py任务示例

```python
from talos.common import celery
from talos.common import async_helper
from cms.workers.app_name import callback
@celery.app.task
def add(task_id, x, y):
    result = x + y
    # 这里还可以通知其他附加任务
    async_helper.send_task('cms.workers.app_name.tasks.other_task', kwargs={'result': result, 'task_id': task_id})
   # send callback的参数必须与callback函数参数匹配(request，response除外)
   async_helper.send_callback(url_base, callback.callback_add,
                               data,
                               task_id=task_id)
   # 此处是异步回调结果，不需要服务器等待或者轮询，worker会主动发送进度或者结果，可以不return
   # 如果想要使用return方式，则按照正常celery流程编写代码
   return result
```

callback.py回调示例
```python
from talos.common import async_helper
# 可以使用函数参数中的任意变量作为url的变量（为了某种情况下作为url区分），当然也可以不用
@async_helper.callback('/callback/add/{task_id}')
def callback_add(data, task_id, request=None, response=None):
    db.save(task_id, result)
```

route中添加回调
```python
from talos.common import async_helper
from project_name.workers.app_name import callback

def add_route(api):
    async_helper.add_callback_route(api, callback.callback_add)
```

启动worker
  celery -A cms.server.celery_worker worker --autoscale=50,4 --loglevel=DEBUG -Q your_queue_name

调用
  add('id', 1, 1).delay()
  会有任务发送到worker中，然后woker会启动一个other_task任务，并回调url将结果发送会服务端

##### 异步任务配置

依赖：
​    库：
​        celery

​    配置：

```
{
        ...
        "celery": {
            "worker_concurrency": 8,
            "broker_url": "pyamqp://guest@127.0.0.1//",
            "result_backend": "redis://127.0.0.1",
            "imports": [
                "project_name.workers.app_name.tasks"
            ],
            "task_serializer": "json",
            "result_serializer": "json",
            "accept_content": ["json"],
            "worker_prefetch_multiplier": 1,
            "task_routes": {
                "project_name.workers.*": {"queue": "your_queue_name",
                                        "exchange": "your_exchange_name",
                                        "routing_key": "your_routing_name"}
            }
        },
        "worker": {
            "callback": {
                "strict_client": true,
                "allow_hosts": ["127.0.0.1"]
            }
        }
}
```



#### 定时任务[^ 2]

talos中你可以使用原生celery的定时任务机制，也可以使用talos中提供的扩展定时任务(TScheduler)，扩展的定时任务可以在5s(可通过beat_max_loop_interval来修改这个时间)内发现定时任务的变化并刷新调度，从而提供动态的定时任务，而定时任务的来源可以从配置文件，也可以通过自定义的函数中动态提供

> 原生celery的scheduler是不支持动态定时任务的

> 使用原生celery定时任务因为talos配置项为json数据而无法提供复杂类型的schedule，当然也可以使用add_periodic_task来解决，但会降低我们使用的便利性
>
> 这些问题在talos扩展定时任务中得以解决

##### 静态配置定时任务：

使用最原始的celery定时任务配置，最快捷的定时任务例子[^ 3]：

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
    "beat_scheduler": "talos.common.scheduler:TScheduler"
```

或者命令行启动时指定：

启动beat： celery -A cms.server.celery_worker beat --loglevel=DEBUG -S talos.common.scheduler:TScheduler 

启动worker：celery -A cms.server.celery_worker worker --loglevel=DEBUG -Q cms-dev-queue

除了type，TScheduler的任务还提供了很多其他的扩展属性，以下是属性以及其描述

```
name:           string, 唯一名称
task:           string, 任务模块函数
[description]:  string, 备注信息
[type]:         string, interval 或 crontab, 默认 interval
schedule:       string/int/float/schedule eg. 1.0,'5.1', '10 *' , '*/10 * * * *' 
args:           tuple/list, 参数
kwargs:         dict, 命名参数
[priority]:     int, 优先级, 默认5
[expires]:      int, 单位为秒，当任务产生后，多久还没被执行会认为超时
[enabled]:      bool, True/False, 默认True
[max_calls]:    None/int, 最大调度次数, 默认None无限制
[last_updated]: Datetime, 任务最后更新时间，常用于判断是否有定时任务需要更新
```



##### 动态配置定时任务：

TScheduler的动态任务仅限用户自定义的所有schedules
所有定时任务 = 配置文件任务 + add_periodic_task任务 + hooks任务，hooks任务可以通过相同name来覆盖已存在配置中的任务，否则相互独立

- 使用TScheduler预留的hooks进行动态定时任务配置(推荐方式)：

  TScheduler中预留了2个hooks：talos_on_user_schedules_changed/talos_on_user_schedules

  **talos_on_user_schedules_changed**钩子用于判断是否需要更新定时器，钩子被执行的最小间隔是beat_max_loop_interval(如不设置默认为5s)

  钩子定义为callable(scheduler)，返回值是True/False

  **talos_on_user_schedules**钩子用于提供新的定时器字典数据

  钩子定义为callable(scheduler)，返回值是字典，全量的自定义动态定时器

  我们来尝试提供一个，每过13秒自动生成一个全新定时器的代码

  以下是cms.workers.periodic.hooks.py的文件内容

  ```python
  import datetime
  from datetime import timedelta
  import random
  
  # talos_on_user_schedules_changed, 用于判断是否需要更新定时器
  # 默认每5s调用一次
  class ChangeDetection(object):
      '''
      等价于函数，只是此处我们需要保留_last_modify属性所以用类来定义callable
      def ChangeDetection(scheduler):
          ...do something...
      '''
      def __init__(self, scheduler):
          self._last_modify = self.now()
      def now(self):
          return datetime.datetime.now()
      def __call__(self, scheduler):
          now = self.now()
          # 每过13秒定义定时器有更新
          if now - self._last_modify >= timedelta(seconds=13):
              self._last_modify = now
              return True
          return False
  
  # talos_on_user_schedules, 用于提供新的定时器字典数据
  # 在talos_on_user_schedules_changed hooks返回True后被调用
  class Schedules(object):
      '''
      等价于函数
      def Schedules(scheduler):
          ...do something...
      '''
      def __init__(self, scheduler):
          pass
      def __call__(self, scheduler):
          interval = random.randint(1,10)
          name = 'dynamic_every_%s s' % interval
          # 生成一个纯随机的定时任务
          return {name: {'task': 'cms.workers.periodic.tasks.test_add', 'schedule': interval, 'args': (1,3)}}
  ```

  配置文件如下：

  ```json
      "celery": {
          ...
          "beat_schedule": {
              "every_5s_max_call_2_times": {
                  "task": "cms.workers.periodic.tasks.test_add",
                  "schedule": "5",
                  "max_calls": 2,
                  "enabled": true,
                  "args": [1, 3]
              }
          },
          "talos_on_user_schedules_changed":[
              "cms.workers.periodic.hooks:ChangeDetection"],
          "talos_on_user_schedules": [
              "cms.workers.periodic.hooks:Schedules"]
      },
  ```

  得到的结果是，一个每5s，最多调度2次的定时任务；一个每>=13s自动生成的随机定时任务

- 使用官方的setup_periodic_tasks进行动态配置

  见celery文档

  截止当前2018.11.13 celery 4.2.0在定时任务中依然存在问题，使用官方建议的on_after_configure动态配置定时器时，定时任务不会被触发：[GitHub Issue 3589](https://github.com/celery/celery/issues/3589)

  ```
  @celery.app.on_after_configure.connect
  def setup_periodic_tasks(sender, **kwargs):
      sender.add_periodic_task(3.0, test.s('add every 3s by add_periodic_task'), name='add every 3s by add_periodic_task')
  
  @celery.app.task
  def test(arg):
      print(arg)
  ```

而测试以下代码有效，可以使用以下方法：

```
@celery.app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(3.0, test.s('add every 3s by add_periodic_task'), name='add every 3s by add_periodic_task')

@celery.app.task
def test(arg):
    print(arg)
```

#### 频率限制

##### controller & 中间件 频率限制

主要用于http接口频率限制

    基本使用步骤：
    
    - 在controller上配置装饰器
    - 将Limiter配置到启动中间件
    
    装饰器通过管理映射关系表LIMITEDS，LIMITEDS_EXEMPT来定位用户设置的类实例->频率限制器关系，
    频率限制器是实力级别的，意味着每个实例都使用自己的频率限制器
    
    频率限制器有7个主要参数：频率设置，关键限制参数，限制范围，是否对独立方法进行不同限制, 算法，错误提示信息, hit函数
    
    - 频率设置：格式[count] [per|/] [n (optional)] [second|minute|hour|day|month|year]
    - 关键限制参数：默认为IP地址(支持X-Forwarded-For)，自定义函数：def key_func(request) -> string
    - 限制范围：默认python类完整路径，自定义函数def scope_func(request) -> string
    - 是否对独立方法进行不同限制: 布尔值，默认True
    - 算法：支持fixed-window、fixed-window-elastic-expiry、moving-window
    - 错误提示信息：错误提示信息可接受3个格式化（limit，remaining，reset）内容
    - hit函数：函数定义为def hit(resource, request) -> bool，为True时则触发频率限制器hit，否则忽略

> PS：真正的频率限制范围 = 关键限制参数(默认IP地址) + 限制范围(默认python类完整路径) + 方法名(如果区分独立方法)，当此频率范围被命中后才会触发频率限制





###### 静态频率限制(配置/代码)

**controller级的频率限制**

```python
# coding=utf-8

import falcon
from talos.common import decorators as deco
from talos.common import limitwrapper

# 快速自定义一个简单支持GET、POST请求的Controller
# add_route('/things', ThingsController())

@deco.limit('1/second')
class ThingsController(object):
    def on_get(self, req, resp):
        """Handles GET requests, using 1/second limit"""
        resp.body = ('It works!')
    def on_post(self, req, resp):
        """Handles POST requests, using global limit(if any)"""
        resp.body = ('It works!')
```

###### 全局级的频率限制

```json
{
    "rate_limit": {
        "enabled": true,
        "storage_url": "memory://",
        "strategy": "fixed-window",
        "global_limits": "5/second",
        "per_method": true,
        "header_reset": "X-RateLimit-Reset",
        "header_remaining": "X-RateLimit-Remaining",
        "header_limit": "X-RateLimit-Limit"
    }
}
```

###### 基于中间件动态频率限制

以上的频率限制都是预定义的，无法根据具体参数进行动态的更改，而通过重写中间件的get_extra_limits函数，我们可以获得动态追加频率限制的能力

```python
class MyLimiter(limiter.Limiter):
    def __init__(self, *args, **kwargs):
        super(MyLimiter, self).__init__(*args, **kwargs)
        self.mylimits = {'cms.apps.test1': [wrapper.LimitWrapper('2/second')]}
    def get_extra_limits(self, request, resource, params):
        if request.method.lower() == 'post':
            return self.mylimits['cms.apps.test1']

```

频率限制默认被加载在了系统的中间件中，如果不希望重复定义中间件，可以在cms.server.wsgi_server中修改项目源代码：

```python
application = base.initialize_server('cms',
                                     ...
                                     middlewares=[
                                         globalvars.GlobalVars(),
                                         MyLimiter(),
                                         json_translator.JSONTranslator()],
                                     override_middlewares=True)
```

##### 函数级频率限制

```python
from talos.common import decorators as deco

@deco.limit('1/second')
def test():
    pass
```



    用于装饰一个函数、类函数表示其受限于此调用频率
    当装饰类成员函数时，频率限制范围是类级别的，意味着类的不同实例共享相同的频率限制，
    如果需要实例级隔离的频率限制，需要手动指定key_func，并使用返回实例标识作为限制参数
    
    :param limit_value: 频率设置：格式[count] [per|/] [n (optional)][second|minute|hour|day|month|year]
    :param scope: 限制范围空间：默认python类/函数完整路径.
    :param key_func: 关键限制参数：默认为空字符串，自定义函数：def key_func(*args, **kwargs) -> string
    :param strategy: 算法：支持fixed-window、fixed-window-elastic-expiry、moving-window
    :param message: 错误提示信息：错误提示信息可接受3个格式化（limit，remaining，reset）内容
    :param storage: 频率限制后端存储数据，如: memory://, redis://:pass@localhost:6379
    :param hit_func: 函数定义为def hit(result) -> bool，为True时则触发频率限制器hit，否则忽略
    :param delay_hit: 默认在函数执行前测试频率hit，可以设置为True将频率测试hit放置在函数执行后，搭配hit_func
                       使用，可以获取到函数执行结果来控制是否执行hit
关于函数频率限制模块更多用例，请见单元测试tests.test_limit_func

#### 数据库版本管理

修改models.py为最终目标表模型，运行命令：

alembic revision --autogenerate -m "add table: xxxxx"

备注不支持中文, autogenerate用于生成upgrade，downgrade函数内容，生成后需检查升级降级函数是否正确

升级：alembic upgrade head

降级：alembic downgrade base

head指最新版本，base指最原始版本即models第一个version，更多升级降级方式如下：

- alembic upgrade +2 升级2个版本

- alembic downgrade -1 回退一个版本

- alembic upgrade ae10+2 升级到ae1027a6acf+2个版本


#### 单元测试

talos生成的项目预置了一些依赖要求，可以更便捷的使用pytest进行单元测试，如需了解更详细的单元测试编写指导，请查看pytest文档

> python setup.py test

可以简单从命令行输出中查看结果，或者从unit_test_report.html查看单元测试报告，从htmlcov/index.html中查看覆盖测试报告结果

示例可以从talos源码的tests文件夹中查看

```bash
$ tree tests
tests
├── __init__.py
├── models.py
├── test_db_filters.py
├── unittest.conf
├── unittest.sqlite3
└── ...

```

单元测试文件以test_xxxxxx.py作为命名

## Sphinx注释文档

Sphinx的注释格式这里不再赘述，可以参考网上文档教程，talos内部使用的注释文档格式如下：

```
    """
    函数注释文档

    :param value: 参数描述
    :type value: 参数类型
    :returns: 返回值描述
    :rtype: `bytes`/`str` 返回值类型
    """
```



- 安装sphinx

- 在工程目录下运行sphinx-quickstart

  - root path for the documentation [.]: docs
  - Project name: cms
  - Author name(s): Roy
  - Project version []: 1.0.0
  - Project language [en]: zh_cn
  - autodoc: automatically insert docstrings from modules (y/n) [n]: y

- 可选的风格主题，推荐sphinx_rtd_theme，需要pip install sphinx_rtd_theme

- 修改docs/conf.py

  ```python
  # import os
  # import sys
  # sys.path.insert(0, os.path.abspath('.'))
  import os
  import sys
  sys.path.insert(0, os.path.abspath('..'))
  
  import sphinx_rtd_theme
  html_theme = "sphinx_rtd_theme"
  html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
  ```

- 生成apidoc sphinx-apidoc -o docs/ ./cms

- 生成html：

  - cd docs
  - make.bat html
  - 打开docs/_build/html/index.html

## 国际化i18n

同样以cms项目作为例子

### 提取待翻译

```bash
# 需要翻译项目的语言
find /usr/lib/python2.7/site-packages/cms/ -name "*.py" >POTFILES.in
# 需要翻译talos的语言
find /usr/lib/python2.7/site-packages/talos/ -name "*.py" >>POTFILES.in
# 提取为cms.po
xgettext --default-domain=cms --add-comments --keyword=_ --keyword=N_ --files-from=POTFILES.in --from-code=UTF8
```



### 合并已翻译

```bash
msgmerge cms-old.po cms.po -o cms.po
```



### 翻译

可以使用如Poedit的工具帮助翻译

(略)

### 编译发布

Windows：使用Poedit工具，则点击保存即可生成cms.mo文件

Linux：msgfmt --output-file=cms.mo cms.po

将mo文件发布到

/etc/fitportal/locale/$lang/LC_MESSAGES/

$lang即配置项中的language



## 工具库

### 带宽限速

talos.common.bandwidth_limiter:BandWidthLimiter

### 导出CSV

talos.common.exporter:export_csv

### LDAP登录认证

talos.common.ldap_util:Ldap

### SMTP邮件发送

talos.common.mailer:Mailer

### 访问控制规则校验器

talos.core.acl:Registry

### 实用小函数

talos.core.utils

## 配置项

talos中预置了很多控制程序行为的配置项，可以允许用户进行相关的配置：全局配置、启动服务配置、日志配置、数据库连接配置、缓存配置、频率限制配置、异步和回调配置

| 路径                                   | 类型   | 描述                                                         | 默认值                                                       |
| -------------------------------------- | ------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| host                                   | string | 主机名                                                       | 当前主机名                                                   |
| language                               | string | 系统语言翻译                                                 | en                                                           |
| locale_app                             | string | 国际化locale应用名称                                         | 当前项目名                                                   |
| locale_path                            | string | 国际化locale文件路径                                         | ./etc/locale                                                 |
| controller.list_size_limit_enabled     | bool   | 是否启用全局列表大小限制                                     | False                                                        |
| controller.list_size_limit             | int    | 全局列表数据大小，如果没有设置，则默认返回全部，如果用户传入limit参数，则以用户参数为准 | None                                                         |
| controller.criteria_key.offset         | string | controller接受用户的offset参数的关键key值                    | __offset                                                     |
| controller.criteria_key.limit          | string | controller接受用户的limit参数的关键key值                     | __limit                                                      |
| controller.criteria_key.orders         | string | controller接受用户的orders参数的关键key值                    | __orders                                                     |
| controller.criteria_key.fields         | string | controller接受用户的fields参数的关键key值                    | __fields                                                     |
| override_defalut_middlewares           | bool   | 覆盖系统默认加载的中间件                                     | Flase                                                        |
| server                                 | dict   | 服务监听配置项                                               |                                                              |
| server.bind                            | string | 监听地址                                                     | 0.0.0.0                                                      |
| server.port                            | int    | 监听端口                                                     | 9001                                                         |
| server.backlog                         | int    | 监听最大队列数                                               | 2048                                                         |
| log                                    | dict   | 日志配置项                                                   |                                                              |
| log.log_console                        | bool   | 是否将日志重定向到标准输出                                   | True                                                         |
| log.gunicorn_access                    | string | gunicorn的access日志路径                                     | ./access.log                                                 |
| log.gunicorn_error                     | string | gunicorn的error日志路径                                      | ./error.log                                                  |
| log.path                               | string | 全局日志路径                                                 | ./server.log                                                 |
| log.level                              | string | 日志级别                                                     | INFO                                                         |
| log.format_string                      | string | 日志字段配置                                                 | %(asctime)s.%(msecs)03d %(process)d %(levelname)s %(name)s:%(lineno)d [-] %(message)s |
| log.date_format_string                 | string | 日志时间格式                                                 | %Y-%m-%d %H:%M:%S                                            |
| log.loggers                            | list   | 模块独立日志配置，列表每个元素是dict: [{"name": "cms.test.api", "path": "api.log"}] |                                                              |
| log.loggers.name                       | string | 模块名称路径，如cms.apps.test                                |                                                              |
| log.loggers.level                      | string | 日志级别                                                     |                                                              |
| log.loggers.path                       | string | 日志路径                                                     |                                                              |
| db                                     | dict   | 默认数据库配置项，用户可以自行定义其他DB配置项，但需要自己初始化DBPool对象(可以参考DefaultDBPool进行单例控制) |                                                              |
| db.connection                          | string | 连接字符串                                                   |                                                              |
| db.pool_size                           | int    | 连接池大小                                                   | 3                                                            |
| db.pool_recycle                        | int    | 连接最大空闲时间，超过时间后自动回收                         | 3600                                                         |
| db.pool_timeout                        | int    | 获取连接超时时间，单位秒                                     | 5                                                            |
| db.max_overflow                        | int    | 突发连接池扩展大小                                           | 5                                                            |
| dbcrud                                 | dict   | 数据库CRUD控制项                                             |                                                              |
| dbcrud.unsupported_filter_as_empty     | bool   | 当遇到不支持的filter时的默认行为，1是返回空结果，2是忽略不支持的条件，由于历史版本的行为默认为2，因此其默认值为False，即忽略不支持的条件 | False                                                        |
| cache                                  | dict   | 缓存配置项                                                   |                                                              |
| cache.type                             | string | 缓存后端类型                                                 | dogpile.cache.memory                                         |
| cache.expiration_time                  | int    | 缓存默认超时时间，单位为秒                                   | 3600                                                         |
| cache.arguments                        | dict   | 缓存额外配置                                                 | None                                                         |
| application                            | dict   |                                                              |                                                              |
| application.names                      | list   | 加载的应用列表，每个元素为string，代表加载的app路径          | []                                                           |
| rate_limit                             | dict   | 频率限制配置项                                               |                                                              |
| rate_limit.enabled                     | bool   | 是否启用频率限制                                             | False                                                        |
| rate_limit.storage_url                 | string | 频率限制数据存储计算后端                                     | memory://                                                    |
| rate_limit.strategy                    | string | 频率限制算法，可选fixed-window，fixed-window-elastic-expiry，moving-window | fixed-window                                                 |
| rate_limit.global_limits               | string | 全局频率限制(依赖于全局中间件)，eg. 1/second; 5/minute       | None                                                         |
| rate_limit.per_method                  | bool   | 是否为每个HTTP方法独立频率限制                               | True                                                         |
| rate_limit.header_reset                | string | HTTP响应头，频率重置时间                                     | X-RateLimit-Reset                                            |
| rate_limit.header_remaining            | string | HTTP响应头，剩余的访问次数                                   | X-RateLimit-Remaining                                        |
| rate_limit.header_limit                | string | HTTP响应头，最大访问次数                                     | X-RateLimit-Limit                                            |
| celery                                 | dict   | 异步任务配置项                                               |                                                              |
| celery.talos_on_user_schedules_changed | list   | 定时任务变更判断函数列表"talos_on_user_schedules_changed":["cms.workers.hooks:ChangeDetection"], |                                                              |
| celery.talos_on_user_schedules         | list   | 定时任务函数列表"talos_on_user_schedules": ["cms.workers.hooks:AllSchedules"] |                                                              |
| worker                                 | dict   | 异步工作进程配置项                                           |                                                              |
| worker.callback                        | dict   | 异步工作进程回调控制配置项                                   |                                                              |
| worker.callback.strict_client          | bool   | 异步工作进程认证时仅使用直连IP                               | True                                                         |
| worker.callback.allow_hosts            | list   | 异步工作进程认证主机IP列表，当设置时，仅允许列表内worker调用回调 | None                                                         |
| worker.callback.name.%s.allow_hosts    | list   | 异步工作进程认证时，仅允许列表内worker调用此命名回调         | None                                                         |



[^1]: 本文档基于v1.1.8版本，并增加了后续版本的一些特性描述
[^ 2]: v1.1.9版本中新增了TScheduler支持动态的定时任务以及更丰富的配置定义定时任务
[^ 3]: v1.1.8版本中仅支持这类简单的定时任务
[^ 4]: v1.2.0版本增加了__fields字段选择 以及 null, notnull, nlike, nilike的查询条件 以及 relationship查询支持
[^ 5]: v1.2.0版本新增$or,$and查询支持