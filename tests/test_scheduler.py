# coding=utf-8

from __future__ import absolute_import

import time
import datetime
import logging

from talos.common import scheduler

LOG = logging.getLogger(__name__)


def job():
    pass


class MockAny(object):

    def __call__(self, *args, **kwargs):
        pass


class MockConf(object):
    result_expires = False
    broker_connection_max_retries = 1
    timezone = 'UTC'
    enable_utc = True
    beat_schedule = {
        "test_interval_crontab": {
            "type": "crontab",
            "task": "tests.test_scheduler.job",
            "schedule": "* * * * *",
            "args": []},
        "test_interval_1": {
            "type": "interval",
            "task": "tests.test_scheduler.job",
            "schedule": "1.0",
            "args": []},
        "test_interval_2_disable": {
            "type": "interval",
            "task": "tests.test_scheduler.job",
            "schedule": "1.5",
            "args": [],
            "enabled": False},
        "test_interval_1.5_max_3": {
            "type": "interval",
            "task": "tests.test_scheduler.job",
            "schedule": "1.5",
            "args": [],
            "enabled": True,
            "max_calls": 3},
        }
    beat_schedule_changed = {
        "test_interval_crontab": {
            "type": "crontab",
            "task": "tests.test_scheduler.job",
            "schedule": "* * * * *",
            "args": []},
        "test_interval_5": {
            "type": "interval",
            "task": "tests.test_scheduler.job",
            "schedule": "5",
            "args": []},
        "test_interval_2_disable": {
            "type": "interval",
            "task": "tests.test_scheduler.job",
            "schedule": "1.5",
            "args": [],
            "enabled": False},
        }
    beat_max_loop_interval = 3
    beat_sync_every = 60

def schedule_changed(val):
    return True
    
class MockBackend(object):
    supports_autoexpire = False


class MockTask(object):
    def get(self, *args, **kwargs):
        pass

class MockApp(object):
    timezone = 'UTC'
    conf = MockConf()
    backend = MockBackend()
    tasks = MockTask()
    def now(self):
        return datetime.datetime.now()
    
    def send_task(self, *args, **kwargs):
        o = MockAny()
        o.id = str(datetime.datetime.now())
        return o
    
    def set_current(self):
        pass
    
    def set_default(self):
        pass

    def connection_for_write(self):
        o = MockAny()
        o.ensure_connection = lambda x, y: True
        return o
    

def test_scheduler():
    c_app = MockApp()
    s = scheduler.TScheduler(c_app, Producer=MockAny())
    exit_code = 0
    counter = 0
    for counter in range(80):
        interval = s.tick()
        print('wait %s to due' % interval)
        if counter >= 70 and interval > 2.0:
            exit_code = 1
            break
        if counter == 50:
            c_app.conf.beat_schedule = c_app.conf.beat_schedule_changed
            s.on_user_schedules_changed = [schedule_changed]
        else:
            s.on_user_schedules_changed = []
        time.sleep(interval)
    assert exit_code == 1 and counter > 50

