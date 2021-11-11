import pytest

from ad_scheduler.scheduler import Scheduler


@pytest.fixture
def scheduler(given_that):
    sched = Scheduler(None, None, None, None, None, None, None)

    sched.initialize()
    given_that.mock_functions_are_cleared()

    return sched
