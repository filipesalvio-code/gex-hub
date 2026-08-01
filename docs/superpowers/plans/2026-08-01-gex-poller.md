# gex-poller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically poll core MenthorQ + SpotGamma MCP tools on a 15-min LaunchAgent schedule and store normalized time series in `timeseries.db`, with minimal observability.

**Architecture:** Stateless Python package `poller/` spawns both MCP servers over stdio JSON-RPC, calls the core tool set, normalizes responses into typed sqlite tables, audits every call in `scrape_runs`, logs JSONL, exits. A `--once` flag runs a single cycle for live e2e.

**Tech Stack:** Python 3.11+, stdlib only for runtime (subprocess, sqlite3, json), pytest + pytest-cov for tests, macOS LaunchAgent for scheduling, CodeRabbit for review.

## Global Constraints

- Runtime code in `poller/` uses **stdlib only** (no new dependencies). `pytest-cov` is dev-only.
- Ruff `line-length = 110`; code must pass `ruff check poller tests`.
- Tests must not touch the network: root `tests/conftest.py` blocks sockets (autouse). Poller tests use stdio subprocesses (pipes are allowed) and `:memory:`/tmp-path sqlite.
- Live tests are marked `@pytest.mark.live` and skipped unless `--runlive` is passed.
- Markers: `unit`, `integration`, `live`. Every test carries exactly one marker.
- Coverage gates: `unit` → 100% on `poller/normalize.py poller/schedule.py poller/db.py poller/observe.py`; `unit+integration` → ≥80% on `poller/`; live e2e exercises ≥40% of capture tools (≥4 of 10).
- **CodeRabbit review gate after every 3 tasks** (after Tasks 3, 6, 9): push branch, open PR, address all CodeRabbit findings, merge before continuing.
- Commit style matches repo: `feat:`, `test:`, `chore:`, `docs:` lowercase conventional commits.

## File Structure

```
poller/
  __init__.py        # empty
  db.py              # schema init, run audit, idempotent inserts
  normalize.py       # ToolResult parsing + payload → row dicts (pure)
  mcp_client.py      # stdio JSON-RPC client for both servers
  schedule.py        # market-hours window gate (pure)
  observe.py         # JSONL logger, failure streak, macOS notify, status report
  poll.py            # cycle orchestration + CLI (--once)
  status.py          # status CLI
poller/com.gexhub.poller.plist  # LaunchAgent template
tests/poller/
  conftest.py        # fake MCP server fixture, marker registration helpers
  fake_mcp_server.py # stdio server replaying canned responses
  test_db.py         # unit
  test_normalize.py  # unit
  test_schedule.py   # unit
  test_observe.py    # unit
  test_mcp_client.py # integration
  test_poll.py       # integration
  test_status.py     # integration
  test_e2e_live.py   # live
```

---

### Task 1: Scaffolding, markers, coverage config

**Files:**
- Create: `poller/__init__.py`
- Create: `tests/poller/__init__.py` (empty)
- Modify: `pyproject.toml` (dev deps + pytest markers + coverage config)

**Interfaces:**
- Produces: pytest markers `unit`, `integration`, `live`; `--runlive` CLI flag (defined in `tests/poller/conftest.py`, Task 4).

- [ ] **Step 1: Create package skeletons**

```bash
mkdir -p poller tests/poller
touch poller/__init__.py tests/poller/__init__.py
```

- [ ] **Step 2: Update `pyproject.toml`**

In `[project.optional-dependencies]` dev list, add `"pytest-cov>=5"`. In `[tool.pytest.ini_options]`, replace with:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: pure-function tests, no subprocess, no sqlite files",
    "integration: stdio subprocess and/or real sqlite file I/O",
    "live: hits real MCP servers and bridge daemon (needs --runlive)",
]

[tool.coverage.run]
source = ["poller"]
branch = true

[tool.coverage.report]
show_missing = true
exclude_also = ["if __name__ == .__main__.:"]
```

- [ ] **Step 3: Verify config loads**

Run: `pip install -e ".[dev]" && pytest --collect-only -q | tail -3`
Expected: existing tests still collected, no marker warnings.

- [ ] **Step 4: Commit**

```bash
git add poller tests/poller pyproject.toml
git commit -m "chore: scaffold poller package, pytest markers, coverage config"
```

---

### Task 2: `poller/db.py` — schema + idempotent writes

**Files:**
- Create: `poller/db.py`
- Test: `tests/poller/test_db.py`

**Interfaces:**
- Produces:
  - `init_db(path: str | Path) -> sqlite3.Connection` — creates all tables, returns conn with `row_factory = sqlite3.Row`.
  - `begin_cycle(conn, source: str) -> int` — inserts scrape_runs row with `finished_at=NULL`, returns `cycle_id`.
  - `record_call(conn, cycle_id: int, tool: str, http_status: int | None, rows: int, error: str | None) -> None`
  - `finish_cycle(conn, cycle_id: int) -> None`
  - `insert_rows(conn, table: str, rows: list[dict]) -> int` — INSERT OR IGNORE, returns count actually inserted.
  - Table names: `gamma_levels`, `dealer_positioning`, `key_levels`, `put_call_ratio`, `compass`, `snapshots`, `scrape_runs`.

- [ ] **Step 1: Write the failing test**

```python
# tests/poller/test_db.py
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
    runs = conn.execute("SELECT * FROM scrape_runs WHERE cycle_id=?", (cid,)).fetchall()
    assert len(runs) == 2
    assert all(r["finished_at"] is not None for r in runs)
    assert runs[1]["error"] == "bridge unreachable"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/poller/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: poller.db`

- [ ] **Step 3: Implement `poller/db.py`**

```python
"""SQLite schema and write helpers for gex-poller time series."""
import sqlite3
from datetime import datetime, timezone
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
  UNIQUE (ticker, ts)
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
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def begin_cycle(conn: sqlite3.Connection, source: str) -> int:
    cur = conn.execute(
        "INSERT INTO scrape_runs (cycle_id, source, tool, started_at) "
        "VALUES ((SELECT COALESCE(MAX(cycle_id),0)+1 FROM scrape_runs), ?, NULL, ?)",
        (source, _utcnow()))
    conn.commit()
    return conn.execute("SELECT MAX(cycle_id) FROM scrape_runs").fetchone()[0]


def record_call(conn, cycle_id: int, tool: str, http_status: int | None,
                rows: int, error: str | None) -> None:
    now = _utcnow()
    conn.execute(
        "INSERT INTO scrape_runs (cycle_id, source, tool, started_at, finished_at,"
        " http_status, rows_written, error) VALUES (?,?,?,?,?,?,?,?)",
        (cycle_id, "", tool, now, now, http_status, rows, error))
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/poller/test_db.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add poller/db.py tests/poller/test_db.py
git commit -m "feat: poller sqlite schema with idempotent inserts and run audit"
```

---

### Task 3: `poller/normalize.py` — response parsing + row mapping

**Files:**
- Create: `poller/normalize.py`
- Test: `tests/poller/test_normalize.py`

**Interfaces:**
- Consumes: nothing from other tasks (pure).
- Produces:
  - `ToolResult` dataclass: `tool: str, ok: bool, data: Any, http_status: int | None, error: str | None`
  - `parse_tool_text(tool: str, text: str) -> ToolResult` — handles MenthorQ envelope `{"http_status", "data"}`, SpotGamma raw JSON, and `"Error: ..."` plain text.
  - `to_rows(tool: str, result: ToolResult, captured_at: str) -> tuple[str, list[dict]]` — returns `(table, rows)`; rows match `db.insert_rows` columns. Unknown/failed results return `("snapshots", [])` only when `ok`; raise `ValueError` when `not ok`.
  - `SOURCE_MENTHORQ = "menthorq"`, `SOURCE_SPOTGAMMA = "spotgamma"`; source derived from tool name prefix.

Row shapes per tool:
- `menthorq_gamma_levels` → `gamma_levels`: ticker, frequency, ts=`data["timestamp"]`, gex_1/2/3, payload=raw text, captured_at, source
- `menthorq_dealer_positioning` → `dealer_positioning`: ts=`reference_timestamp`, net_gex, net_dex, gex_dte_0_7d/8_30d/over_30d
- `menthorq_put_call_ratio` (and `spotgamma_equity_put_call_ratio`) → `put_call_ratio`: ts=`timestamp`, volume_calls, volume_puts, ratio=`put_call_ratio`
- `spotgamma_key_levels` → `key_levels`: one row per `data["data"]` item, ticker=`sym`, ts=`trade_date`
- `spotgamma_compass` → `compass`: ticker from args echoed in data or `"SPX"` default, ts=`date`/`timestamp` fallback `captured_at`
- everything else (`menthorq_metrics_intraday`, `menthorq_market_status`, `spotgamma_zero_dte`, `spotgamma_most_recent_market_open`) → `snapshots`: tool, ticker (or `""`), ts (first of timestamp/trade_date/date, fallback captured_at), payload

- [ ] **Step 1: Write the failing test**

```python
# tests/poller/test_normalize.py
import json

import pytest

from poller.normalize import parse_tool_text, to_rows

pytestmark = pytest.mark.unit

CAP = "2026-08-01T14:00:00+00:00"


def _env(data, status=200):
    return json.dumps({"http_status": status, "data": data})


def test_parse_menthorq_envelope():
    r = parse_tool_text("menthorq_gamma_levels", _env({"a": 1}))
    assert r.ok and r.http_status == 200 and r.data == {"a": 1}


def test_parse_menthorq_error_status():
    r = parse_tool_text("menthorq_prices", _env({"msg": "bad"}, status=401))
    assert not r.ok and r.http_status == 401


def test_parse_spotgamma_raw_json():
    r = parse_tool_text("spotgamma_key_levels", '{"data": [1, 2]}')
    assert r.ok and r.data == {"data": [1, 2]}


def test_parse_plain_error_text():
    r = parse_tool_text("spotgamma_compass", "Error: unauthorized")
    assert not r.ok and "unauthorized" in r.error


def test_gamma_levels_row():
    r = parse_tool_text("menthorq_gamma_levels", _env(
        {"ticker": "SPX", "timestamp": "2026-08-01", "frequency": "eod",
         "gex_1": 7500, "gex_2": 7400, "gex_3": 7300}))
    table, rows = to_rows("menthorq_gamma_levels", r, CAP)
    assert table == "gamma_levels"
    assert rows[0]["ticker"] == "SPX" and rows[0]["gex_1"] == 7500
    assert rows[0]["source"] == "menthorq" and rows[0]["captured_at"] == CAP


def test_key_levels_multi_row():
    r = parse_tool_text("spotgamma_key_levels", json.dumps({"data": [
        {"sym": "SPX", "trade_date": "2026-07-30T00:00:00.000Z", "levels_with_pct": "[]"},
        {"sym": "SPY", "trade_date": "2026-07-30T00:00:00.000Z", "levels_with_pct": "[]"}]}))
    table, rows = to_rows("spotgamma_key_levels", r, CAP)
    assert table == "key_levels" and len(rows) == 2
    assert rows[1]["ticker"] == "SPY" and rows[1]["source"] == "spotgamma"


def test_fallback_to_snapshots():
    r = parse_tool_text("spotgamma_zero_dte", '[{"sym": "SPX", "date": "2026-07-31"}]')
    table, rows = to_rows("spotgamma_zero_dte", r, CAP)
    assert table == "snapshots" and rows[0]["tool"] == "spotgamma_zero_dte"


def test_failed_result_raises():
    r = parse_tool_text("menthorq_prices", _env({}, status=500))
    with pytest.raises(ValueError):
        to_rows("menthorq_prices", r, CAP)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/poller/test_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: poller.normalize`

- [ ] **Step 3: Implement `poller/normalize.py`**

```python
"""Parse MCP tool response text and map payloads to table rows."""
import json
from dataclasses import dataclass
from typing import Any

SOURCE_MENTHORQ = "menthorq"
SOURCE_SPOTGAMMA = "spotgamma"


@dataclass
class ToolResult:
    tool: str
    ok: bool
    data: Any = None
    http_status: int | None = None
    error: str | None = None
    raw: str = ""


def parse_tool_text(tool: str, text: str) -> ToolResult:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return ToolResult(tool, ok=False, error=text[:300], raw=text)
    if isinstance(payload, dict) and "http_status" in payload:
        status = payload["http_status"]
        ok = status == 200
        return ToolResult(tool, ok=ok, data=payload.get("data"), http_status=status,
                          error=None if ok else str(payload.get("data"))[:300], raw=text)
    return ToolResult(tool, ok=True, data=payload, raw=text)


def _source(tool: str) -> str:
    return SOURCE_MENTHORQ if tool.startswith("menthorq_") else SOURCE_SPOTGAMMA


def _first(d: dict, *keys: str):
    return next((d[k] for k in keys if isinstance(d, dict) and d.get(k)), None)


def _base(tool: str, ticker: str, ts: str, cap: str) -> dict:
    return {"tool": tool, "ticker": ticker or "", "ts": ts,
            "captured_at": cap, "source": _source(tool)}


def to_rows(tool: str, result: ToolResult, captured_at: str) -> tuple[str, list[dict]]:
    if not result.ok:
        raise ValueError(f"{tool} failed: {result.error}")
    d = result.data
    payload = result.raw
    src = _source(tool)

    if tool == "menthorq_gamma_levels":
        row = {"ticker": d["ticker"], "frequency": d["frequency"], "ts": d["timestamp"],
               "gex_1": d.get("gex_1"), "gex_2": d.get("gex_2"), "gex_3": d.get("gex_3"),
               "payload": payload, "captured_at": captured_at, "source": src}
        return "gamma_levels", [row]
    if tool == "menthorq_dealer_positioning":
        row = {"ticker": d.get("ticker", ""), "ts": d["reference_timestamp"],
               "net_gex": d.get("net_gex"), "net_dex": d.get("net_dex"),
               "gex_dte_0_7d": d.get("gex_dte_0_7d"), "gex_dte_8_30d": d.get("gex_dte_8_30d"),
               "gex_dte_over_30d": d.get("gex_dte_over_30d"),
               "payload": payload, "captured_at": captured_at, "source": src}
        return "dealer_positioning", [row]
    if tool in ("menthorq_put_call_ratio", "spotgamma_equity_put_call_ratio"):
        row = {"ticker": d.get("ticker", d.get("sym", "")), "ts": d["timestamp"],
               "volume_calls": d.get("volume_calls"), "volume_puts": d.get("volume_puts"),
               "ratio": d.get("put_call_ratio"),
               "payload": payload, "captured_at": captured_at, "source": src}
        return "put_call_ratio", [row]
    if tool == "spotgamma_key_levels":
        items = d.get("data", []) if isinstance(d, dict) else d
        rows = [{"ticker": it.get("sym", ""), "ts": it.get("trade_date", captured_at),
                 "payload": json.dumps(it, ensure_ascii=False),
                 "captured_at": captured_at, "source": src} for it in items]
        return "key_levels", rows
    if tool == "spotgamma_compass":
        ts = _first(d, "date", "timestamp") or captured_at if isinstance(d, dict) else captured_at
        row = {"ticker": _first(d, "ticker", "sym") or "SPX" if isinstance(d, dict) else "SPX",
               "ts": ts, "payload": payload, "captured_at": captured_at, "source": src}
        return "compass", [row]

    items = d if isinstance(d, list) else [d]
    rows = []
    for it in items:
        b = _base(tool, _first(it, "ticker", "sym") or "",
                  _first(it, "timestamp", "trade_date", "date") or captured_at, captured_at)
        b.pop("tool")
        rows.append({**b, "tool": tool,
                     "payload": json.dumps(it, ensure_ascii=False)})
    return "snapshots", rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/poller/test_normalize.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add poller/normalize.py tests/poller/test_normalize.py
git commit -m "feat: normalize MCP tool payloads into typed table rows"
```

---

### Task 3.5: CodeRabbit review gate #1

- [ ] **Step 1: Push and open PR**

```bash
git push -u origin main
gh pr create --fill --title "gex-poller tasks 1-3: scaffold, db, normalize" || true
```

(If working directly on `main`, push and let CodeRabbit review the PR; open the PR from a short-lived branch `poller/batch-1` if branch protection requires it.)

- [ ] **Step 2: Wait for CodeRabbit review, apply every finding or reply with justification, merge**

- [ ] **Step 3: Pull merged main before continuing**

```bash
git checkout main && git pull
```

---

### Task 4: `poller/mcp_client.py` — stdio JSON-RPC client

**Files:**
- Create: `poller/mcp_client.py`
- Create: `tests/poller/fake_mcp_server.py`
- Create: `tests/poller/conftest.py`
- Test: `tests/poller/test_mcp_client.py`

**Interfaces:**
- Consumes: `parse_tool_text`, `ToolResult` from `poller/normalize.py`.
- Produces:
  - `class McpClient(argv: list[str], cwd: str | None = None)` — context manager; on `__enter__` spawns process and handshakes; on `__exit__` kills it.
  - `McpClient.call_tool(name: str, arguments: dict) -> ToolResult` — raises `McpError` on JSON-RPC error or dead process.
  - `McpError(Exception)`.
  - `MENTHORQ_ARGV = [sys.executable, "mcp/menthorq_mcp.py"]`, `SPOTGAMMA_ARGV = ["node", "spotgamma-mcp/server.js"]` (repo-root relative).

- [ ] **Step 1: Write the fake server and conftest**

```python
# tests/poller/fake_mcp_server.py
"""Fake MCP stdio server: replays canned tool responses from FIXTURE env."""
import json
import os
import sys

FIXTURE = json.loads(os.environ.get("FAKE_MCP_FIXTURE", "{}"))

for line in sys.stdin:
    msg = json.loads(line)
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        out = {"jsonrpc": "2.0", "id": mid,
               "result": {"protocolVersion": "2024-11-05", "capabilities": {},
                          "serverInfo": {"name": "fake", "version": "0.0"}}}
    elif method == "notifications/initialized":
        continue
    elif method == "ping":
        out = {"jsonrpc": "2.0", "id": mid, "result": {}}
    elif method == "tools/call":
        name = msg["params"]["name"]
        if name in FIXTURE:
            out = {"jsonrpc": "2.0", "id": mid, "result":
                   {"content": [{"type": "text", "text": FIXTURE[name]}], "isError": False}}
        else:
            out = {"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32602, "message": f"unknown tool: {name}"}}
    else:
        out = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "nope"}}
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()
```

```python
# tests/poller/conftest.py
import json
import sys
from pathlib import Path

import pytest

FAKE_SERVER = str(Path(__file__).parent / "fake_mcp_server.py")


def pytest_addoption(parser):
    parser.addoption("--runlive", action="store_true", help="run live e2e tests")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runlive"):
        return
    skip = pytest.mark.skip(reason="needs --runlive")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def fake_mcp(monkeypatch):
    def _make(fixture: dict[str, str]):
        env_fixture = json.dumps(fixture)
        monkeypatch.setenv("FAKE_MCP_FIXTURE", env_fixture)
        from poller.mcp_client import McpClient
        return McpClient([sys.executable, FAKE_SERVER])
    return _make
```

- [ ] **Step 2: Write the failing test**

```python
# tests/poller/test_mcp_client.py
import json

import pytest

from poller.mcp_client import McpClient, McpError

pytestmark = pytest.mark.integration


def test_call_tool_success(fake_mcp):
    with fake_mcp({"menthorq_prices": json.dumps({"http_status": 200, "data": [1]})}) as c:
        r = c.call_tool("menthorq_prices", {"tickers": "SPX"})
        assert r.ok and r.data == [1] and r.http_status == 200


def test_unknown_tool_raises(fake_mcp):
    with fake_mcp({}) as c:
        with pytest.raises(McpError):
            c.call_tool("nope", {})


def test_dead_process_raises():
    with pytest.raises((McpError, OSError)):
        with McpClient(["/nonexistent/binary-xyz"]) as c:
            c.call_tool("x", {})
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/poller/test_mcp_client.py -v`
Expected: FAIL — `ModuleNotFoundError: poller.mcp_client`

- [ ] **Step 4: Implement `poller/mcp_client.py`**

```python
"""Minimal stdio JSON-RPC client for the gex-hub MCP servers."""
import json
import subprocess
import sys

from poller.normalize import ToolResult, parse_tool_text

MENTHORQ_ARGV = [sys.executable, "mcp/menthorq_mcp.py"]
SPOTGAMMA_ARGV = ["node", "spotgamma-mcp/server.js"]

_PROTOCOL = "2024-11-05"


class McpError(Exception):
    pass


class McpClient:
    def __init__(self, argv: list[str], cwd: str | None = None):
        self._argv, self._cwd = argv, cwd
        self._proc: subprocess.Popen | None = None
        self._next_id = 0

    def __enter__(self) -> "McpClient":
        try:
            self._proc = subprocess.Popen(
                self._argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, cwd=self._cwd)
        except OSError as e:
            raise McpError(f"spawn failed: {e}") from e
        self._rpc("initialize", {"protocolVersion": _PROTOCOL, "capabilities": {},
                                 "clientInfo": {"name": "gex-poller", "version": "0.1"}})
        self._rpc("notifications/initialized", is_notification=True)
        return self

    def __exit__(self, *exc) -> None:
        if self._proc:
            self._proc.kill()
            self._proc.wait()

    def _rpc(self, method: str, params: dict | None = None,
             is_notification: bool = False) -> dict:
        if not self._proc or self._proc.poll() is not None:
            raise McpError("server process is dead")
        self._next_id += 1
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not is_notification:
            msg["id"] = self._next_id
        assert self._proc.stdin and self._proc.stdout
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()
        if is_notification:
            return {}
        line = self._proc.stdout.readline()
        if not line:
            raise McpError("server closed stdout")
        return json.loads(line)

    def call_tool(self, name: str, arguments: dict) -> ToolResult:
        r = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if "error" in r:
            raise McpError(f"{name}: {r['error'].get('message')}")
        result = r.get("result", {})
        if result.get("isError"):
            text = result["content"][0]["text"] if result.get("content") else "isError"
            return ToolResult(name, ok=False, error=text[:300], raw=text)
        text = result["content"][0]["text"]
        return parse_tool_text(name, text)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/poller/test_mcp_client.py -v`
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add poller/mcp_client.py tests/poller/
git commit -m "feat: stdio JSON-RPC MCP client with fake-server integration tests"
```

---

### Task 5: `poller/schedule.py` — market-hours gate

**Files:**
- Create: `poller/schedule.py`
- Test: `tests/poller/test_schedule.py`

**Interfaces:**
- Produces: `in_market_window(now: datetime) -> bool` — True Mon–Fri, 13:30 ≤ UTC time < 20:00. Naive datetimes are treated as UTC.

- [ ] **Step 1: Write the failing test**

```python
# tests/poller/test_schedule.py
from datetime import datetime, timezone

import pytest

from poller.schedule import in_market_window

pytestmark = pytest.mark.unit
UTC = timezone.utc


@pytest.mark.parametrize("dt,expected", [
    (datetime(2026, 8, 3, 13, 30, tzinfo=UTC), True),   # Mon open edge
    (datetime(2026, 8, 3, 16, 0, tzinfo=UTC), True),    # Mon midday
    (datetime(2026, 8, 7, 19, 59, tzinfo=UTC), True),   # Fri before close
    (datetime(2026, 8, 7, 20, 0, tzinfo=UTC), False),   # Fri close edge
    (datetime(2026, 8, 3, 13, 29, tzinfo=UTC), False),  # before open
    (datetime(2026, 8, 8, 16, 0, tzinfo=UTC), False),   # Saturday
    (datetime(2026, 8, 9, 16, 0, tzinfo=UTC), False),   # Sunday
    (datetime(2026, 8, 4, 3, 0, tzinfo=UTC), False),    # overnight
])
def test_window(dt, expected):
    assert in_market_window(dt) is expected


def test_naive_treated_as_utc():
    assert in_market_window(datetime(2026, 8, 3, 16, 0)) is True
```

- [ ] **Step 2: Run, watch fail; implement; run, watch pass**

```python
# poller/schedule.py
"""Market-hours gate (US equities, UTC). Holiday check happens at runtime
via menthorq_market_status in poll.py."""
from datetime import datetime, time, timezone

_OPEN, _CLOSE = time(13, 30), time(20, 0)


def in_market_window(now: datetime) -> bool:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)
    return now.weekday() < 5 and _OPEN <= now.time() < _CLOSE
```

Run: `pytest tests/poller/test_schedule.py -v` → 2 PASS (9 param cases + naive)

- [ ] **Step 3: Commit**

```bash
git add poller/schedule.py tests/poller/test_schedule.py
git commit -m "feat: market-hours window gate"
```

---

### Task 6: `poller/observe.py` — logging, streak, notify, status

**Files:**
- Create: `poller/observe.py`
- Test: `tests/poller/test_observe.py`

**Interfaces:**
- Consumes: `init_db` conn shape from Task 2 (reads `scrape_runs`).
- Produces:
  - `class JsonlLogger(path, max_bytes=10_000_000)` — `.log(event: dict) -> None`; rotates to `path.1` when size exceeded.
  - `failure_streak(conn) -> int` — count of most recent consecutive cycles whose calls all errored or cycle has ≥1 error (cycle-level: any error counts as failed cycle).
  - `notify_macos(title: str, message: str, runner=subprocess.run) -> None` — injectable runner; swallows OSError.
  - `status_report(conn) -> dict` with keys `last_cycle`, `cycles_24h`, `failed_24h`, `freshness` (tool → minutes since last success), `last_errors` (≤5 strings).

- [ ] **Step 1: Write the failing test**

```python
# tests/poller/test_observe.py
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
```

- [ ] **Step 2: Run, watch fail (`ModuleNotFoundError: poller.observe`)**

- [ ] **Step 3: Implement `poller/observe.py`**

```python
"""Minimal observability: JSONL log, failure streak, macOS notify, status."""
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_STALE_MIN = 24 * 60


class JsonlLogger:
    def __init__(self, path: str | Path, max_bytes: int = 10_000_000):
        self.path, self.max_bytes = Path(path), max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: dict) -> None:
        if self.path.exists() and self.path.stat().st_size > self.max_bytes:
            self.path.replace(self.path.with_suffix(self.path.suffix + ".1"))
        event = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **event}
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
    now = datetime.now(timezone.utc)
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
```

- [ ] **Step 4: Run tests → 4 PASS**

- [ ] **Step 5: Commit**

```bash
git add poller/observe.py tests/poller/test_observe.py
git commit -m "feat: jsonl logging, failure streak, macOS notify, status report"
```

---

### Task 6.5: CodeRabbit review gate #2

- [ ] Push batch branch `poller/batch-2`, open PR, address all CodeRabbit findings, merge, pull main (same procedure as Task 3.5).

---

### Task 7: `poller/poll.py` — cycle orchestration + CLI

**Files:**
- Create: `poller/poll.py`
- Test: `tests/poller/test_poll.py`

**Interfaces:**
- Consumes: `McpClient`, `MENTHORQ_ARGV`, `SPOTGAMMA_ARGV` (Task 4); `to_rows` (Task 3); `db.*` (Task 2); `in_market_window` (Task 5); `JsonlLogger`, `failure_streak`, `notify_macos` (Task 6).
- Produces:
  - `CAPTURE: list[tuple[str, str, dict]]` — (client_key `"m"|"sg"`, tool, arguments).
  - `run_cycle(clients: dict[str, McpClient], conn, logger, now=None) -> dict` — returns `{"calls": int, "errors": int, "rows": int}`.
  - `main(argv: list[str] | None = None) -> int` — flags: `--once` (skip window gate), `--db PATH` (default `timeseries.db`), `--log PATH` (default `logs/poller.jsonl`).

`CAPTURE` (10 calls):

```python
CAPTURE = [
    ("m", "menthorq_market_status", {"exchange": "NYSE"}),
    ("m", "menthorq_gamma_levels", {"ticker": "SPX", "frequency": "eod"}),
    ("m", "menthorq_gamma_levels", {"ticker": "SPY", "frequency": "eod"}),
    ("m", "menthorq_dealer_positioning", {"ticker": "NVDA"}),
    ("m", "menthorq_put_call_ratio", {"ticker": "SPY", "frequency": "intraday"}),
    ("m", "menthorq_metrics_intraday", {"ticker": "SPX", "fields": ["iv_1m_50d", "skew_1m"], "limit": 3}),
    ("sg", "spotgamma_most_recent_market_open", {}),
    ("sg", "spotgamma_key_levels", {"include_gamma_curve": False}),
    ("sg", "spotgamma_equity_put_call_ratio", {}),
    ("sg", "spotgamma_zero_dte", {}),
]
```

- [ ] **Step 1: Write the failing test**

```python
# tests/poller/test_poll.py
import json
from datetime import datetime, timezone

import pytest

from poller.db import init_db
from poller.observe import JsonlLogger
from poller.poll import CAPTURE, run_cycle

pytestmark = pytest.mark.integration

FIX = {
    "menthorq_market_status": json.dumps({"http_status": 200, "data": {
        "exchange": "NYSE", "status": "open", "is_open": True,
        "date": "2026-08-03", "timestamp": "2026-08-03T16:00:00Z"}}),
    "menthorq_gamma_levels": json.dumps({"http_status": 200, "data": {
        "ticker": "SPX", "timestamp": "2026-08-03", "frequency": "eod",
        "gex_1": 7500, "gex_2": 7400, "gex_3": 7300}}),
    "menthorq_dealer_positioning": json.dumps({"http_status": 200, "data": {
        "reference_timestamp": "2026-08-03", "net_gex": 1.0, "net_dex": 2.0,
        "gex_dte_0_7d": 0.1, "gex_dte_8_30d": 0.2, "gex_dte_over_30d": 0.3}}),
    "menthorq_put_call_ratio": json.dumps({"http_status": 200, "data": {
        "timestamp": "2026-08-03T16:00:00Z", "volume_calls": 10,
        "volume_puts": 5, "put_call_ratio": 0.5}}),
    "menthorq_metrics_intraday": json.dumps({"http_status": 200, "data":
        [{"timestamp": "2026-08-03T16:00:00Z", "iv_1m_50d": 0.2}]}),
    "spotgamma_most_recent_market_open": '[{"sym": "SPX", "price": 7468.65, "date": "2026-07-31"}]',
    "spotgamma_key_levels": json.dumps({"data": [
        {"sym": "SPX", "trade_date": "2026-07-30T00:00:00.000Z", "levels_with_pct": "[]"}]}),
    "spotgamma_equity_put_call_ratio": json.dumps({
        "timestamp": "2026-07-31", "volume_calls": 1, "volume_puts": 2, "put_call_ratio": 2.0}),
    "spotgamma_zero_dte": '[{"sym": "SPX", "date": "2026-07-31"}]',
}


def _clients(fake_mcp):
    return {"m": fake_mcp(FIX).__enter__(), "sg": fake_mcp(FIX).__enter__()}


def test_run_cycle_writes_all_families(fake_mcp, tmp_path):
    conn = init_db(tmp_path / "t.db")
    clients = _clients(fake_mcp)
    rep = run_cycle(clients, conn, JsonlLogger(tmp_path / "l.jsonl"),
                    now=datetime(2026, 8, 3, 16, 0, tzinfo=timezone.utc))
    assert rep["errors"] == 0 and rep["calls"] == len(CAPTURE)
    for t in ("gamma_levels", "dealer_positioning", "key_levels",
              "put_call_ratio", "snapshots"):
        assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] >= 1


def test_run_cycle_records_errors_and_continues(fake_mcp, tmp_path):
    broken = dict(FIX, spotgamma_zero_dte="Error: unauthorized")
    conn = init_db(tmp_path / "t.db")
    clients = {"m": fake_mcp(broken).__enter__(), "sg": fake_mcp(broken).__enter__()}
    rep = run_cycle(clients, conn, JsonlLogger(tmp_path / "l.jsonl"),
                    now=datetime(2026, 8, 3, 16, 0, tzinfo=timezone.utc))
    assert rep["errors"] == 1
    errs = conn.execute("SELECT COUNT(*) FROM scrape_runs WHERE error IS NOT NULL").fetchone()[0]
    assert errs == 1
```

- [ ] **Step 2: Run, watch fail (`ModuleNotFoundError: poller.poll`)**

- [ ] **Step 3: Implement `poller/poll.py`**

```python
"""One polling cycle: call core MCP tools, normalize, store, audit."""
import argparse
import sys
from datetime import datetime, timezone

from poller.db import begin_cycle, finish_cycle, init_db, insert_rows, record_call
from poller.mcp_client import MENTHORQ_ARGV, SPOTGAMMA_ARGV, McpClient, McpError
from poller.normalize import to_rows
from poller.observe import JsonlLogger, failure_streak, notify_macos
from poller.schedule import in_market_window

CAPTURE = [
    ("m", "menthorq_market_status", {"exchange": "NYSE"}),
    ("m", "menthorq_gamma_levels", {"ticker": "SPX", "frequency": "eod"}),
    ("m", "menthorq_gamma_levels", {"ticker": "SPY", "frequency": "eod"}),
    ("m", "menthorq_dealer_positioning", {"ticker": "NVDA"}),
    ("m", "menthorq_put_call_ratio", {"ticker": "SPY", "frequency": "intraday"}),
    ("m", "menthorq_metrics_intraday", {"ticker": "SPX",
                                        "fields": ["iv_1m_50d", "skew_1m"], "limit": 3}),
    ("sg", "spotgamma_most_recent_market_open", {}),
    ("sg", "spotgamma_key_levels", {"include_gamma_curve": False}),
    ("sg", "spotgamma_equity_put_call_ratio", {}),
    ("sg", "spotgamma_zero_dte", {}),
]


def run_cycle(clients: dict[str, McpClient], conn, logger: JsonlLogger,
              now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    cap = now.isoformat(timespec="seconds")
    calls = errors = rows_total = 0
    cid = begin_cycle(conn, "poller")
    for key, tool, args in CAPTURE:
        calls += 1
        try:
            result = clients[key].call_tool(tool, args)
            table, rows = to_rows(tool, result, cap)
            written = insert_rows(conn, table, rows)
            record_call(conn, cid, tool, result.http_status, written, None)
            rows_total += written
        except (McpError, ValueError, KeyError) as e:
            errors += 1
            record_call(conn, cid, tool, None, 0, str(e)[:300])
    finish_cycle(conn, cid)
    logger.log({"event": "cycle", "calls": calls, "errors": errors, "rows": rows_total})
    return {"calls": calls, "errors": errors, "rows": rows_total}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gex-poller")
    p.add_argument("--once", action="store_true", help="ignore market-hours gate")
    p.add_argument("--db", default="timeseries.db")
    p.add_argument("--log", default="logs/poller.jsonl")
    ns = p.parse_args(argv)

    if not ns.once and not in_market_window(datetime.now(timezone.utc)):
        return 0

    logger = JsonlLogger(ns.log)
    conn = init_db(ns.db)
    try:
        with McpClient(MENTHORQ_ARGV) as m, McpClient(SPOTGAMMA_ARGV) as sg:
            rep = run_cycle({"m": m, "sg": sg}, conn, logger)
    except McpError as e:
        logger.log({"event": "spawn_failure", "error": str(e)[:300]})
        return 1
    if failure_streak(conn) >= 3:
        notify_macos("gex-poller", "3 consecutive failed cycles — check logs/poller.jsonl")
    return 0 if rep["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests → 2 PASS**

- [ ] **Step 5: Commit**

```bash
git add poller/poll.py tests/poller/test_poll.py
git commit -m "feat: polling cycle orchestration with per-call audit and CLI"
```

---

### Task 8: `poller/status.py` — status CLI

**Files:**
- Create: `poller/status.py`
- Test: `tests/poller/test_status.py`

**Interfaces:**
- Consumes: `status_report` (Task 6), `init_db` (Task 2).
- Produces: `main(argv: list[str] | None = None) -> int` — `--db PATH` (default `timeseries.db`); prints human-readable report.

- [ ] **Step 1: Write the failing test**

```python
# tests/poller/test_status.py
import pytest

from poller.db import begin_cycle, init_db, record_call
from poller.status import main

pytestmark = pytest.mark.integration


def test_status_prints_summary(tmp_path, capsys):
    db = tmp_path / "t.db"
    conn = init_db(db)
    c = begin_cycle(conn, "poller")
    record_call(conn, c, "menthorq_prices", 200, 3, None)
    conn.close()
    assert main(["--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert "cycles (24h): 1" in out and "failed: 0" in out
    assert "menthorq_prices" in out
```

- [ ] **Step 2: Run, watch fail; implement:**

```python
# poller/status.py
"""Print poller health summary from scrape_runs."""
import argparse

from poller.db import init_db
from poller.observe import status_report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gex-poller-status")
    p.add_argument("--db", default="timeseries.db")
    ns = p.parse_args(argv)
    rep = status_report(init_db(ns.db))
    print(f"cycles (24h): {rep['cycles_24h']}  failed: {rep['failed_24h']}"
          f"  last cycle: {rep['last_cycle']}")
    for tool, mins in sorted(rep["freshness"].items()):
        print(f"  {tool:<40} last ok {mins} min ago")
    if rep["last_errors"]:
        print("recent errors:")
        for e in rep["last_errors"]:
            print(f"  - {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `pytest tests/poller/test_status.py -v` → 1 PASS

- [ ] **Step 3: Commit**

```bash
git add poller/status.py tests/poller/test_status.py
git commit -m "feat: poller status CLI"
```

---

### Task 9: LaunchAgent plist + install docs + plist validation test

**Files:**
- Create: `poller/com.gexhub.poller.plist`
- Create: `tests/poller/test_plist.py`
- Modify: `docs/RUNBOOK.md` (append poller section)

**Interfaces:**
- Produces: LaunchAgent label `com.gexhub.poller`, `StartInterval` 900, runs `python3 -m poller.poll` from repo root, stdout/stderr → `logs/launchagent.log`.

- [ ] **Step 1: Write the failing test**

```python
# tests/poller/test_plist.py
import plistlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLIST = Path(__file__).parents[2] / "poller" / "com.gexhub.poller.plist"


def test_plist_valid_and_complete():
    d = plistlib.loads(PLIST.read_bytes())
    assert d["Label"] == "com.gexhub.poller"
    assert d["StartInterval"] == 900
    assert d["ProgramArguments"][:2] == ["/usr/bin/env", "python3"]
    assert "-m" in d["ProgramArguments"] and "poller.poll" in d["ProgramArguments"]
    assert d["WorkingDirectory"].endswith("gex-hub")
    assert "StandardOutPath" in d and "StandardErrorPath" in d
```

- [ ] **Step 2: Run, watch fail (file missing)**

- [ ] **Step 3: Create `poller/com.gexhub.poller.plist`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.gexhub.poller</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>python3</string>
    <string>-m</string>
    <string>poller.poll</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/filipesalvio/gex-hub</string>
  <key>StartInterval</key><integer>900</integer>
  <key>StandardOutPath</key><string>/Users/filipesalvio/gex-hub/logs/launchagent.log</string>
  <key>StandardErrorPath</key><string>/Users/filipesalvio/gex-hub/logs/launchagent.log</string>
</dict>
</plist>
```

- [ ] **Step 4: Append to `docs/RUNBOOK.md`**

```markdown
## gex-poller

Install:  `cp poller/com.gexhub.poller.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.gexhub.poller.plist`
Remove:   `launchctl unload ~/Library/LaunchAgents/com.gexhub.poller.plist`
One shot: `python3 -m poller.poll --once`
Status:   `python3 -m poller.status`
Logs:     `logs/poller.jsonl` (cycles), `logs/launchagent.log` (stdout/stderr)
```

- [ ] **Step 5: Run test → 1 PASS; commit**

```bash
git add poller/com.gexhub.poller.plist tests/poller/test_plist.py docs/RUNBOOK.md
git commit -m "feat: LaunchAgent schedule for 15-min polling + runbook"
```

---

### Task 9.5: CodeRabbit review gate #3

- [ ] Push batch branch `poller/batch-3`, open PR, address all CodeRabbit findings, merge, pull main (same procedure as Task 3.5).

---

### Task 10: Live e2e + CI coverage gates + README

**Files:**
- Create: `tests/poller/test_e2e_live.py`
- Modify: `.github/workflows/ci.yml` (coverage gates)
- Modify: `README.md` (poller bullet)

**Interfaces:**
- Consumes: everything. Exercises ≥4 of 10 capture tools live (40% e2e floor).

- [ ] **Step 1: Write the live test (skipped without `--runlive`)**

```python
# tests/poller/test_e2e_live.py
import pytest

from poller.db import init_db
from poller.mcp_client import MENTHORQ_ARGV, SPOTGAMMA_ARGV, McpClient
from poller.observe import JsonlLogger
from poller.poll import CAPTURE, run_cycle

pytestmark = pytest.mark.live


def test_live_cycle(tmp_path):
    conn = init_db(tmp_path / "live.db")
    with McpClient(MENTHORQ_ARGV) as m, McpClient(SPOTGAMMA_ARGV) as sg:
        rep = run_cycle({"m": m, "sg": sg}, conn, JsonlLogger(tmp_path / "l.jsonl"))
    ok = conn.execute("SELECT COUNT(*) FROM scrape_runs WHERE error IS NULL").fetchone()[0]
    assert ok >= len(CAPTURE) * 0.4, f"only {ok}/{len(CAPTURE)} tools succeeded"
    assert rep["rows"] > 0
```

- [ ] **Step 2: Run live**

Run: `pytest tests/poller/test_e2e_live.py --runlive -v`
Expected: 1 PASS (requires bridge daemon up; if SpotGamma token absent, MenthorQ calls alone satisfy the 40% floor)

- [ ] **Step 3: Add coverage gates to `.github/workflows/ci.yml`** (append job steps after existing pytest step)

```yaml
      - name: Unit coverage gate (100%)
        run: |
          pytest -m unit --cov=poller.normalize --cov=poller.schedule \
                 --cov=poller.db --cov=poller.observe --cov-fail-under=100 -q
      - name: Integration coverage gate (80%)
        run: pytest -m "unit or integration" --cov=poller --cov-fail-under=80 -q
```

- [ ] **Step 4: README bullet** under "What you get":

```markdown
- `gex-poller` — LaunchAgent-scheduled capture of core tools into `timeseries.db` (`python3 -m poller.poll --once`, status via `python3 -m poller.status`)
```

- [ ] **Step 5: Full local verification**

Run: `pytest -q && ruff check poller tests && pytest tests/poller/test_e2e_live.py --runlive -q`
Expected: all PASS, no lint findings.

- [ ] **Step 6: Commit and push**

```bash
git add tests/poller/test_e2e_live.py .github/workflows/ci.yml README.md
git commit -m "test: live e2e cycle + CI coverage gates (100/80/40)"
git push
```

---

## Self-Review Notes

- Spec coverage: capture set ✓ (Task 7 CAPTURE), schema ✓ (Task 2), scheduling ✓ (Tasks 5+9), error handling ✓ (Tasks 2/7 fail-closed + per-call transactions), observability ✓ (Task 6), coverage targets ✓ (Tasks 1/10), CodeRabbit every 3 tasks ✓ (gates 3.5/6.5/9.5), live smoke ✓ (Task 10).
- Type consistency: `ToolResult.raw` added so `to_rows` can embed original payload; `begin_cycle` returns cycle_id used by `record_call`/`finish_cycle`; `status_report` keys match `status.py` output and Task 6 test.
- Deviation from design doc: `metrics_intraday`, `market_status`, `zero_dte`, `most_recent_market_open` land in a generic `snapshots` table instead of dedicated typed tables (shapes are lists/open-ended); the 5 design-doc typed tables are unchanged.
