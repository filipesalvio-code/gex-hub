"""SQLite schema and write helpers for gex-poller time series."""
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DATA_TABLES = ("gamma_levels", "dealer_positioning", "key_levels",
               "put_call_ratio", "compass", "snapshots")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS gamma_levels (
  ticker TEXT NOT NULL, frequency TEXT NOT NULL, ts TEXT NOT NULL,
  gex_1 REAL, gex_2 REAL, gex_3 REAL,
  payload TEXT NOT NULL, captured_at TEXT NOT NULL, source TEXT NOT NULL,
  UNIQUE (ticker, frequency, ts)
);
CREATE TABLE IF NOT EXISTS dealer_positioning (
  ticker TEXT NOT NULL, ts TEXT NOT NULL,
  net_gex REAL, net_dex REAL, gex_dte_0_7d REAL, gex_dte_8_30d REAL, gex_dte_over_30d REAL,
  payload TEXT NOT NULL, captured_at TEXT NOT NULL, source TEXT NOT NULL,
  UNIQUE (ticker, ts)
);
CREATE TABLE IF NOT EXISTS key_levels (
  ticker TEXT NOT NULL, ts TEXT NOT NULL,
  payload TEXT NOT NULL, captured_at TEXT NOT NULL, source TEXT NOT NULL,
  UNIQUE (ticker, ts)
);
CREATE TABLE IF NOT EXISTS put_call_ratio (
  ticker TEXT NOT NULL, ts TEXT NOT NULL,
  volume_calls REAL, volume_puts REAL, ratio REAL,
   payload TEXT NOT NULL, captured_at TEXT NOT NULL, source TEXT NOT NULL,
   UNIQUE (ticker, ts, source)
);
CREATE TABLE IF NOT EXISTS compass (
  ticker TEXT NOT NULL, ts TEXT NOT NULL,
  payload TEXT NOT NULL, captured_at TEXT NOT NULL, source TEXT NOT NULL,
  UNIQUE (ticker, ts)
);
CREATE TABLE IF NOT EXISTS snapshots (
  tool TEXT NOT NULL, ticker TEXT NOT NULL, ts TEXT NOT NULL,
  payload TEXT NOT NULL, captured_at TEXT NOT NULL, source TEXT NOT NULL,
  UNIQUE (tool, ticker, ts)
);
CREATE TABLE IF NOT EXISTS scrape_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cycle_id INTEGER NOT NULL, source TEXT NOT NULL, tool TEXT,
  started_at TEXT NOT NULL, finished_at TEXT,
  http_status INTEGER, rows_written INTEGER DEFAULT 0, error TEXT
);
"""


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


_PCR_NEW_SQL = """CREATE TABLE put_call_ratio (
  ticker TEXT NOT NULL, ts TEXT NOT NULL,
  volume_calls REAL, volume_puts REAL, ratio REAL,
  payload TEXT NOT NULL, captured_at TEXT NOT NULL, source TEXT NOT NULL,
  UNIQUE (ticker, ts, source)
);"""


def _migrate_put_call_ratio(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table'"
        " AND name='put_call_ratio'").fetchone()
    if row is None or "UNIQUE (ticker, ts, source)" in row[0]:
        return
    conn.executescript(
        "ALTER TABLE put_call_ratio RENAME TO put_call_ratio_old;\n"
        + _PCR_NEW_SQL + "\n"
        "INSERT OR IGNORE INTO put_call_ratio"
        " (ticker, ts, volume_calls, volume_puts, ratio, payload, captured_at, source)"
        " SELECT ticker, ts, volume_calls, volume_puts, ratio, payload, captured_at, source"
        " FROM put_call_ratio_old;\n"
        "DROP TABLE put_call_ratio_old;")
    conn.commit()


def init_db(path: str | Path) -> sqlite3.Connection:
    if sqlite3.sqlite_version_info < (3, 35, 0):
        raise RuntimeError(
            f"SQLite >= 3.35 required (RETURNING); got {sqlite3.sqlite_version}")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    _migrate_put_call_ratio(conn)
    conn.executescript(_SCHEMA)
    return conn


def begin_cycle(conn: sqlite3.Connection, source: str) -> int:
    row = conn.execute(
        "INSERT INTO scrape_runs (cycle_id, source, tool, started_at) "
        "VALUES ((SELECT COALESCE(MAX(cycle_id),0)+1 FROM scrape_runs), ?, NULL, ?) "
        "RETURNING cycle_id",
        (source, _utcnow())).fetchone()
    conn.commit()
    return row[0]


def record_call(conn, cycle_id: int, tool: str, http_status: int | None,
                rows: int, error: str | None, source: str | None = None) -> None:
    if source is None:
        source = "menthorq" if tool.startswith("menthorq_") else "spotgamma"
    now = _utcnow()
    conn.execute(
        "INSERT INTO scrape_runs (cycle_id, source, tool, started_at, finished_at,"
        " http_status, rows_written, error) VALUES (?,?,?,?,?,?,?,?)",
        (cycle_id, source, tool, now, now, http_status, rows, error))
    conn.commit()


def finish_cycle(conn: sqlite3.Connection, cycle_id: int) -> None:
    conn.execute("UPDATE scrape_runs SET finished_at=? WHERE cycle_id=? AND tool IS NULL",
                 (_utcnow(), cycle_id))
    conn.commit()


def insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> int:
    if table not in DATA_TABLES:
        raise ValueError(f"unknown table: {table}")
    if not rows:
        return 0
    cols = list(rows[0].keys())
    sql = f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
    before = conn.total_changes
    with conn:
        conn.executemany(sql, [[r.get(c) for c in cols] for r in rows])
    return conn.total_changes - before
