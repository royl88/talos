# coding=utf-8

from __future__ import absolute_import

"""
scheduler需要的数据字段
{
    name: ..., 
    task: ..., 
    description: ...
    type: interval/crontab, 
    schedule: 可以是 '5.1' 或者 '*/1 * * * *' , 
    args:
    kwargs:
    priority: 优先级
    expires: 当任务产生后，多久还没被执行就认为超时
    enabled: True/False,
    once: True/False,
    last_updated: ..., 
}

"""

from datetime import timedelta

from celery import schedules
from celery.beat import ScheduleEntry, Scheduler

from talos.core.i18n import _


DEFAULT_MAX_INTERVAL = 5
DEFAULT_PRIORITY = 5


def maybe_schedule(s, relative=False, app=None):
    if isinstance(s, dict):
        schedule_type = s.get('type', 'interval')
        if schedule_type.upper() == 'INTERVAL':
            s = schedules.schedule(
                timedelta(seconds=float(s['schedule'])),
                app=app
            )
        elif schedule_type.upper() == 'CRONTAB':
            fields = s['schedule'].split()
            s = schedules.crontab(*fields, app=app)
        else:
            raise RuntimeError(_('can not parse schedule of type: %(type)s') % {'type': s.get('type', 'undefinded')})
    else:
        s.app = app
    return s


class TEntry(ScheduleEntry):
    def __init__(self, model, app=None):
        self.model = model.copy()
        self.app = app
        self.name = model['name']
        self.task = model['task']
        self.args = model.get('args')
        self.kwargs = model.get('kwargs')
        self.options = {'expires': model['expires']} if model.get('expires') else {}
        self.schedule = maybe_schedule(model, app=self.app)
        # 设置model以在model中传递参数
        self.model['last_run_at'] = model.get('last_run_at') or self.default_now()
        self.model['total_run_count'] = model.get('total_run_count') or 0
        self.model['last_updated'] = model.get('last_updated') or self.default_now()

    @property
    def enabled(self):
        return self.model.get('enabled', True)

    @property
    def once(self):
        return self.model.get('once', False)

    @property
    def priority(self):
        return self.model.get('priority', DEFAULT_PRIORITY)

    @property
    def last_run_at(self):
        return self.model.get('last_run_at')

    @last_run_at.setter
    def last_run_at(self, value):
        self.model['last_run_at'] = value

    @property
    def total_run_count(self):
        return self.model.get('total_run_count')

    @total_run_count.setter
    def total_run_count(self, value):
        self.model['total_run_count'] = value

    @property
    def last_updated(self):
        return self.model.get('last_updated')

    @last_updated.setter
    def last_updated(self, value):
        self.model['last_updated'] = value

    def is_due(self):
        if not self.enabled:
            # 5 second delay for re-enable.
            return schedules.schedstate(False, DEFAULT_MAX_INTERVAL)
        if self.once and self.enabled and self.total_run_count > 0:
            # Don't recheck
            return schedules.schedstate(False, None)
        return self.schedule.is_due(self.last_run_at)

    def update(self, other):
        super(TEntry, self).update(other)
        self.last_updated = self.default_now()

    def __next__(self):
        self.last_run_at = self.default_now()
        self.total_run_count += 1
        return self.__class__(self.model, self.app)
    next = __next__  # for 2to3


class TScheduler(Scheduler):
    def __init__(self, *args, **kwargs):
        """Initialize the scheduler."""
        super(TScheduler, self).__init__(*args, **kwargs)
        self._init_schedules = True
        self._last_updated = None
        self.max_interval = (
            kwargs.get('max_interval')
            or self.app.conf.beat_max_loop_interval
            or DEFAULT_MAX_INTERVAL)

    def setup_schedule(self):
        self.install_default_entries(self.data)
        self.update_from_dict(self.app.conf.beat_schedule)

    def install_default_entries(self, data):
        entries = {}
        if self.app.conf.result_expires and \
                not self.app.backend.supports_autoexpire:
            if 'celery.backend_cleanup' not in data:
                entries['celery.backend_cleanup'] = {
                    'task': 'celery.backend_cleanup',
                    'schedule': schedules.crontab('0', '4', '*'),
                    'options': {'expires': 12 * 3600}}
        self.update_from_dict(entries)

    def update_from_dict(self, mapping):
        s = {}
        for name, entry_fields in mapping.items():
            entry_model = entry_fields.copy()
            entry_model['name'] = name
            entry = TEntry(entry_model,
                           app=self.app)
            if entry.enabled:
                s[name] = entry
        self.data.update(s)

    def schedule_changed(self):
        # 可以通过记录self._last_updated与获取定时任务列表的last_updated进行对比
        # 比如：rpc_call(count_changed, self._last_updated) > 0
        return False

    def all_schedules(self):
        # all_schedules仅限用户自定义的所有schedules
        # beat的所有schedules = default_schedules + conf_schedules + all_schedules的字典
        return {}

    @property
    def schedule(self):
        update = False
        if self._init_schedules:
            self._init_schedules = False
            update = True
        if not update and self.schedule_changed():
            update = True
        if update:
            last_updated = self._last_updated
            all_schedules = self.all_schedules()
            new_entries = {}
            for n, s in all_schedules.items():
                s = s.copy()
                s['name'] = n
                entry = TEntry(s)
                new_entries[n] = entry
                if last_updated is None and entry.last_updated is not None:
                    last_updated = entry.last_updated
                elif entry.last_updated and entry.last_updated > last_updated:
                    last_updated = entry.last_updated
            self.data = new_entries
            self.install_default_entries(self.data)
            self.update_from_dict(self.app.conf.beat_schedule)
            self._last_updated = last_updated
            # the schedule changed, invalidate the heap in Scheduler.tick
            self._heap = []
        return self.data

    @schedule.setter
    def schedule(self, value):
        self.data = value
