from src.schedule import Entry
import pytest
from pytest_mock import mocker

from src.entities import EntityGroup
from src.const import EntityKind


@pytest.fixture
def entry():
    return Entry(42, 10, 0, additional_attrs={"some_attr": "some_attr_value"})


@pytest.fixture
def schedule(mocker, entry):
    mock = mocker.Mock()
    mock.current_entry = entry
    return mock


@pytest.mark.parametrize(
    "name,kind,entities",
    [
        ("MyName", EntityKind.THERMO, []),
        (
            "NameWith Weird Charsæø'¨k123",
            EntityKind.ON_OFF,
            ["light.my_light", "switch.on_off"],
        ),
    ],
)
def test_initializer(name, kind, entities):
    g = EntityGroup(name, kind, *entities)

    assert g.name == name, f"Name not set correctly, expected {name}, got {g.name}"
    assert g.kind == kind, f"Kind not set correctly, expected {kind}, got {g.kind}"
    assert g.entities == set(
        entities
    ), f"Entities not set correctly, expected {set(entities)}, got {g.entities}"


def test_initializer_illegal_kind_raises():
    with pytest.raises(ValueError):
        EntityGroup("SomeName", "IncorrectGroupKind")


def test_set_entity_calls_scheduler(schedule, entry):
    entity = "light.my_light"

    eg = EntityGroup("SomeName", EntityKind.ON_OFF, entity)
    eg.schedule = schedule

    eg.set_entity(entity, entry)
    schedule.scheduler.set_state.assert_called_once_with(
        entity, state=entry.value, attributes=entry.additional_attrs
    )


def test_add_entity_with_new_entity(mocker, schedule, entry):
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF)

    mocker.patch.object(eg, "set_entity")
    eg.schedule = schedule

    entity = "light.new_light"

    eg.add_entity(entity)
    assert eg.entities == {entity}, "Entity not added to eg.entites"
    eg.set_entity.assert_called_with(entity, entry)

    entity_two = "light.another_new_light"

    eg.add_entity(entity_two)

    assert eg.entities == {entity, entity_two}, "Entity two not added to eg.entities"
    eg.set_entity.assert_called_with(entity_two, entry)


def test_add_entity_with_same_entity_does_nothing(mocker, schedule):
    entity = "light.new_light"

    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, entity)

    mocker.patch.object(eg, "set_entity")
    eg.schedule = schedule

    eg.add_entity(entity)
    assert eg.entities == {entity}, "Entity should not be added to eg.entities"
    eg.set_entity.assert_not_called()


def test_remove_entity_existing():
    entity1 = "light.new_light"
    entity2 = "light.other_light"

    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, entity1, entity2)

    assert {entity1, entity2} == eg.entities

    eg.remove_entity(entity1)

    assert {entity2} == eg.entities

    eg.remove_entity(entity2)
    assert set() == eg.entities


def test_remove_entity_non_existing():
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, "light.some_light")

    with pytest.raises(KeyError):
        eg.remove_entity("light.non_existing")


def test_schedule_changed_sets_all_entities(mocker, entry):
    entities = ["light.light1", "light.light2", "light.light3", "light.light4"]
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, *entities)

    mocker.patch.object(eg, "set_entity")

    eg.schedule_changed(entry)

    eg.set_entity.assert_has_calls(
        [mocker.call(e, entry) for e in entities], any_order=True
    )


def test_schedule_changed_inactive_does_nothing(mocker, entry):
    entities = ["light.light1", "light.light2", "light.light3", "light.light4"]
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, *entities)
    eg.active = False

    mocker.patch.object(eg, "set_entity")

    eg.schedule_changed(entry)
    eg.set_entity.assert_not_called()


def test_remove_schedule_also_removes_group_from_subscribers(schedule):
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF)
    eg2 = EntityGroup("OtherGroup", EntityKind.ON_OFF)
    schedule.subscribers = [eg, eg2]
    eg.schedule = schedule

    eg.remove_schedule()

    assert eg.schedule is None, "Schedule was not removed"
    assert schedule.subscribers == [
        eg2
    ], "Group was not removed from schedules subscribers"


def test_remove_schedule_without_schedule_does_nothing(schedule):
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF)

    eg.remove_schedule()

    assert eg.schedule is None, "Schedule is not None"


def test_assign_schedule_wrong_type_raises(schedule):
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF)

    schedule.kind = EntityKind.THERMO
    schedule.subscribers = []

    with pytest.raises(ValueError):
        eg.assign_schedule(schedule)

    assert eg.schedule is None
    assert schedule.subscribers == []


def test_assign_does_everything(mocker, schedule, entry):
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF)

    schedule.kind = EntityKind.ON_OFF
    schedule.subscribers = []

    mocker.patch.object(eg, "remove_schedule")
    mocker.patch.object(eg, "schedule_changed")

    eg.assign_schedule(schedule)

    assert schedule == eg.schedule
    eg.remove_schedule.assert_called_once()
    eg.schedule_changed.assert_called_once_with(entry)
    assert schedule.subscribers == [eg]
