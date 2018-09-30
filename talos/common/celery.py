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

使用方式：
1. 建立workers.app_name.task.py用于编写远程任务
2. 建立workers.app_name.callback.py用于编写远程回调
3. task.py任务示例
from talos.common import celery
from talos.common import async_helper
from project_name.workers.app_name import callback
@celery.app.task
def add(task_id, x, y):
    result = x + y
    # 这里还可以通知其他附加任务
    async_helper.send_task('project_name.workers.app_name.tasks.other_task', kwargs={'result': result, 'task_id': task_id})
    # send callback的参数必须与callback函数参数匹配(request，response除外)
    async_helper.send_callback(url_base, callback.callback_add,
                                data,
                                task_id=task_id)
    # 此处是异步回调结果，不需要服务器等待或者轮询，worker会主动发送进度或者结果，可以不return
    # 如果想要使用return方式，则按照正常celery流程编写代码
    return result

4. callback.py回调示例
from talos.common import async_helper
# 可以使用函数参数中的任意变量作为url的变量（为了某种情况下作为url区分），当然也可以不用
@async_helper.callback('/callback/add/{task_id}')
def callback_add(data, task_id, request=None, response=None):
    db.save(task_id, result)

5. route中添加回调
from talos.common import async_helper
from project_name.workers.app_name import callback

async_helper.add_callback_route(api, callback.callback_add)

6. 启动worker
celery -A talos.server.celery_worker worker --autoscale=50,4 --loglevel=DEBUG -Q your_queue_name

7. 调用
add('id', 1, 1).delay()
会有任务发送到worker中，然后woker会启动一个other_task任务，并回调url将结果发送会服务端
"""

from __future__ import absolute_import

from celery import Celery
from talos.core import config


CONF = config.CONF


app = Celery(CONF.locale_app)
app.config_from_object(CONF.celery.to_dict())