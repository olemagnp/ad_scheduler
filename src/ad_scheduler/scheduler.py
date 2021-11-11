from .schedule import Entry, Schedule
from .entities import EntityGroup
from typing import Dict

import appdaemon.plugins.hass.hassapi as hass

from pathlib import Path, PurePosixPath

from .writers import GroupsWriter, ScheduleWriter


class Scheduler(hass.Hass):
    def initialize(self):
        self.root: Path = Path(self.args["root_dir"])
        self.root.mkdir(parents=True, exist_ok=True)

        # Read all existing schedules
        schedule_dir: Path = self.root.joinpath("schedules")
        self.schedules: Dict[str, Schedule] = {}

        if schedule_dir.exists():
            all_scheds = schedule_dir.glob("*.json")
            for sched_path in all_scheds:
                with open(sched_path, "r") as f:
                    sched = ScheduleWriter.read_schedule(f, self)
                    if sched.name in self.schedules:
                        raise ValueError(
                            f"Schedule with duplicate name found: {sched.name}"
                        )
                    self.schedules[sched.name] = sched
        else:
            schedule_dir.mkdir()

        # Read all entity groups
        self.groups: Dict[str, EntityGroup] = {}

        group_path = self.root.joinpath("groups.json")
        if group_path.exists():
            with open(group_path, "r") as f:
                groups, schedule_names = GroupsWriter.read_groups(
                    f, self, self.schedules
                )

                self.groups = {g.name: g for g in groups}

        def build_endpoint(*parts):
            return "_".join([self.name, *parts])

        self.register_endpoint(self.add_entity_group, build_endpoint("groups", "add"))
        self.register_endpoint(self.edit_entity_group, build_endpoint("groups", "edit"))
        self.register_endpoint(
            self.remove_entity_group, build_endpoint("groups", "delete")
        )
        self.register_endpoint(
            self.activate_group, build_endpoint("groups", "activate")
        )
        self.register_endpoint(
            self.deactivate_group, build_endpoint("groups", "deactivate")
        )
        self.register_endpoint(self.assign_schedule, build_endpoint("groups", "assign"))

        self.register_endpoint(self.add_schedule, build_endpoint("schedules", "add"))
        self.register_endpoint(self.edit_schedule, build_endpoint("schedules", "edit"))
        self.register_endpoint(
            self.remove_schedule, build_endpoint("schedules", "delete")
        )

        self.register_endpoint(self.add_entry, build_endpoint("entries", "add"))
        self.register_endpoint(self.edit_entry, build_endpoint("entries", "edit"))
        self.register_endpoint(self.remove_entry, build_endpoint("entries", "delete"))

        self.set_own_state()

    def set_own_state(self):
        state = {}

        def map_entry(entry: Entry):
            return {
                "hour": entry.hour,
                "minute": entry.minute,
                "days": entry.days,
                "value": entry.value,
                "attrs": entry.additional_attrs,
            }

        def map_schedule(schedule: Schedule):
            return {
                "name": schedule.name,
                "kind": schedule.kind,
                "current_entry": map_entry(schedule.current_entry)
                if schedule.current_entry is not None
                else None,
                "next_entry": map_entry(schedule.next_entry)
                if schedule.next_entry is not None
                else None,
                "entries": [map_entry(e) for e in schedule.entries],
                "subscribers": [sub.name for sub in schedule.subscribers],
            }

        def map_group(group: EntityGroup):
            return {
                "name": group.name,
                "kind": group.kind,
                "entities": list(group.entities),
                "active": group.active,
                "schedule": group.schedule.name if group.schedule is not None else None,
            }

        state["schedules"] = [map_schedule(s) for s in self.schedules.values()]
        state["groups"] = [map_group(g) for g in self.groups.values()]

        self.set_state(f"sensor.scheduler_{self.name}", state="on", attributes=state)

    def store_groups(self):
        with open(self.root.joinpath("groups.json"), "w") as f:
            GroupsWriter.write_groups(f, self.groups.values())

    def store_schedule(self, schedule: Schedule):
        with open(self.root.joinpath("schedules", f"{schedule.name}.json"), "w") as f:
            ScheduleWriter.write_schedule(f, schedule)

    def add_entity_group(self, request: Dict):
        name = request["name"]
        if name in self.groups:
            return f"Group with name {name} already exists", 403

        entities = request.get("entities", [])
        eg = EntityGroup(request["name"], request["kind"], self, *entities)
        self.groups[name] = eg
        self.store_groups()
        self.set_own_state()
        return GroupsWriter.group_to_dict(eg), 200

    def edit_entity_group(self, request: Dict):
        name = request["name"]
        if name not in self.groups:
            return f"Group not found: {name}", 403

        if "new_name" in request:
            new_name = request["new_name"]
            if new_name in self.groups:
                return f"Group with name {new_name} already exists", 403

            self.groups[new_name] = self.groups[name]
            self.groups[new_name].name = new_name
            del self.groups[name]
            name = new_name

        group = self.groups[name]
        group.kind = request.get("kind", group.kind)

        if "entities" in request:
            group.set_entities(request["entities"])

        self.store_groups()
        self.set_own_state()
        return GroupsWriter.group_to_dict(group), 200

    def remove_entity_group(self, request: Dict):
        name = request["name"]
        if name not in self.groups:
            return f"Group not found: {name}", 403

        group = self.groups[name]
        group.remove_schedule()

        del self.groups[name]

        self.store_groups()
        self.set_own_state()

        return {"msg": f"Group {name} removed"}, 200

    def activate_group(self, request: Dict):
        name = request["name"]
        if name not in self.groups:
            return f"Group not found: {name}", 403

        self.groups[name].activate()

        self.store_groups()
        self.set_own_state()

        return GroupsWriter.group_to_dict(self.groups[name]), 200

    def deactivate_group(self, request: Dict):
        name = request["name"]
        if name not in self.groups:
            return f"Group not found: {name}", 403

        group = self.groups[name]

        group.deactivate_for(request.get("delay", None))

        self.store_groups()
        self.set_own_state()

        return GroupsWriter.group_to_dict(group), 200

    def assign_schedule(self, request: Dict):
        groupname = request["group"]
        schedulename = request["schedule"]

        if groupname not in self.groups:
            return f"Group not found: {groupname}", 403

        if schedulename == "":
            self.groups[groupname].remove_schedule()
            self.store_groups()
            self.set_own_state()
            return "", 200

        if schedulename not in self.groups:
            return f"Schedule not found: {schedulename}", 403

        self.groups[groupname].assign_schedule(self.schedules[schedulename])

        self.store_groups()
        self.set_own_state()

        return "", 200

    def add_schedule(self, request: Dict):
        name = request["name"]
        if name in self.schedules:
            return f"Schedule already exists: {name}", 403

        sched = Schedule(name, request["kind"], self)
        self.schedules[name] = sched

        self.store_schedule(sched)
        self.set_own_state()

        sched.subscribers.append(self)
        return ScheduleWriter.schedule_to_dict(sched), 200

    def schedule_changed(self, entry: Entry):
        self.set_own_state()

    def edit_schedule(self, request: Dict):
        name = request["name"]
        if name not in self.schedules:
            return f"Schedule not found: {name}", 403

        if "new_name" in request:
            new_name = request["new_name"]
            if new_name in self.schedules:
                return f"Schedule with name {new_name} already exists", 403

            self.schedules[new_name] = self.schedules[name]
            del self.schedules[name]
            self.schedules[new_name].name = new_name

            p = self.root.joinpath("schedules", f"{name}.json")
            if p.exists():
                p.unlink()
            name = new_name

        schedule = self.schedules[name]
        schedule.kind = request.get("kind", schedule.kind)

        self.store_schedule(schedule)
        self.set_own_state()
        return ScheduleWriter.schedule_to_dict(schedule), 200

    def remove_schedule(self, request: Dict):
        name = request["name"]
        if name not in self.schedules:
            return f"Schedule not found: {name}", 403

        del self.schedules[name]
        p = self.root.joinpath("schedules", f"{name}.json")
        if p.exists():
            p.unlink()

        self.set_own_state()
        return {"msg": f"Schedule {name} removed"}, 200

    def add_entry(self, request: Dict):
        schedulename = request["schedule"]

        if schedulename not in self.schedules:
            return f"Schedule not found: {schedulename}", 403
        schedule = self.schedules[schedulename]

        value = request["value"]
        hour = request["hour"]
        minute = request["minute"]
        days = request.get("days", "daily")
        attrs = request.get("attrs", {})

        entry = Entry(value, hour, minute, days, attrs)

        try:
            schedule.add_entry(entry)
        except ValueError:
            return "Entry collides with existing entry", 403

        self.store_schedule(schedule)
        self.set_own_state()
        return ScheduleWriter.schedule_to_dict(schedule), 200

    def edit_entry(self, request: Dict):
        schedulename = request["schedule"]

        if schedulename not in self.schedules:
            return f"Schedule not found: {schedulename}", 403
        schedule = self.schedules[schedulename]

        hour = request["hour"]
        minute = request["minute"]
        days = request.get("days", "daily")
        entry = schedule.get_entry(hour, minute, days)
        if entry is None:
            return "No entry with given spec found", 403

        new_hour = request.get("new_hour", entry.hour)
        new_minute = request.get("new_minute", entry.minute)
        new_days = request.get("new_days", entry.days)
        new_value = request.get("new_value", entry.value)
        new_attrs = request.get("new_attrs", entry.attrs)

        new_entry = Entry(new_value, new_hour, new_minute, new_days, new_attrs)

        schedule.entries.remove(entry)
        schedule.add_entry(new_entry)

        self.store_schedule(schedule)
        self.set_own_state()

        return ScheduleWriter.schedule_to_dict(schedule), 200

    def remove_entry(self, request: Dict):
        schedulename = request["schedule"]

        if schedulename not in self.schedules:
            return f"Schedule not found: {schedulename}", 403
        schedule = self.schedules[schedulename]

        hour = request["hour"]
        minute = request["minute"]
        days = request.get("days", "daily")
        entry = schedule.get_entry(hour, minute, days)
        if entry is None:
            return "No entry with given spec found", 403

        schedule.entries.remove(entry)
        schedule.trigger()

        self.store_schedule(schedule)
        self.set_own_state()

        return ScheduleWriter.schedule_to_dict(schedule), 200
