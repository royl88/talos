# coding=utf-8
"""
包装了celery，方便进行远程调用，回调
依赖：
    库：
        celery
    配置：
        "celery": {
            "worker_concurrency": 8,
            "broker_url": "pyamqp://guest@127.0.0.1//",
            "result_backend": "redis://127.0.0.1",
            "imports": [
                "{$project_name}.workers.{$app_name}.tasks"
            ],
            "task_serializer": "json",
            "result_serializer": "json",
            "accept_content": ["json"],
            "worker_prefetch_multiplier": 1,
            "task_routes": {
                "{$project_name}.workers.*": {"queue": "{$your_queue_name}",
                                        "exchange": "{$your_exchange_name}",
                                        "routing_key": "{$your_routing_name}"}
            }
        },
        "worker": {
            "callback": {
                "strict_client": true,
                "allow_hosts": ["127.0.0.1"]
            }
        }

以上，{$xxxx}包括的内容代表需要替换为实际工程项目对应名称
{$project_name}为项目名称
{$app_name}为当前应用模块名称
{$your_queue_name}{$your_exchange_name}{$your_routing_name} 简单认为是本项目的专用队列名称，可以一致，详细参考celery

使用方式：
1. 项目代码目录下建立workers.{$app_name}.tasks.py用于编写远程任务
2. 项目代码目录下建立workers.{$app_name}.callback.py用于编写远程回调
3. tasks.py任务示例
from talos.common import celery
from talos.common import async_helper
from {$project_name}.workers.{$app_name} import callback
@celery.app.task
def add(task_id, x, y):
    # task_id, x, y均为函数自定义参数，本次我们需要做回调演示，因此我们需要task_id异步任务id，以及加法的x和y
    result = x + y
    # 这里还可以通知其他附加任务,当需要本次的一些计算结果来启动二次任务时使用
    # 接受参数：task调用函数路径 & 函数命名参数(dict)
    async_helper.send_task('{$project_name}.workers.{$app_name}.tasks.other_task', kwargs={'result': result, 'task_id': task_id})
    # send callback的参数必须与callback函数参数匹配(request，response除外)
    # url_base为callback注册的api地址，eg: http://127.0.0.1:9001
    # 仅接受data参数，若有多个参数，可打包为可json序列化的类型
    # task_id为url接受参数(所以函数也必须接受此参数)
    async_helper.send_callback(url_base, callback.callback_add,
                                data,
                                task_id=task_id)
    # 此处是异步回调结果，不需要服务器等待或者轮询，worker会主动发送进度或者结果，可以不return
    # 如果想要使用return方式，则按照正常celery流程编写代码
    return result

@celery.app.task
def other_task(task_id, result):
    # task_id, result均为函数自定义参数，本次我们需要做通知演示，因此我们需要task_id原始异步任务id，以及加法的result
    pass


4. callback.py回调示例
from talos.common import async_helper
# data是强制参数，task_id为url强制参数(如果url没有参数，则函数也无需task_id)
@async_helper.callback('/callback/add/{task_id}')
def callback_add(data, task_id, request=None, response=None):
    # 想要使用db功能，需要修改{$project_name}.server.celery_worker文件的默认项
    # 移除 # base.initialize_db()的注释符号
    task_db_api().update(task_id, data)

5. route中添加回调
from talos.common import async_helper
from {$project_name}.workers.{$app_name} import callback

async_helper.add_callback_route(api, callback.callback_add)

6. 启动worker
celery -A {$project_name}.server.celery_worker worker --autoscale=50,4 --loglevel=DEBUG -Q {$your_queue_name}

7. 调用
add.delay('id1', 1, 1)
会有任务发送到worker中，然后woker会启动一个other_task任务，并回调url将结果发送会服务端
（如果API模块有统一权限校验，请注意放行）
"""

from __future__ import absolute_import

from celery import Celery
from talos.core import config


CONF = config.CONF


app = Celery(CONF.locale_app)
app.config_from_object(CONF.celery.to_dict())
