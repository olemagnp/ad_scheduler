from typing import Any, List, Union

import datetime
import json

from .const import EntityKind, Days


def dt_now() -> datetime.datetime:
    return datetime.now()


class Entry:
    def __init__(self, value: Any, hour, minute=0, days="daily"):
        self.value = value

        self.hour = hour
        self.minute = minute
        self.time = datetime.time(hour=hour, minute=minute)
        if days == "daily":
            self.days = list(Days.__all__)
        else:
            if not isinstance(days, list) or not all([x in Days.__all__ for x in days]):
                raise ValueError(
                    "Days must be either the string 'daily' or a list of day strings (e.g. 'mon', 'tue', etc."
                )
            self.days = days

        self.__next_datetime = None

    @staticmethod
    def from_dict(d):
        return Entry(d["value"], d["hour"], d["minute"], d["days"])

    def same_time(self, other: "Entry"):
        return (
            self.hour == other.hour
            and self.minute == other.minute
            and self.days == other.days
        )

    def as_dict(self):
        return {
            "value": self.value,
            "hour": self.hour,
            "minute": self.minute,
            "days": self.days,
        }

    def json(self):
        return json.dumps(self.as_dict())

    @property
    def next_datetime(self):
        now = dt_now()
        if self.__next_datetime is None or self.__next_datetime < now:
            cur_day = now.weekday()
            diff = [Days.__all__.index(d) - cur_day for d in self.days]
            if self.time > now.time():
                targ = 0
            else:
                targ = 1

            best_diff = float("inf")
            for d in diff:
                if d < targ:
                    d += 7
                elif d == targ:
                    best_diff = d
                    break
                if d < best_diff:
                    best_diff = d
            self.__next_datetime = now.replace(
                hour=self.hour, minute=self.minute
            ) + datetime.timedelta(days=best_diff)
        return self.__next_datetime


class Schedule:
    def __init__(self, name: str, kind: str):
        if kind not in EntityKind.__all__:
            raise ValueError("Unknown schedule kind")
        self.kind = kind
        self.name = name
        self.entries = []
        self.subscribers = []
        self.current_entry = None

    def as_dict(self):
        return {
            "kind": self.kind,
            "name": self.name,
            "entries": [e.as_dict() for e in self.entries],
        }

    def json(self):
        return json.dumps(self.as_dict())

    @staticmethod
    def from_dict(self, d):
        sched = Schedule(d["name"], d["kind"])
        for entry in d["entries"]:
            sched.add_entry(Entry.from_dict(entry))

    def value_updated(self):
        for sub in self.subscribers:
            sub.schedule_changed(self.current_entry.value)

    def add_entry(self, entry: Entry):
        if any([e.same_time(entry) for e in self.entries]):
            raise ValueError(
                "Trying to add a new entry that collides with an existing one."
            )

    def find_next(self):
        now = dt_now()
        tmp_entries = list(self.entries)
        if self.current_entry is not None:
            tmp_entries.remove(self.current_entry)
        next_entry = min(tmp_entries, key=lambda e: e.next_datetime - now)
        self.current_entry = next_entry

    def trigger(self):
        self.value_updated()
        self.find_next()

        # TODO Set new trigger for next
