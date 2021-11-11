from typing import Any, Dict, List, Optional, Union

import datetime
import json

from .const import EntityKind, Days


def dt_now() -> datetime.datetime:
    return datetime.datetime.now()


class Entry:
    """
    Entry class that contains information about a single step in a schedule.

    Note that an entry only contains a start time and a value. The end time
    is when the next entry in the schedule starts.

    Attributes:
        value (Any): A value that can be set as state argument to hass.set_state
        additional_attrs (Dict): Extra attrs to pass in the dict given to hass.set_state
        hour (int): The hour of the start time
        minute (int): The minute of the starttime
        time (datetime.time): A :code:`time`-variable representing the time given by
            :code:`hour` and :code:`minute`
        days (List[int]): A list containing the days of the week this entry is valid
        next_datetime (datetime.datetime): The next datetime this entry should trigger
    """

    def __init__(
        self,
        value: Any,
        hour,
        minute=0,
        days="daily",
        additional_attrs: Optional[Any] = None,
    ):
        """Sets the fields of the entry, as well as validating the given days"""
        self.value = value
        self.additional_attrs = additional_attrs

        self.hour = hour
        self.minute = minute
        self.time = datetime.time(hour=hour, minute=minute)
        if days == "daily":
            self.days = list(map(lambda d: Days.to_int(d), Days.__all__))
        else:
            if not isinstance(days, list):
                raise ValueError(
                    "Days must be either the string 'daily' or a list of day strings (e.g. 'mon', 'tue', etc., or a list of ints."
                )
            if isinstance(days[0], int):
                if not all([isinstance(x, int) and 0 <= x <= 6 for x in days]):
                    raise ValueError(
                        "If days contains ints, all elements must be ints in the range [0, 6]."
                    )
            else:
                if not all([x in Days.__all__ for x in days]):
                    raise ValueError(
                        "If days contains string, all elements must be day strings, e.g. 'mon', 'tue'."
                    )
                days = list(map(lambda d: Days.to_int(d), days))

            self.days = list(set(days))  # Remove duplicates

        self.__next_datetime = None
        self.__prev_datetime = None

    def __str__(self):
        return f"Entry [hour={self.hour}, minute={self.minute}, value={self.value}, attrs={self.additional_attrs}, days={self.days}]"

    def __repr__(self):
        return f"'{str(self)}'"

    def same_time(self, other: "Entry"):
        """Check if two entries trigger at the same time"""
        return (
            self.hour == other.hour
            and self.minute == other.minute
            and any([d in other.days for d in self.days])
        )

    @property
    def next_datetime(self):
        """Find the next date and time when this entry triggers"""
        now = dt_now()
        if self.__next_datetime is None or self.__next_datetime < now:
            cur_day = now.weekday()
            diff = [d - cur_day for d in self.days]
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

    @property
    def previous_datetime(self):
        now = dt_now()
        cur_day = now.weekday()
        diff = [cur_day - d for d in self.days]

        if self.time < now.time():
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
        self.__prev_datetime = now.replace(
            hour=self.hour, minute=self.minute
        ) + datetime.timedelta(days=-best_diff)

        return self.__prev_datetime


class Schedule:
    """
    A schedule for controlling a single type of devices.

    The schedule contains a list of :class:`Entry`-objects, as well as a list of
    subscribers that change with this schedule.

    Attributes:
        kind (str): The kind of devices this schedule controls. Should be one of the
            values defined in :class:`EntityKind`
        name (str): The name of the schedule.
        entries (List[Entry]): List of entries in this schedule
        subscribers (List[src.entities.EntityGroup]): Subscribers listening to this
            schedule
        current_entry (Entry): The currently active entry, used to set device states on
            restart or when adding them.
        next_entry (Entry): The next entry that will be activated, used when the update
            is triggered.
        scheduler (scheduler.Scheduler): The scheduler that runs the actual schedule
    """

    def __init__(self, name: str, kind: str, scheduler: "Scheduler"):
        if kind not in EntityKind.__all__:
            raise ValueError("Unknown schedule kind")
        self.kind: str = kind
        self.name: str = name
        self.entries: List[Entry] = []
        self.subscribers: List["EntityGroup"] = []
        self.current_entry: Optional[Entry] = None
        self.next_entry: Optional[Entry] = None
        self.next_trigger: object = None
        self.scheduler: "Scheduler" = scheduler

    def cancel(self):
        """Cancel the current trigger if it is set"""
        if self.next_trigger is not None:
            self.scheduler.cancel_timer(self.next_trigger)
            self.next_trigger = None

    def get_entry(self, hour, minute, days):
        tmp_entry = Entry(0, hour, minute, days)

        first = filter(lambda e: tmp_entry.same_time(e), self.entries)
        if first:
            return next(first)
        return None

    def add_entry(self, entry: Entry):
        """Add a new trigger, update the state, and if the current entry has changed, update subscribers"""
        if any([e.same_time(entry) for e in self.entries]):
            raise ValueError(
                "Trying to add a new entry that collides with an existing one."
            )
        self.entries.append(entry)
        cur_entry = self.current_entry
        self.update_state()
        if self.current_entry != cur_entry:
            self.set_subscribers(self.current_entry)

    def set_subscribers(self, entry):
        """Set the state of all subscribers based on entry"""
        for sub in self.subscribers:
            sub.schedule_changed(entry)

    def update_state(self):
        """
        Update the state of the schedule.

        This cancels the current trigger (if active), finds the current and next entries,
        and sets up a trigger for the next.
        """
        self.cancel()
        if not self.entries:
            self.current_entry = None
            self.next_entry = None
            self.next_trigger = None
            return

        now = dt_now()
        tmp_entries = list(self.entries)

        self.next_entry = min(tmp_entries, key=lambda e: e.next_datetime - now)
        self.current_entry = min(tmp_entries, key=lambda e: now - e.previous_datetime)
        self.next_trigger = self.scheduler.run_at(
            self.trigger, self.next_entry.next_datetime
        )

    def trigger(self, kwargs):
        """Trigger callback"""
        self.update_state()
        self.set_subscribers(self.current_entry)
