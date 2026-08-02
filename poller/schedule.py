"""Market-hours gate (US equities, UTC). Holiday check happens at runtime
via menthorq_market_status in poll.py."""
from datetime import UTC, datetime, time

_OPEN, _CLOSE = time(13, 30), time(20, 0)


def in_market_window(now: datetime) -> bool:
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    else:
        now = now.astimezone(UTC)
    return now.weekday() < 5 and _OPEN <= now.time() < _CLOSE
