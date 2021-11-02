import unittest
from unittest import mock
import src.schedule
import datetime


class EntryTest(unittest.TestCase):
    def test_initial_next_datetime_today(self):
        def test_today(dt: datetime.datetime):
            with mock.patch("src.schedule.dt_now") as mock_dt:
                mock_dt.return_value = dt

                entry = src.schedule.Entry(0, 23, 59, "daily")

                exp = dt.replace(hour=23, minute=59)
                actual = entry.next_datetime
                assert (
                    exp == actual
                ), f"Incorrect next datetime, expected {exp}, got {actual}"

        test_today(datetime.datetime(2021, 10, 4, 10, 0))
        test_today(datetime.datetime(2021, 3, 19, 10, 0))
        test_today(datetime.datetime(2025, 11, 1, 10, 0))
        test_today(datetime.datetime(1983, 7, 3, 10, 0))

    def test_initial_next_datetime_now_monday_next_tuesday(self):
        with mock.patch("src.schedule.dt_now") as mock_dt:
            mock_dt.return_value = datetime.datetime(2021, 11, 1, 12, 0)

            entry = src.schedule.Entry(0, 10, 0, ["tue"])

            exp = datetime.datetime(2021, 11, 2, 10, 0)
            actual = entry.next_datetime
            assert (
                exp == actual
            ), f"Incorrect next datetime, expected {exp}, got {actual}"

            entry = src.schedule.Entry(0, 10, 0, "daily")

            exp = datetime.datetime(2021, 11, 2, 10, 0)
            actual = entry.next_datetime
            assert (
                exp == actual
            ), f"Incorrect next datetime, expected {exp}, got {actual}"

    def test_initial_next_datetime_now_monday_next_thursday(self):
        with mock.patch("src.schedule.dt_now") as mock_dt:
            mock_dt.return_value = datetime.datetime(2021, 11, 1, 12, 0)

            entry = src.schedule.Entry(0, 10, 0, ["thu"])

            exp = datetime.datetime(2021, 11, 4, 10, 0)
            actual = entry.next_datetime
            assert (
                exp == actual
            ), f"Incorrect next datetime, expected {exp}, got {actual}"

    def test_initial_next_datetime_now_wednesday_next_monday(self):
        with mock.patch("src.schedule.dt_now") as mock_dt:
            mock_dt.return_value = datetime.datetime(2021, 11, 3, 12, 0)

            entry = src.schedule.Entry(0, 10, 0, ["mon"])

            exp = datetime.datetime(2021, 11, 8, 10, 0)
            actual = entry.next_datetime
            assert (
                exp == actual
            ), f"Incorrect next datetime, expected {exp}, got {actual}"

    def test_initial_next_datetime_multiple_days(self):
        def test(now: datetime.datetime, expected: datetime.datetime, entry):
            with mock.patch("src.schedule.dt_now") as mock_dt:
                mock_dt.return_value = now

                actual = entry.next_datetime

                assert (
                    expected == actual
                ), f"Incorrect next datetime, expected {expected}, got {actual}"

        entry = src.schedule.Entry(0, 10, 0, ["wed", "fri", "mon", "tue"])
        test(
            datetime.datetime(2021, 11, 3, 12, 00),
            datetime.datetime(2021, 11, 5, 10, 0),
            entry,
        )

        entry = src.schedule.Entry(0, 13, 0, ["tue", "mon"])
        test(
            datetime.datetime(2021, 11, 3, 12, 00),
            datetime.datetime(2021, 11, 8, 13, 0),
            entry,
        )

    def test_next_datetime_changes(self):
        entry = src.schedule.Entry(0, 10, 0, ["mon", "tue", "thu"])
        with mock.patch("src.schedule.dt_now") as mock_dt:
            mock_dt.return_value = datetime.datetime(2021, 11, 1, 12, 0)

            exp = datetime.datetime(2021, 11, 2, 10, 0)
            actual = entry.next_datetime
            assert (
                exp == actual
            ), f"Incorrect next datetime, expected {exp}, got {actual}"

            mock_dt.return_value = datetime.datetime(2021, 11, 2, 12, 0)

            exp = datetime.datetime(2021, 11, 4, 10, 0)
            actual = entry.next_datetime
            assert (
                exp == actual
            ), f"Incorrect next datetime, expected {exp}, got {actual}"
