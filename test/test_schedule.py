from datetime import datetime
from scheduler.const import EntityKind
from scheduler.entities import EntityGroup
from scheduler.schedule import Entry, Schedule
import pytest
from pytest_mock import mocker


@pytest.fixture
def schedule(mocker) -> Schedule:
    scheduler = mocker.Mock()
    return Schedule("name", EntityKind.ON_OFF, scheduler)


@pytest.fixture
def entry() -> Entry:
    return Entry(42, 10, 0, additional_attrs={"some_attr": "some_value"})


@pytest.fixture
def subscribers(mocker):
    return [
        mocker.Mock(EntityGroup),
        mocker.Mock(EntityGroup),
        mocker.Mock(EntityGroup),
    ]


def test_init(schedule):
    assert schedule.name == "name"
    assert schedule.kind == EntityKind.ON_OFF
    assert schedule.entries == []
    assert schedule.subscribers == []
    assert schedule.current_entry is None
    assert schedule.next_entry is None
    assert schedule.next_trigger is None


def test_cancel_without_trigger(schedule):
    schedule.cancel()
    assert schedule.next_trigger is None


def test_cancel_with_trigger(mocker, schedule):
    mocker.patch.object(schedule, "next_trigger")

    schedule.cancel()
    assert schedule.next_trigger is None
    schedule.scheduler.cancel_timer.assert_called()


def test_add_entry(mocker, schedule, entry):
    mocker.patch.object(schedule, "update_state")
    schedule.add_entry(entry)

    assert schedule.entries == [entry]
    schedule.update_state.assert_called_once()

    mocker.patch.object(schedule, "set_subscribers")

    def set_current():
        schedule.current_entry = entry

    schedule.update_state.side_effect = set_current
    entry2 = Entry(10, 12, 0, ["tue"])
    schedule.add_entry(entry2)

    assert schedule.entries == [entry, entry2]
    schedule.update_state.assert_called()
    schedule.set_subscribers.assert_called()


def test_entry_at_same_time_raises(mocker, schedule):
    e1 = Entry(52, 10, 0, ["mon", "wed"])
    e2 = Entry(20, 10, 0, ["wed", "fri", "sat"])

    mocker.patch.object(schedule, "update_state")

    schedule.add_entry(e1)

    with pytest.raises(ValueError):
        schedule.add_entry(e2)


def test_set_subscribers_calls_all(schedule, subscribers, entry):
    schedule.subscribers = subscribers

    schedule.set_subscribers(entry)

    for sub in subscribers:
        sub.schedule_changed.assert_called_once_with(entry)


def test_trigger_calls(mocker, schedule, entry):
    mocker.patch.object(schedule, "update_state")
    mocker.patch.object(schedule, "set_subscribers")

    schedule.current_entry = entry
    schedule.trigger(None)

    schedule.update_state.assert_called_once()
    schedule.set_subscribers.assert_called_once_with(entry)


def test_update_state_with_no_entries(schedule):
    schedule.update_state()
    assert schedule.current_entry is None
    assert schedule.next_entry is None
    assert schedule.next_trigger is None


def test_update_state_with_single_entry(schedule, entry):
    schedule.entries = [entry]

    schedule.update_state()

    assert schedule.current_entry == entry
    assert schedule.next_entry == entry

    schedule.scheduler.run_at.assert_called_once()


def test_update_state_with_multiple_entries(mocker, schedule: Schedule):
    mock = mocker.patch("scheduler.schedule.dt_now")
    mock.return_value = datetime(2021, 11, 1, 9, 0)  # Monday 9:00
    # TODO Need to find previous datetime instead of max next-datetime
    entries = [
        Entry(10, 10, 0, ["mon", "tue", "wed"]),
        Entry(20, 12, 0, ["wed", "thu"]),
        Entry(30, 9, 0, ["sun", "tue"]),
    ]

    schedule.entries = entries

    schedule.update_state()
    assert schedule.current_entry == entries[2]
    assert schedule.next_entry == entries[0]
    schedule.scheduler.run_at.assert_called()

    mock.return_value = datetime(2021, 11, 1, 10, 1, 0, 1)  # Monday 10:00+

    schedule.update_state()
    assert schedule.current_entry == entries[0]
    assert schedule.next_entry == entries[2]
    schedule.scheduler.run_at.assert_called()
