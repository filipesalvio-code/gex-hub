import json
import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from poller.db import begin_cycle, init_db, record_call
from poller.observe import JsonlLogger, failure_streak, notify_macos, status_report

pytestmark = pytest.mark.unit


def test_jsonl_log_and_rotation(tmp_path):
    p = tmp_path / "poller.jsonl"
    log = JsonlLogger(p, max_bytes=200)
    for i in range(20):
        log.log({"i": i, "msg": "x" * 30})
    lines = p.read_text().strip().splitlines()
    assert all(json.loads(l)["i"] is not None for l in lines)
    assert (tmp_path / "poller.jsonl.1").exists()


def test_failure_streak(tmp_path):
    conn = init_db(tmp_path / "t.db")
    c1 = begin_cycle(conn, "m"); record_call(conn, c1, "t", 200, 1, None)
    c2 = begin_cycle(conn, "m"); record_call(conn, c2, "t", None, 0, "boom")
    c3 = begin_cycle(conn, "m"); record_call(conn, c3, "t", 500, 0, "err")
    assert failure_streak(conn) == 2


def test_failure_streak_all_cycles_failed_exhausts_loop(tmp_path):
    conn = init_db(tmp_path / "t.db")
    c1 = begin_cycle(conn, "m"); record_call(conn, c1, "t", None, 0, "boom")
    c2 = begin_cycle(conn, "m"); record_call(conn, c2, "t", 500, 0, "err")
    assert failure_streak(conn) == 2


def test_notify_macos_uses_runner():
    calls = []
    notify_macos("t", "m", runner=lambda *a, **k: calls.append(a[0]))
    assert calls and "osascript" in calls[0][0]


def test_notify_macos_passes_values_as_argv_not_script():
    calls = []
    title = 'Bad "quoted" \\ title'
    message = 'evil" & do shell script "rm -rf ~'
    notify_macos(title, message, runner=lambda *a, **k: calls.append(a[0]))
    argv = calls[0]
    assert argv[0] == "osascript"
    script = argv[argv.index("-e") + 1]
    assert title not in script and message not in script
    assert "on run argv" in script
    assert title in argv and message in argv


def test_notify_macos_timeout_is_swallowed():
    def _boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="osascript", timeout=10)
    notify_macos("t", "m", runner=_boom)  # must not raise


def test_notify_macos_timeout_kwarg():
    calls = []
    notify_macos("t", "m", runner=lambda *a, **k: calls.append(k))
    assert calls[0].get("timeout") == 10


def test_status_report_shape(tmp_path):
    conn = init_db(tmp_path / "t.db")
    c = begin_cycle(conn, "m"); record_call(conn, c, "menthorq_prices", 200, 3, None)
    rep = status_report(conn)
    assert rep["cycles_24h"] == 1 and rep["failed_24h"] == 0
    assert "menthorq_prices" in rep["freshness"]
    assert rep["last_errors"] == []


def _insert_cycle(conn, cycle_id, started_at, finished_at=None):
    conn.execute(
        "INSERT INTO scrape_runs (cycle_id, source, tool, started_at, finished_at)"
        " VALUES (?,?,?,?,?)", (cycle_id, "m", "t", started_at, finished_at or started_at))
    conn.commit()


def test_status_report_unparseable_timestamp_marks_stale(tmp_path):
    conn = init_db(tmp_path / "t.db")
    conn.execute(
        "INSERT INTO scrape_runs (cycle_id, source, tool, started_at, finished_at)"
        " VALUES (1, 'm', 't', '2026-08-01T14:00:00+00:00', 'not-a-timestamp')")
    conn.commit()
    rep = status_report(conn)
    assert rep["freshness"]["t"] == 24 * 60


def test_status_report_24h_window_boundary(tmp_path):
    conn = init_db(tmp_path / "t.db")
    threshold = conn.execute("SELECT datetime('now', '-1 day')").fetchone()[0]
    thr = datetime.strptime(threshold, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    # same calendar date as threshold, 1 minute older: string compare ('T' > ' ')
    # would wrongly include this row; julianday must exclude it
    stale = (thr - timedelta(minutes=1)).isoformat()
    fresh = (thr + timedelta(minutes=1)).isoformat()
    _insert_cycle(conn, 1, stale)
    _insert_cycle(conn, 2, fresh)
    rep = status_report(conn)
    assert rep["cycles_24h"] == 1 and rep["last_cycle"] == 2
