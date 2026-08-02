import json

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


def test_notify_macos_uses_runner():
    calls = []
    notify_macos("t", "m", runner=lambda *a, **k: calls.append(a[0]))
    assert calls and "osascript" in calls[0][0]


def test_status_report_shape(tmp_path):
    conn = init_db(tmp_path / "t.db")
    c = begin_cycle(conn, "m"); record_call(conn, c, "menthorq_prices", 200, 3, None)
    rep = status_report(conn)
    assert rep["cycles_24h"] == 1 and rep["failed_24h"] == 0
    assert "menthorq_prices" in rep["freshness"]
    assert rep["last_errors"] == []
