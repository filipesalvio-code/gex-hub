"""SQLite helpers for the MenthorQ scraping fleet.

All scraped data lands in menthorq.db with a consistent schema.
Agents must use these helpers instead of writing SQL themselves.
"""
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "menthorq.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scrape_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  agent_name TEXT,
  unit_key TEXT,
  status TEXT,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS raw_responses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER REFERENCES scrape_runs(id),
  captured_at TEXT NOT NULL,
  service TEXT,
  method TEXT DEFAULT 'GET',
  url TEXT NOT NULL,
  http_status INTEGER,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_url ON raw_responses(url);
CREATE INDEX IF NOT EXISTS idx_raw_captured ON raw_responses(captured_at);
CREATE TABLE IF NOT EXISTS api_endpoints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service TEXT NOT NULL,
  method TEXT DEFAULT 'GET',
  path_template TEXT NOT NULL,
  example_url TEXT,
  params TEXT,
  status INTEGER,
  discovered_via TEXT,
  first_seen TEXT NOT NULL,
  UNIQUE(service, method, path_template)
);
CREATE TABLE IF NOT EXISTS tickers (
  ticker TEXT PRIMARY KEY,
  symbol TEXT,
  provider TEXT,
  name TEXT,
  exchange TEXT,
  asset_type TEXT,
  category TEXT,
  calendar_code TEXT,
  free_visible INTEGER,
  contracts_json TEXT,
  raw_json TEXT
);
"""


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_db() -> None:
    with _connect() as con:
        con.executescript(_SCHEMA)


def utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def start_run(agent_name: str, unit_key: str) -> int:
    init_db()
    with _connect() as con:
        cur = con.execute(
            "INSERT INTO scrape_runs (started_at, agent_name, unit_key, status) VALUES (?,?,?,?)",
            (utcnow(), agent_name, unit_key, "running"),
        )
        return cur.lastrowid


def finish_run(run_id: int, status: str, notes: str = "") -> None:
    with _connect() as con:
        con.execute(
            "UPDATE scrape_runs SET finished_at=?, status=?, notes=? WHERE id=?",
            (utcnow(), status, notes, run_id),
        )


def save_response(run_id: int, service: str, url: str, http_status: int,
                  payload, method: str = "GET") -> int:
    init_db()
    with _connect() as con:
        cur = con.execute(
            "INSERT INTO raw_responses (run_id, captured_at, service, method, url, http_status, payload_json) VALUES (?,?,?,?,?,?,?)",
            (run_id, utcnow(), service, method, url, http_status,
             json.dumps(payload, ensure_ascii=False)),
        )
        return cur.lastrowid


def save_endpoint(service: str, path_template: str, example_url: str = "",
                  params: str = "", status: int = 0, discovered_via: str = "",
                  method: str = "GET") -> None:
    init_db()
    with _connect() as con:
        con.execute(
            """INSERT INTO api_endpoints (service, method, path_template, example_url, params, status, discovered_via, first_seen)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(service, method, path_template) DO UPDATE SET
                 example_url=COALESCE(NULLIF(excluded.example_url,''), api_endpoints.example_url),
                 status=CASE WHEN excluded.status!=0 THEN excluded.status ELSE api_endpoints.status END""",
            (service, method, path_template, example_url, params, status,
             discovered_via, utcnow()),
        )


def upsert_ticker(row: dict) -> None:
    init_db()
    with _connect() as con:
        con.execute(
            """INSERT INTO tickers (ticker, symbol, provider, name, exchange, asset_type, category, calendar_code, free_visible, contracts_json, raw_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(ticker) DO UPDATE SET
                 symbol=excluded.symbol, provider=excluded.provider, name=excluded.name,
                 exchange=excluded.exchange, asset_type=excluded.asset_type,
                 category=excluded.category, calendar_code=excluded.calendar_code,
                 free_visible=excluded.free_visible, contracts_json=excluded.contracts_json,
                 raw_json=excluded.raw_json""",
            (row.get("ticker"), row.get("symbol"), row.get("provider"),
             row.get("name"), row.get("exchange"), row.get("asset_type"),
             row.get("category"), row.get("calendar_code"),
             1 if row.get("free_visible") else 0,
             json.dumps(row.get("contracts", []), ensure_ascii=False),
             json.dumps(row, ensure_ascii=False)),
        )
