import pytest

from poller.db import begin_cycle, finish_cycle, init_db, insert_rows, record_call

pytestmark = pytest.mark.unit


def test_init_db_creates_tables(tmp_path):
    conn = init_db(tmp_path / "t.db")
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"gamma_levels", "dealer_positioning", "key_levels",
            "put_call_ratio", "compass", "snapshots", "scrape_runs"} <= names


def test_insert_rows_idempotent(tmp_path):
    conn = init_db(tmp_path / "t.db")
    row = {"ticker": "SPX", "frequency": "eod", "ts": "2026-08-01",
           "gex_1": 7500.0, "gex_2": None, "gex_3": None,
           "payload": "{}", "captured_at": "2026-08-01T14:00:00+00:00", "source": "menthorq"}
    assert insert_rows(conn, "gamma_levels", [row]) == 1
    assert insert_rows(conn, "gamma_levels", [row]) == 0  # duplicate ignored


def test_cycle_audit_roundtrip(tmp_path):
    conn = init_db(tmp_path / "t.db")
    cid = begin_cycle(conn, "menthorq")
    record_call(conn, cid, "menthorq_gamma_levels", 200, 1, None)
    record_call(conn, cid, "menthorq_prices", None, 0, "bridge unreachable")
    finish_cycle(conn, cid)
    runs = conn.execute(
        "SELECT * FROM scrape_runs WHERE cycle_id=? AND tool IS NOT NULL", (cid,)).fetchall()
    assert len(runs) == 2
    assert all(r["finished_at"] is not None for r in runs)
    assert runs[1]["error"] == "bridge unreachable"
    cycle_row = conn.execute(
        "SELECT finished_at FROM scrape_runs WHERE cycle_id=? AND tool IS NULL", (cid,)).fetchone()
    assert cycle_row["finished_at"] is not None
