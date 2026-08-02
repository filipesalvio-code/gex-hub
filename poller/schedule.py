"""Market-hours gate (US equities, America/New_York). No holiday check here —
menthorq_market_status is captured as data only and does not gate the cycle."""
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")
_OPEN, _CLOSE = time(9, 30), time(16, 0)


def in_market_window(now: datetime) -> bool:
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    local = now.astimezone(_ET)
    return local.weekday() < 5 and _OPEN <= local.time() < _CLOSE
