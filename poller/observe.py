"""Minimal observability: JSONL log, failure streak, macOS notify, status."""
import json
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path

_STALE_MIN = 24 * 60


class JsonlLogger:
    def __init__(self, path: str | Path, max_bytes: int = 10_000_000):
        self.path, self.max_bytes = Path(path), max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: dict) -> None:
        if self.path.exists() and self.path.stat().st_size > self.max_bytes:
            self.path.replace(self.path.with_suffix(self.path.suffix + ".1"))
        event = {"ts": datetime.now(UTC).isoformat(timespec="seconds"), **event}
        with self.path.open("a") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def failure_streak(conn: sqlite3.Connection) -> int:
    cycles = conn.execute(
        "SELECT cycle_id, MAX(error IS NOT NULL) AS failed FROM scrape_runs"
        " WHERE tool IS NOT NULL GROUP BY cycle_id ORDER BY cycle_id DESC").fetchall()
    streak = 0
    for row in cycles:
        if row["failed"]:
            streak += 1
        else:
            break
    return streak


def notify_macos(title: str, message: str, runner=subprocess.run) -> None:
    script = f'display notification "{message}" with title "{title}"'
    try:
        runner(["osascript", "-e", script], check=False, capture_output=True)
    except OSError:
        pass


def status_report(conn: sqlite3.Connection) -> dict:
    now = datetime.now(UTC)
    cycles = conn.execute(
        "SELECT cycle_id, MAX(error IS NOT NULL) AS failed, MAX(finished_at) AS done"
        " FROM scrape_runs WHERE tool IS NOT NULL"
        " AND started_at >= datetime('now', '-1 day') GROUP BY cycle_id").fetchall()
    fresh = {}
    for row in conn.execute(
            "SELECT tool, MAX(finished_at) AS last_ok FROM scrape_runs"
            " WHERE tool IS NOT NULL AND error IS NULL GROUP BY tool"):
        last = row["last_ok"]
        try:
            mins = int((now - datetime.fromisoformat(last)).total_seconds() // 60)
        except (TypeError, ValueError):
            mins = _STALE_MIN
        fresh[row["tool"]] = mins
    errors = [r["error"] for r in conn.execute(
        "SELECT error FROM scrape_runs WHERE error IS NOT NULL"
        " ORDER BY id DESC LIMIT 5")]
    return {"last_cycle": cycles[0]["cycle_id"] if cycles else None,
            "cycles_24h": len(cycles),
            "failed_24h": sum(1 for c in cycles if c["failed"]),
            "freshness": fresh, "last_errors": errors}
