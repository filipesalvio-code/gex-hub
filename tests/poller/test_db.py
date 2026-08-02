import sqlite3

import pytest

from poller.db import begin_cycle, finish_cycle, init_db, insert_rows, record_call

pytestmark = pytest.mark.unit


def test_init_db_creates_tables():
    conn = init_db(":memory:")
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"gamma_levels", "dealer_positioning", "key_levels",
            "put_call_ratio", "compass", "snapshots", "scrape_runs"} <= names


def test_insert_rows_idempotent():
    conn = init_db(":memory:")
    row = {"ticker": "SPX", "frequency": "eod", "ts": "2026-08-01",
           "gex_1": 7500.0, "gex_2": None, "gex_3": None,
           "payload": "{}", "captured_at": "2026-08-01T14:00:00+00:00", "source": "menthorq"}
    assert insert_rows(conn, "gamma_levels", [row]) == 1
    assert insert_rows(conn, "gamma_levels", [row]) == 0  # duplicate ignored


def test_cycle_audit_roundtrip():
    conn = init_db(":memory:")
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


def test_put_call_ratio_allows_cross_source_same_ts():
    conn = init_db(":memory:")
    base = {"ticker": "SPX", "ts": "2026-08-01", "volume_calls": 1e6,
            "volume_puts": 9e5, "ratio": 0.9, "payload": "{}",
            "captured_at": "2026-08-01T14:00:00+00:00"}
    assert insert_rows(conn, "put_call_ratio", [{**base, "source": "menthorq"}]) == 1
    assert insert_rows(conn, "put_call_ratio", [{**base, "source": "spotgamma"}]) == 1
    assert insert_rows(conn, "put_call_ratio", [{**base, "source": "menthorq"}]) == 0


def test_begin_cycle_returns_incrementing_ids():
    conn = init_db(":memory:")
    assert begin_cycle(conn, "menthorq") == 1
    assert begin_cycle(conn, "spotgamma") == 2


def test_record_call_derives_source():
    conn = init_db(":memory:")
    cid = begin_cycle(conn, "menthorq")
    record_call(conn, cid, "menthorq_gamma_levels", 200, 1, None)
    record_call(conn, cid, "spotgamma_key_levels", 200, 3, None)
    sources = [r["source"] for r in conn.execute(
        "SELECT source FROM scrape_runs WHERE cycle_id=? AND tool IS NOT NULL"
        " ORDER BY rowid", (cid,)).fetchall()]
    assert sources == ["menthorq", "spotgamma"]


def test_record_call_explicit_source():
    conn = init_db(":memory:")
    cid = begin_cycle(conn, "menthorq")
    record_call(conn, cid, "menthorq_prices", None, 0, "boom", source="custom")
    src = conn.execute(
        "SELECT source FROM scrape_runs WHERE tool='menthorq_prices'").fetchone()[0]
    assert src == "custom"


def test_init_db_fails_on_old_sqlite(monkeypatch):
    monkeypatch.setattr(sqlite3, "sqlite_version_info", (3, 34, 0))
    with pytest.raises(RuntimeError, match="SQLite"):
        init_db(":memory:")


_OLD_PCR_SCHEMA = """
CREATE TABLE put_call_ratio (
  ticker TEXT NOT NULL, ts TEXT NOT NULL,
  volume_calls REAL, volume_puts REAL, ratio REAL,
  payload TEXT NOT NULL, captured_at TEXT NOT NULL, source TEXT NOT NULL,
  UNIQUE (ticker, ts)
);
"""


def test_init_db_migrates_old_put_call_ratio_schema(tmp_path):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(_OLD_PCR_SCHEMA)
    old.execute(
        "INSERT INTO put_call_ratio VALUES ('SPX','2026-07-01',1e6,9e5,0.9,"
        " '{\"a\":1}','2026-07-01T14:00:00+00:00','menthorq')")
    old.commit()
    old.close()

    conn = init_db(path)
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table'"
        " AND name='put_call_ratio'").fetchone()[0]
    assert "UNIQUE (ticker, ts, source)" in sql
    rows = conn.execute("SELECT * FROM put_call_ratio").fetchall()
    assert len(rows) == 1 and rows[0]["ticker"] == "SPX"
    base = {"ticker": "SPX", "ts": "2026-07-01", "volume_calls": 1e6,
            "volume_puts": 9e5, "ratio": 0.9, "payload": "{}",
            "captured_at": "2026-07-01T14:00:00+00:00"}
    assert insert_rows(conn, "put_call_ratio", [{**base, "source": "spotgamma"}]) == 1
    assert insert_rows(conn, "put_call_ratio", [{**base, "source": "menthorq"}]) == 0
