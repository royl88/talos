# coding=utf-8

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
    max_calls: None/1/4000,
    max_instances： 相同任务最大并发数
    last_updated: ..., 
}

"""

from __future__ import absolute_import

from collections import namedtuple
import copy
from datetime import timedelta
import heapq
import numbers

from celery import schedules
from celery.beat import ScheduleEntry, Scheduler
import six
from talos.core.i18n import _


event_t = namedtuple('event_t', ('time', 'priority', 'entry'))

DEFAULT_MAX_INTERVAL = 5
DEFAULT_PRIORITY = 5


def maybe_schedule(s, relative=False, app=None):
    schedule_type = s.get('type', 'interval')
    schedule = s.get('schedule', None)
    if isinstance(schedule, (six.string_types, numbers.Number)):
        if schedule_type.upper() == 'INTERVAL':
            schedule = schedules.schedule(
                timedelta(seconds=float(schedule)),
                app=app
            )
        elif schedule_type.upper() == 'CRONTAB':
            fields = schedule.split()
            schedule = schedules.crontab(*fields, app=app)
        else:
            raise RuntimeError(_('can not parse schedule of type: %(type)s') % {'type': s.get('type', 'undefinded')})
    else:
        if schedule:
            schedule.app = app
    return schedule


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

    @property
    def enabled(self):
        return self.model.setdefault('enabled', True)

    @property
    def max_calls(self):
        return self.model.setdefault('max_calls', None)

    @property
    def priority(self):
        return self.model.setdefault('priority', DEFAULT_PRIORITY)

    @property
    def max_instances(self):
        return self.model.setdefault('max_instances', 1)

    @property
    def last_run_at(self):
        return self.model.setdefault('last_run_at', self.default_now())

    @last_run_at.setter
    def last_run_at(self, value):
        self.model['last_run_at'] = value

    @property
    def total_run_count(self):
        return self.model.setdefault('total_run_count', 0)

    @total_run_count.setter
    def total_run_count(self, value):
        self.model['total_run_count'] = value

    @property
    def last_updated(self):
        return self.model.setdefault('last_updated', self.default_now())

    @last_updated.setter
    def last_updated(self, value):
        self.model['last_updated'] = value

    def is_due(self):
        if not self.enabled:
            # enabled直接跳过
            return schedules.schedstate(False, None)
        if self.enabled and self.max_calls is not None and self.total_run_count >= self.max_calls:
            # 启用但任务已超过最大调用次数
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

    def populate_heap(self, event_t=event_t, heapify=heapq.heapify):
        """Populate the heap with the data contained in the schedule."""
        self._heap = []
        for entry in self.schedule.values():
            is_due, next_call_delay = entry.is_due()
            # 如果不需要再次出现在heap中，因为永远延期调度
            if next_call_delay is not None:
                self._heap.append(event_t(
                    self._when(
                        entry,
                        0 if is_due else next_call_delay
                    ) or 0,
                    entry.priority, entry
                ))
        heapify(self._heap)

    # pylint disable=redefined-outer-name
    def tick(self, event_t=event_t, min=min, heappop=heapq.heappop,
             heappush=heapq.heappush):
        """Run a tick - one iteration of the scheduler.

        Executes one due task per call.

        Returns:
            float: preferred delay in seconds for next call.
        """
        adjust = self.adjust
        max_interval = self.max_interval

        if (self._heap is None or
                not self.schedules_equal(self.old_schedulers, self.schedule)):
            self.old_schedulers = copy.copy(self.schedule)
            self.populate_heap()

        H = self._heap

        if not H:
            return max_interval

        event = H[0]
        entry = event[2]
        is_due, next_time_to_run = self.is_due(entry)
        if is_due:
            verify = heappop(H)
            if verify is event:
                next_entry = self.reserve(entry)
                self.apply_entry(entry, producer=self.producer)
                heappush(H, event_t(self._when(next_entry, next_time_to_run),
                                    event[1], next_entry))
                return 0
            else:
                heappush(H, verify)
                return min(verify[0], max_interval)
        else:
            # 此任务已经永远无法被调度到，直接从heap中移除
            if next_time_to_run is None:
                heappop(H)
        return min(adjust(next_time_to_run) or max_interval, max_interval)

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
        # TODO: 增加hooks
        return False

    def all_schedules(self):
        # all_schedules仅限用户自定义的所有schedules
        # beat的所有schedules = default_schedules + conf_schedules + all_schedules的字典
        # TODO: 增加hooks
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
            # TODO: 如果因为一个简单修改而导致数据全部重新载入，会导致已运行的任务信息丢失
            # 比如：原max_calls=3的任务，因为重载而导致了total_run_count被重置，任务会重新运行
            # 这并不是我们希望的结果，需要修复，不能导致total_run_count和last_run_at被重置
            # the schedule changed, invalidate the heap in Scheduler.tick
            self._heap = []
        return self.data

    @schedule.setter
    def schedule(self, value):
        self.data = value
