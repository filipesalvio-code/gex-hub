from datetime import UTC, datetime

import pytest

from poller.schedule import in_market_window

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("dt,expected", [
    (datetime(2026, 8, 3, 13, 30, tzinfo=UTC), True),   # Mon open edge (EDT)
    (datetime(2026, 8, 3, 16, 0, tzinfo=UTC), True),    # Mon midday (EDT)
    (datetime(2026, 8, 7, 19, 59, tzinfo=UTC), True),   # Fri before close (EDT)
    (datetime(2026, 8, 7, 20, 0, tzinfo=UTC), False),   # Fri close edge (EDT)
    (datetime(2026, 8, 3, 13, 29, tzinfo=UTC), False),  # before open (EDT)
    (datetime(2026, 8, 8, 16, 0, tzinfo=UTC), False),   # Saturday
    (datetime(2026, 8, 9, 16, 0, tzinfo=UTC), False),   # Sunday
    (datetime(2026, 8, 4, 3, 0, tzinfo=UTC), False),    # overnight
    (datetime(2026, 1, 5, 14, 30, tzinfo=UTC), True),   # Mon open edge (EST)
    (datetime(2026, 1, 5, 14, 29, tzinfo=UTC), False),  # before open (EST)
    (datetime(2026, 1, 5, 21, 0, tzinfo=UTC), False),   # Mon close edge (EST)
    (datetime(2026, 1, 5, 20, 59, tzinfo=UTC), True),   # before close (EST)
    (datetime(2026, 1, 3, 17, 0, tzinfo=UTC), False),   # Saturday (EST)
])
def test_window(dt, expected):
    assert in_market_window(dt) is expected


def test_naive_treated_as_utc():
    assert in_market_window(datetime(2026, 8, 3, 16, 0)) is True  # noqa: DTZ001
