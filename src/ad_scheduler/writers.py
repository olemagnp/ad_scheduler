from json.decoder import JSONDecodeError
from .entities import EntityGroup
from typing import Dict, Optional, TextIO, Iterable
import json
from .schedule import Schedule, Entry
import logging

logger = logging.getLogger(__name__)


class ScheduleWriter:
    @classmethod
    def write_schedule(cls, fp: TextIO, schedule: Schedule):
        d = cls.schedule_to_dict(schedule)

        json.dump(d, fp)

    @classmethod
    def schedule_to_dict(cls, schedule):
        return {
            "kind": schedule.kind,
            "name": schedule.name,
            "entries": [cls.entry_to_dict(e) for e in schedule.entries],
        }

    @classmethod
    def entry_to_dict(cls, entry: Entry) -> Dict:
        return {
            "value": entry.value,
            "hour": entry.hour,
            "minute": entry.minute,
            "days": entry.days,
        }

    @classmethod
    def entry_from_dict(cls, d: Dict) -> Entry:
        return Entry(d["value"], d["hour"], d["minute"], d["days"])

    @classmethod
    def read_schedule(cls, fp: TextIO, scheduler) -> Schedule:
        d = json.load(fp)
        sched = Schedule(d["name"], d["kind"], scheduler)

        for e in d["entries"]:
            sched.add_entry(cls.entry_to_dict(e))
        return sched


class GroupsWriter:
    @classmethod
    def write_groups(cls, fp: TextIO, groups: Iterable[EntityGroup]):
        data = [cls.group_to_dict(g) for g in groups]

        json.dump(data, fp)

    @classmethod
    def group_to_dict(cls, group: EntityGroup):
        return {
            "name": group.name,
            "kind": group.kind,
            "active": group.active,
            "schedule_name": group.schedule.name
            if group.schedule is not None
            else None,
            "entities": list(group.entities),
        }

    @classmethod
    def read_groups(cls, fp: TextIO, schedules: Optional[Dict[str, Schedule]] = None):

        try:
            data = json.load(fp)
        except JSONDecodeError as e:
            logger.warning("Failed to read groups from file:", e)
            return [], []
        groups = []
        schedule_names = []
        for g in data:
            group = EntityGroup(g["name"], g["kind"], *g["entities"])
            groups.append(group)
            sched = g["schedule_name"]
            schedule_names.append(sched)
            if sched is not None and schedules is not None:
                try:
                    group.assign_schedule(schedules[sched])
                except KeyError:
                    logger.warning(f"Schedule not found when reading: {sched}")

        return groups, schedule_names
