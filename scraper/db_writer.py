"""SQLite writer helpers for the SpotGamma scraping fleet.

Every agent (or the orchestrator driving WebBridge) uses these helpers so all
scraped data lands in spotgamma.db with a consistent schema.
"""
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "spotgamma.db"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    return con


def utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def start_run(agent_name: str, source_url: str) -> int:
    with _connect() as con:
        cur = con.execute(
            "INSERT INTO scrape_runs (started_at, agent_name, source_url, status) VALUES (?,?,?,?)",
            (utcnow(), agent_name, source_url, "running"),
        )
        return cur.lastrowid


def finish_run(run_id: int, status: str, notes: str = "") -> None:
    with _connect() as con:
        con.execute(
            "UPDATE scrape_runs SET finished_at=?, status=?, notes=? WHERE id=?",
            (utcnow(), status, notes, run_id),
        )


def save_snapshot(run_id: int, source_url: str, section: str, payload: dict) -> int:
    with _connect() as con:
        cur = con.execute(
            "INSERT INTO raw_snapshots (run_id, captured_at, source_url, section, payload_json) VALUES (?,?,?,?,?)",
            (run_id, utcnow(), source_url, section, json.dumps(payload, ensure_ascii=False)),
        )
        return cur.lastrowid
