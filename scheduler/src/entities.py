from .const import EntityKind
from .dependencies import ha_session
import asyncio


class Entity:
    def __init__(self, entity_id: str, kind: str):
        self.id = entity_id
        if kind not in EntityKind.__all__:
            raise ValueError(f"Illegal entity kind: {kind}")

        self.kind = kind

    async def set(self, value):
        return ha_session.post(f"states/{self.entity_id}", data={"state": value})

class ThermostatEntity(Entity):
    def __init__(self, entity_id: str):
        super().__init__(entity_id, EntityKind.THERMO)


class EntityGroup:
    def __init__(self, name: str, kind: str):
        self.name = name
        if kind not in EntityKind.__all__:
            raise ValueError(f"Illegal group kind: {kind}")
        self.kind = kind
        self.entities = []
        self.active = True
        self.schedule = None

    def add_entity(self, entity: Entity):
        if entity.kind != self.kind:
            raise ValueError(f"Entity kind does not match group kind. Expected {self.kind}, got {entity.kind}")
        self.entities.append(entity)

        if self.active and self.schedule is not None:
            entity.set(self.schedule.current)

    def schedule_changed(self, new_value):
        if not self.active:
            return
        tasks = []
        for entity in self.entities:
            tasks.append(asyncio.ensure_future(entity.set(new_value)))

        await asyncio.gather(*tasks)