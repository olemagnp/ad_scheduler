import pytest
from pytest_mock import mocker
import src.schedule
import datetime


@pytest.mark.parametrize(
    "dt",
    [
        datetime.datetime(2021, 10, 4, 10, 0),
        datetime.datetime(2021, 3, 19, 10, 0),
        datetime.datetime(2025, 11, 1, 10, 0),
        datetime.datetime(1983, 7, 3, 10, 0),
    ],
)
def test_next_datetime_is_today(mocker, dt):
    mocker.patch("src.schedule.dt_now")
    dt = datetime.datetime(2021, 10, 4, 10, 0)
    src.schedule.dt_now.return_value = dt

    entry = src.schedule.Entry(0, 23, 59)
    exp = dt.replace(hour=23, minute=59)

    actual = entry.next_datetime

    assert exp == actual, f"Incorrect next datetime, expected {exp}, got {actual}"


@pytest.mark.parametrize(
    "now,entry,exp",
    [
        (
            datetime.datetime(2021, 11, 1, 12, 0),
            src.schedule.Entry(0, 10, 0, ["tue"]),
            datetime.datetime(2021, 11, 2, 10, 0),
        ),
        (
            datetime.datetime(2021, 11, 1, 12, 0),
            src.schedule.Entry(0, 10, 0, "daily"),
            datetime.datetime(2021, 11, 2, 10, 0),
        ),
        (
            datetime.datetime(2021, 11, 1, 12, 0),
            src.schedule.Entry(0, 10, 0, ["thu"]),
            datetime.datetime(2021, 11, 4, 10, 0),
        ),
        (
            datetime.datetime(2021, 11, 3, 12, 0),
            src.schedule.Entry(0, 10, 0, ["mon"]),
            datetime.datetime(2021, 11, 8, 10, 0),
        ),
        (
            datetime.datetime(2021, 11, 3, 12, 00),
            src.schedule.Entry(0, 10, 0, ["wed", "fri", "mon", "tue"]),
            datetime.datetime(2021, 11, 5, 10, 0),
        ),
        (
            datetime.datetime(2021, 11, 3, 12, 00),
            src.schedule.Entry(0, 13, 0, ["tue", "mon"]),
            datetime.datetime(2021, 11, 8, 13, 0),
        ),
    ],
)
def test_initial_next_datetime(mocker, now, entry, exp):
    mocker.patch("src.schedule.dt_now").return_value = now

    actual = entry.next_datetime

    assert exp == actual, f"Incorrect next datetime, expected {exp}, got {actual}"


def test_next_datetime_changes(mocker):
    mock = mocker.patch("src.schedule.dt_now")

    mock.return_value = datetime.datetime(2021, 11, 1, 12, 0)

    entry = src.schedule.Entry(0, 10, 0, ["mon", "tue", "thu"])

    exp = datetime.datetime(2021, 11, 2, 10, 0)
    actual = entry.next_datetime
    assert exp == actual, f"Incorrect next datetime, expected {exp}, got {actual}"

    mock.return_value = datetime.datetime(2021, 11, 2, 12, 0)

    exp = datetime.datetime(2021, 11, 4, 10, 0)
    actual = entry.next_datetime
    assert exp == actual, f"Incorrect next datetime, expected {exp}, got {actual}"
