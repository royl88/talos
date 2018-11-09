# coding=utf-8

from __future__ import absolute_import

"""
scheduler需要的数据字段
{
    id: ..., 
    name: ..., 
    description: ...
    type: interval/crontab, 
    interval: 可以是 '5.1' 或者 '*/1 * * * *' , 
    args:
    kwargs:
    priority: 优先级
    expires: 当任务产生后，多久还没被执行就认为超时
    enabled: True/False, 
    last_updated: ..., 
}

"""

from celery import schedules
from celery.beat import ScheduleEntry, Scheduler


DEFAULT_MAX_INTERVAL = 5


class DatabaseScheduler(Scheduler):
    def __init__(self, *args, **kwargs):
        """Initialize the database scheduler."""
        self._dirty = set()
        Scheduler.__init__(self, *args, **kwargs)
        self.max_interval = (
            kwargs.get('max_interval')
            or self.app.conf.beat_max_loop_interval
            or DEFAULT_MAX_INTERVAL)

    def setup_schedule(self):
        self.install_default_entries(self.schedule)
        self.update_from_dict(self.app.conf.beat_schedule)

    def all_as_schedule(self):
        s = {}
        # 从指定地方获取到所有的定时任务列表
        # for model in self.Model.objects.enabled():
        #     try:
        #         s[model.name] = ScheduleEntry(model, app=self.app)
        #     except ValueError:
        #         pass
        return s

    def schedule_changed(self):
        # 可以通过记录self._last_updated与获取定时任务列表的last_updated进行对比
        return False

    def reserve(self, entry):
        new_entry = next(entry)
        # Need to store entry by name, because the entry may change
        # in the mean time.
        self._dirty.add(new_entry.name)
        return new_entry

    def sync(self):
        # 如果定时任务信息被用户动态修改了，此处是否需要同步保存到源去
        _tried = set()
        _failed = set()
        try:
            while self._dirty:
                name = self._dirty.pop()
                try:
                    self.schedule[name].save()
                    _tried.add(name)
                except KeyError as exc:
                    _failed.add(name)
        except Exception as exc:
            pass
        finally:
            # retry later, only for the failed ones
            self._dirty |= _failed

    def update_from_dict(self, mapping):
        s = {}
        for name, entry_fields in mapping.items():
            try:
                entry = ScheduleEntry.from_entry(name,
                                                 app=self.app,
                                                 **entry_fields)
                if entry.model.enabled:
                    s[name] = entry

            except Exception as exc:
                pass
        self.schedule.update(s)

    def install_default_entries(self, data):
        entries = {}
        if self.app.conf.result_expires:
            entries.setdefault(
                'celery.backend_cleanup', {
                    'task': 'celery.backend_cleanup',
                    'schedule': schedules.crontab('0', '4', '*'),
                    'options': {'expires': 12 * 3600},
                },
            )
        self.update_from_dict(entries)

    def schedules_equal(self, *args, **kwargs):
        if self._heap_invalidated:
            self._heap_invalidated = False
            return False
        return super(DatabaseScheduler, self).schedules_equal(*args, **kwargs)

    @property
    def schedule(self):
        initial = update = False
        if self._initial_read:
            initial = update = True
            self._initial_read = False
        elif self.schedule_changed():
            update = True

        if update:
            self.sync()
            self._schedule = self.all_as_schedule()
            # the schedule changed, invalidate the heap in Scheduler.tick
            if not initial:
                self._heap = []
                self._heap_invalidated = True
        return self._schedule
