from typing import Iterable, Set, Optional, Union
from datetime import datetime, timedelta

from .schedule import Entry, Schedule
from .const import EntityKind


class EntityGroup:
    """
    Group of entities that can have a schedule assigned.

    Attributes:
        kind (str): The kind of devices, one of the values defined in :class:`EntityKind`
        entities (Set[str]): List of entity_ids of the entities in the group
        active (bool): Wether or not entities should be updated on schedule triggers
        schedule (Schedule): The schedule this group is currently assigned to
    """

    def __init__(self, name: str, kind: str, scheduler: "Scheduler", *entities: str):
        if kind not in EntityKind.__all__:
            raise ValueError(f"Illegal group kind: {kind}")

        self.name = name
        self.kind: str = kind
        self.entities: Set[str] = set(entities)
        self.active: bool = True
        self.schedule: Optional[Schedule] = None
        self.activation_timer = None
        self.scheduler = scheduler

    def set_entities(self, entities: Iterable[str]):
        """
        Add entity to this group.

        If the entity is already in this group, no change is made.

        Parameters:
            entity: The entity id to add
        """
        self.entities = set(entities)
        if self.active and self.schedule is not None:
            for entity in self.entities:
                self.set_entity(entity, self.schedule.current_entry)

    def schedule_changed(self, entry: Entry):
        """
        Method to call when a schedule triggers or changes.

        Parameters:
            entry: The current entry containing the new state
        """
        if not self.active:
            return
        for entity_id in self.entities:
            self.set_entity(entity_id, entry)

    def set_entity(self, entity: str, entry: Entry):
        """
        Set the state of a single entity.

        Parameters:
            entity: The entity id to set
            entry: The entry to get the new state from
        """
        self.schedule.scheduler.set_state(
            entity, state=entry.value, attributes=entry.additional_attrs
        )

    def remove_schedule(self):
        """
        Remove this group from the subscribers of the current schedule, and set current schedule to :code:`None`
        """
        if self.schedule is not None:
            self.schedule.subscribers.remove(self)
            self.schedule = None

    def assign_schedule(self, schedule: Schedule):
        """
        Assign a new schedule to this group.

        The method first removes the current schedule, then sets the new one and adds
        itself to the subscribers of the schedule.

        Finally, all entities are set to the current state of the schedule.

        Parameters:
            schedule: The new schedule to assign
        """
        if schedule.kind != self.kind:
            raise ValueError(
                f"Incompatible schedule kind: entities are {self.kind}, schedule is {schedule.kind}"
            )
        self.remove_schedule()

        self.schedule = schedule
        self.schedule.subscribers.append(self)
        self.schedule_changed(self.schedule.current_entry)

    def deactivate_for(self, delay: Optional[Union[int, timedelta]] = None):
        self.active = False

        if delay is not None:
            if isinstance(delay, timedelta):
                delay = delay.total_seconds()
            self.activation_timer = self.scheduler.run_in(self.activate, delay)

    def activate(self, kwargs=None):
        self.active = True
        if self.schedule:
            self.schedule_changed(self.schedule.current_entry)
