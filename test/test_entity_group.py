from scheduler.schedule import Entry
import pytest
from pytest_mock import mocker

from scheduler.entities import EntityGroup
from scheduler.const import EntityKind


@pytest.fixture
def entry():
    return Entry(42, 10, 0, additional_attrs={"some_attr": "some_attr_value"})


@pytest.fixture
def scheduler(mocker):
    return mocker.Mock()


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
def test_initializer(name, kind, entities, scheduler):
    g = EntityGroup(name, kind, scheduler, *entities)

    assert g.name == name, f"Name not set correctly, expected {name}, got {g.name}"
    assert g.kind == kind, f"Kind not set correctly, expected {kind}, got {g.kind}"
    assert g.entities == set(
        entities
    ), f"Entities not set correctly, expected {set(entities)}, got {g.entities}"


def test_initializer_illegal_kind_raises(scheduler):
    with pytest.raises(ValueError):
        EntityGroup("SomeName", "IncorrectGroupKind", scheduler)


def test_set_entity_calls_scheduler(schedule, entry, scheduler):
    entity = "light.my_light"

    eg = EntityGroup("SomeName", EntityKind.ON_OFF, entity, scheduler)
    eg.schedule = schedule

    eg.set_entity(entity, entry)
    schedule.scheduler.set_state.assert_called_once_with(
        entity, state=entry.value, attributes=entry.additional_attrs
    )


def test_set_entities(mocker, schedule, scheduler):
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, scheduler)

    mocker.patch.object(eg, "set_entity")
    eg.schedule = schedule

    entities = ["light.new_light", "light.other_light", "light.new_light"]

    eg.set_entities(entities)

    assert eg.entities == {"light.new_light", "light.other_light"}
    assert eg.set_entity.call_count == 2

    eg.set_entity.reset_mock()

    entities = ["light.other_light", "switch.something_new"]
    eg.set_entities(entities)

    assert eg.entities == {"light.other_light", "switch.something_new"}
    assert eg.set_entity.call_count == 2


def test_schedule_changed_sets_all_entities(mocker, entry, scheduler):
    entities = ["light.light1", "light.light2", "light.light3", "light.light4"]
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, scheduler, *entities)

    mocker.patch.object(eg, "set_entity")

    eg.schedule_changed(entry)

    eg.set_entity.assert_has_calls(
        [mocker.call(e, entry) for e in entities], any_order=True
    )


def test_schedule_changed_inactive_does_nothing(mocker, entry, scheduler):
    entities = ["light.light1", "light.light2", "light.light3", "light.light4"]
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, scheduler, *entities)
    eg.active = False

    mocker.patch.object(eg, "set_entity")

    eg.schedule_changed(entry)
    eg.set_entity.assert_not_called()


def test_remove_schedule_also_removes_group_from_subscribers(schedule, scheduler):
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, scheduler)
    eg2 = EntityGroup("OtherGroup", EntityKind.ON_OFF, scheduler)
    schedule.subscribers = [eg, eg2]
    eg.schedule = schedule

    eg.remove_schedule()

    assert eg.schedule is None, "Schedule was not removed"
    assert schedule.subscribers == [
        eg2
    ], "Group was not removed from schedules subscribers"


def test_remove_schedule_without_schedule_does_nothing(scheduler):
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, scheduler)

    eg.remove_schedule()

    assert eg.schedule is None, "Schedule is not None"


def test_assign_schedule_wrong_type_raises(schedule, scheduler):
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, scheduler)

    schedule.kind = EntityKind.THERMO
    schedule.subscribers = []

    with pytest.raises(ValueError):
        eg.assign_schedule(schedule)

    assert eg.schedule is None
    assert schedule.subscribers == []


def test_assign_does_everything(mocker, schedule, entry, scheduler):
    eg = EntityGroup("MyGroup", EntityKind.ON_OFF, scheduler)

    schedule.kind = EntityKind.ON_OFF
    schedule.subscribers = []

    mocker.patch.object(eg, "remove_schedule")
    mocker.patch.object(eg, "schedule_changed")

    eg.assign_schedule(schedule)

    assert schedule == eg.schedule
    eg.remove_schedule.assert_called_once()
    eg.schedule_changed.assert_called_once_with(entry)
    assert schedule.subscribers == [eg]
