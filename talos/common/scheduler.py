# coding=utf-8

"""
scheduler需要的数据字段
{
    name: string, 唯一名称
    task: string, 任务模块函数
    [description]: string, 备注信息
    [type]: string, interval 或 crontab, 默认 interval
    schedule: string/int/float/schedule eg. 1.0,'5.1', '10 *' , '*/10 * * * *' 
    args: tuple/list, 参数
    kwargs: dict, 命名参数
    [priority]: int, 优先级, 默认5
    [expires]: int, 单位为秒，当任务产生后，多久还没被执行会认为超时
    [enabled]: bool, True/False, 默认True
    [max_calls]: None/int, 最大调度次数, 默认None无限制
    [max_instances]： None/int, 相同任务最大并发数, 默认None无限制, 未支持
    [last_updated]: Datetime, 任务最后更新时间，常用于判断是否有定时任务需要更新，建议记录使用
}

"""

from __future__ import absolute_import

from datetime import timedelta
from collections import namedtuple
import copy
import heapq
import inspect
import logging
import numbers
import sys

from celery import schedules
from celery.beat import ScheduleEntry, Scheduler
import six
from talos.core import utils
from talos.core.i18n import _
from talos.core import config

event_t = namedtuple('event_t', ('time', 'priority', 'entry'))

DEFAULT_MAX_INTERVAL = 5
DEFAULT_PRIORITY = 5
LOG = logging.getLogger(__name__)
CONF = config.CONF


def maybe_schedule(s, relative=False, app=None):
    schedule_type = s.get('type', 'interval')
    schedule = s['schedule']
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
        self.args = model.get('args') or ()
        self.kwargs = model.get('kwargs') or {}
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
        return self.model.setdefault('max_instances', None)

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

    def editable_fields_equal(self, other):
        for attr in ('task', 'args', 'kwargs', 'options', 'schedule',
                     'enabled', 'max_calls', 'priority', 'max_instances'):
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __eq__(self, other):
        return self.editable_fields_equal(other)

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

    def __init__(self, app, *args, **kwargs):
        """Initialize the scheduler."""
        # setup_schedule 需要 _init_schedules & _last_updated, 必须先初始化这2个属性
        self._init_schedules = True
        self._last_updated = None
        self._heap_invalid = False
        self._last_schedule_changed = app.now()
        self.max_interval = kwargs.get('max_interval', 0) or app.conf.beat_max_loop_interval or DEFAULT_MAX_INTERVAL
        kwargs['max_interval'] = self.max_interval
        self. on_user_schedules_changed = self._import_hooks(utils.get_config(
            CONF, 'celery.talos_on_user_schedules_changed', []))
        self. on_user_schedules = self._import_hooks(utils.get_config(
            CONF, 'celery.talos_on_user_schedules', []))
        super(TScheduler, self).__init__(app, *args, **kwargs)

    def populate_heap(self, event_t=event_t, heapify=heapq.heapify):
        """Populate the heap with the data contained in the schedule."""
        self._heap = []
        self._heap_invalid = False
        for entry in self.data.values():
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
                return  max(0, min(verify[0], max_interval))
        else:
            # 此任务已经永远无法被调度到，直接从heap中移除, 并且马上tick计算下一个
            if next_time_to_run is None:
                heappop(H)
                if self._heap:
                    return 0
        return max(0, min(next_time_to_run or max_interval, max_interval))

    def setup_schedule(self):
        self.install_default_entries(self.data)
        self.update_from_dict(self.app.conf.beat_schedule)
        entries = self.schedules_as_entries()
        self.data.update(entries)
        if self._init_schedules:
            self._init_schedules = False

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
        now = self.app.now()
        if now - self._last_schedule_changed >= timedelta(seconds=self.max_interval):
            # 需要检测changed
            self._last_schedule_changed = now
            return self.user_schedules_changed()
        return False

    def _import_hooks(self, names):
        hooks = []
        for name in names:
            mod, func = name.split(':')
            __import__(mod)
            mod = sys.modules[mod]
            hook = getattr(mod, func)
            if hook and inspect.isclass(hook):
                hook = hook(self)
            hooks.append(hook)
        return hooks

    def user_schedules_changed(self):
        result = False
        for hook in self.on_user_schedules_changed:
            if hook(self):
                result = True
        return result

    def user_schedules(self):
        # user_schedules仅限用户自定义的所有schedules
        # beat的所有schedules = default_schedules + conf_schedules + user_schedules的字典
        result = {}
        for hook in self.on_user_schedules:
            result.update(hook(self))
        return result

    def schedules_as_entries(self):
        schedules = self.user_schedules()
        last_updated = self._last_updated
        new_entries = {}
        for n, s in schedules.items():
            s = s.copy()
            s['name'] = n
            entry = TEntry(s)
            new_entries[n] = entry
            if last_updated is None and entry.last_updated is not None:
                last_updated = entry.last_updated
            elif last_updated and entry.last_updated and entry.last_updated > last_updated:
                last_updated = entry.last_updated
        self._last_updated = last_updated
        return new_entries

    @property
    def schedule(self):
        update = False
        if self._init_schedules:
            self._init_schedules = False
            update = True
        if not update and self.schedule_changed():
            update = True
        if update:
            LOG.info('schedules changed detection: reschedule begin...')
            old_data = self.data
            self.data = {}
            self.install_default_entries(self.data)
            self.update_from_dict(self.app.conf.beat_schedule)
            entries = self.schedules_as_entries()
            self.data.update(entries)
            deleted_entries = [old_data[name] for name in list(set(old_data.keys()) - set(self.data.keys()))]
            for entry in deleted_entries:
                LOG.debug('schedule deleted: %s' % entry)
            new_entries = [self.data[name] for name in list(set(self.data.keys()) - set(old_data.keys()))]
            for entry in new_entries:
                LOG.debug('schedule add: %s' % entry)
            maybe_updated_entries = list(set(self.data.keys()) & set(old_data.keys()))
            updated_counter = 0
            for name in maybe_updated_entries:
                if self.data[name] != old_data[name]:
                    updated_counter += 1
                    LOG.debug('schedule updated: %s' % self.data[name])
                self.data[name].total_run_count = old_data[name].total_run_count
                self.data[name].last_run_at = old_data[name].last_run_at
            # 确实有定时器更新，重新计算heap
            if deleted_entries or new_entries or updated_counter:
                self._heap_invalid = True
            else:
                LOG.debug('schedule not change a bit')
            LOG.info('schedules changed detection, reschedule end...')

        return self.data

    @schedule.setter
    def schedule(self, value):
        self.data = value

    def schedules_equal(self, old_schedules, new_schedules):
        if self._heap_invalid:
            return False
        # 如果任务属性被更新了，依然not equal
        return super(TScheduler, self).schedules_equal(old_schedules, new_schedules)

    @property
    def last_updated(self):
        # 用户schedules的最后更新时间
        return self._last_updated
