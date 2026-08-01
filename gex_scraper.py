#!/usr/bin/env python3
"""SpotGamma GEX scraper.

Pulls gamma-exposure data from the SpotGamma dashboard API and stores it in SQLite:

  - GET /home/keyLevels?includeGammaCurve=1  -> table `key_levels`   (SPX walls, zero-gamma, gamma curve)
  - GET /v4/equities                          -> table `equities_gex` (per-symbol GEX for ~5k symbols)

Auth: static app headers (hardcoded in the dashboard bundle) + the user's
`sgToken` session token sent as `Authorization: Bearer ...`. The token comes
from the `$SG_TOKEN` env var or is captured live from an open, logged-in
SpotGamma dashboard tab through the local Kimi WebBridge daemon; it is never
written to disk. Tokens expire every few days; when a request comes back
401/403 (or the token is near expiry) the scraper tries to refresh it
automatically through WebBridge.

Stdlib only — runs anywhere, including the Kimi Work managed Python runtime.

CLI:
  python3 gex_scraper.py                      # full scrape into ./gex_data.db
  python3 gex_scraper.py --skip-equities      # key levels only
  python3 gex_scraper.py --db other.db        # different database file
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime

BASE_URL = "https://api.spotgamma.com"
DASHBOARD_URL = "https://dashboard.spotgamma.com/home"
WEBBRIDGE_URL = "http://127.0.0.1:10086/command"
WEBBRIDGE_SESSION = "gex-scraper"

STATIC_HEADERS = {
    "x-json-web-token": (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJpYXQiOjE2NjgxMjgyNDJ9."
        "0VtbQW99MELrgb4JW56xtbRdh1LAbDBlB1T78dJlILA"
    ),
    "Content-Type": "application/json",
    "Version": "5613",
    "App-Type": "web",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(SCRIPT_DIR, "gex_data.db")

# Refresh the token proactively when it has less than this much lifetime left.
TOKEN_REFRESH_MARGIN_S = 6 * 3600

log = logging.getLogger("gex_scraper")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

# Scalar columns curated from the observed /home/keyLevels record.
KEY_LEVELS_COLS = [
    "sym", "trade_date", "upx",
    "callwallstrike", "putwallstrike", "callwallgam", "putwallgam",
    "zero_g_strike", "max_g_strike", "topabs_strike", "gamma_not",
    "atm_g_calls", "atm_g_puts", "atm_d_calls", "atm_d_puts", "itm_d",
    "atm_Theta", "atm_Vega", "atm_g_c_n", "atm_g_p_n",
    "rr", "sig", "sig5",
    "L1", "L2", "L3", "L4", "C1", "C2", "C3", "C4",
    "calls_OI", "puts_OI", "calls_vol", "puts_vol",
    "futuresDiff", "futuresSym", "rowno",
    "keyLevelTradeDate", "gammaTradeDate",
    # JSON-serialized list fields
    "levels_with_pct", "strike_list", "current_list", "next_exp_list",
]

# Scalar columns curated from the observed /v4/equities record (list/array
# fields are kept only inside raw_json).
EQUITIES_COLS = [
    "sym", "name", "trade_date", "quote_date", "date",
    "upx", "callsum", "putsum", "minfs", "maxfs",
    "keyd", "keyg", "cws", "pws",
    "prev_cws", "prev_pws", "prev_keyg", "prev_maxfs",
    "largeCoi", "largePoi",
    "next_exp_call_gamma", "next_exp_put_gamma", "next_exp_g", "next_exp_d",
    "max_exp_g_date", "max_exp_d_date",
    "atmgc", "atmgp", "atmdc", "atmdp",
    "pv", "cv", "d95ne", "d25ne", "d95", "d25",
    "putctrl", "activity_factor", "position_factor",
    "total_volume", "stock_volume", "stock_volume_30d_avg",
    "dpi", "dpi_high52w", "dpi_low52w", "dpi_sector", "dpi_volume",
    "put_call_ratio", "volume_ratio", "gamma_ratio", "delta_ratio", "totaldelta",
    "ne_skew", "skew", "cskew", "pskew", "cskew_pct", "pskew_pct",
    "options_implied_move", "atm_iv30", "atm_iv30_pct_chg",
    "rv30", "fwd_garch", "iv_pct", "iv_rank", "skew_rank",
    "garch_rank", "garch_scanner", "vrp_scanner", "vrp_scanner_high",
    "squeeze_scanner", "ne_call_volume", "ne_put_volume",
    "sig", "iv_slope_ne_45", "ne_date", "earnings_utc", "tca_score",
]

DDL = """
CREATE TABLE IF NOT EXISTS key_levels (
    sym          TEXT NOT NULL,
    trade_date   TEXT NOT NULL,
    pulled_at    TEXT NOT NULL,
    raw_json     TEXT NOT NULL,
    PRIMARY KEY (sym, trade_date)
);
CREATE TABLE IF NOT EXISTS equities_gex (
    sym          TEXT NOT NULL,
    trade_date   TEXT NOT NULL,
    pulled_at    TEXT NOT NULL,
    raw_json     TEXT NOT NULL,
    PRIMARY KEY (sym, trade_date)
);
CREATE TABLE IF NOT EXISTS scrape_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at      TEXT NOT NULL,
    endpoint    TEXT NOT NULL,
    status      TEXT NOT NULL,
    http_status INTEGER,
    rows        INTEGER,
    message     TEXT
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    # Add curated columns idempotently; ignore "duplicate column" errors.
    for table, cols in (("key_levels", KEY_LEVELS_COLS), ("equities_gex", EQUITIES_COLS)):
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for col in cols:
            if col in existing:
                continue
            conn.execute(f'ALTER TABLE {table} ADD COLUMN "{col}"')
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Token handling
# ---------------------------------------------------------------------------

def _jwt_exp(token: str) -> int | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return int(json.loads(base64.urlsafe_b64decode(payload))["exp"])
    except Exception:
        return None


def token_needs_refresh(token: str | None) -> bool:
    if not token:
        return True
    exp = _jwt_exp(token)
    if exp is None:
        return False  # unknown format; try as-is
    return exp - time.time() < TOKEN_REFRESH_MARGIN_S


def _webbridge_call(action: str, args: dict, timeout: float = 15.0) -> dict:
    body = json.dumps({"action": action, "args": args, "session": WEBBRIDGE_SESSION}).encode()
    req = urllib.request.Request(
        WEBBRIDGE_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def refresh_token_via_webbridge(timeout: float = 15.0) -> str | None:
    """Pull a fresh sgToken from the user's browser via the WebBridge daemon.

    Requires the Kimi WebBridge daemon + browser extension to be running and the
    user to be logged in to the SpotGamma dashboard. Best-effort: returns the
    token string only (never written to disk); returns None on any failure.
    """
    try:
        found = _webbridge_call("find_tab", {"url": DASHBOARD_URL}, timeout)
        if not (found.get("ok") and found.get("data", {}).get("success")):
            log.info("WebBridge: opening SpotGamma dashboard tab for token refresh")
            _webbridge_call(
                "navigate",
                {"url": DASHBOARD_URL, "newTab": True, "group_title": "GEX scraper"},
                timeout,
            )
            time.sleep(5)
        deadline = time.time() + 30
        while time.time() < deadline:
            out = _webbridge_call(
                "evaluate", {"code": 'localStorage.getItem("sgToken")'}, timeout
            )
            token = (out.get("data") or {}).get("value")
            if isinstance(token, str) and token.count(".") == 2:
                log.info("WebBridge: token refreshed")
                return token
            time.sleep(2)
        log.warning("WebBridge: dashboard tab did not yield a token in time")
    except Exception as exc:  # daemon down, browser closed, etc.
        log.warning("WebBridge token refresh failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

class ApiError(Exception):
    def __init__(self, status: int | None, message: str):
        super().__init__(message)
        self.status = status


def fetch_json(path: str, token: str, timeout: float = 30.0) -> object:
    url = f"{BASE_URL}/{path}"
    headers = dict(STATIC_HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read()[:300].decode("utf-8", "replace")
        except Exception:
            pass
        raise ApiError(exc.code, f"GET {path} -> HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(None, f"GET {path} -> {exc.reason}") from exc


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def upsert_rows(conn: sqlite3.Connection, table: str, cols: list[str],
                records: list[dict]) -> int:
    if not records:
        return 0
    pulled_at = utc_now()
    known = [c for c in cols if c in records[0]]
    all_cols = known + ["pulled_at", "raw_json"]
    placeholders = ", ".join("?" for _ in all_cols)
    col_list = ", ".join(f'"{c}"' for c in all_cols)
    sql = f'INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})'
    rows = [
        [rec.get(c) for c in known] + [pulled_at, json.dumps(rec, separators=(",", ":"))]
        for rec in records
    ]
    conn.executemany(sql, rows)
    return len(rows)


def log_run(conn: sqlite3.Connection, endpoint: str, status: str,
            http_status: int | None, rows: int | None, message: str = "") -> None:
    conn.execute(
        "INSERT INTO scrape_runs (run_at, endpoint, status, http_status, rows, message)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (utc_now(), endpoint, status, http_status, rows, message[:500]),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Main scrape
# ---------------------------------------------------------------------------

def run(db_path: str = DEFAULT_DB,
        include_gamma_curve: bool = True,
        do_key_levels: bool = True,
        do_equities: bool = True,
        timeout: float = 60.0) -> dict:
    """Run one scrape. Returns a JSON-serializable summary dict.

    Raises RuntimeError only when nothing could be scraped at all.
    """
    started = utc_now()
    conn = init_db(db_path)

    token = os.environ.get("SG_TOKEN", "").strip() or None
    token_refreshed = False
    if token_needs_refresh(token):
        log.info("Token missing or near expiry — attempting WebBridge refresh")
        fresh = refresh_token_via_webbridge()
        if fresh:
            token, token_refreshed = fresh, True

    if not token:
        conn.close()
        raise RuntimeError(
            "No sgToken available. Set $SG_TOKEN, or keep Chrome logged in to "
            "https://dashboard.spotgamma.com/home for WebBridge capture."
        )

    summary: dict = {
        "status": "ok",
        "ran_at": started,
        "db_path": db_path,
        "token_refreshed": token_refreshed,
        "trade_date": None,
        "key_levels_rows": 0,
        "equities_rows": 0,
        "errors": [],
    }

    jobs = []
    if do_key_levels:
        jobs.append(("key_levels", f"home/keyLevels?includeGammaCurve={1 if include_gamma_curve else 0}"))
    if do_equities:
        jobs.append(("equities_gex", "v4/equities"))

    for table, path in jobs:
        for attempt in (1, 2):  # second attempt only after a token refresh
            try:
                payload = fetch_json(path, token, timeout)
                records = payload.get("data") if isinstance(payload, dict) else payload
                if not isinstance(records, list):
                    raise ApiError(None, f"unexpected payload shape: {type(payload).__name__}")
                cols = KEY_LEVELS_COLS if table == "key_levels" else EQUITIES_COLS
                n = upsert_rows(conn, table, cols, records)
                conn.commit()
                log_run(conn, path, "ok", 200, n)
                if table == "key_levels":
                    summary["key_levels_rows"] = n
                    if records:
                        summary["trade_date"] = records[0].get("trade_date")
                else:
                    summary["equities_rows"] = n
                    if not summary["trade_date"] and records:
                        summary["trade_date"] = records[0].get("trade_date")
                log.info("%s -> %d rows", path, n)
                break
            except ApiError as exc:
                if exc.status in (401, 403) and attempt == 1:
                    log.warning("%s returned HTTP %s — refreshing token and retrying", path, exc.status)
                    fresh = refresh_token_via_webbridge()
                    if fresh:
                        token = fresh
                        summary["token_refreshed"] = True
                        continue
                summary["errors"].append({"endpoint": path, "error": str(exc)})
                log_run(conn, path, "error", exc.status, None, str(exc))
                log.error("%s failed: %s", path, exc)
                break

    if summary["errors"] and summary["key_levels_rows"] + summary["equities_rows"] == 0:
        summary["status"] = "error"
    elif summary["errors"]:
        summary["status"] = "partial"

    total_kl = conn.execute("SELECT COUNT(*) FROM key_levels").fetchone()[0]
    total_eq = conn.execute("SELECT COUNT(*) FROM equities_gex").fetchone()[0]
    summary["db_key_levels_total"] = total_kl
    summary["db_equities_total"] = total_eq
    conn.close()

    if summary["status"] == "error":
        raise RuntimeError(json.dumps(summary))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SpotGamma GEX scraper -> SQLite")
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite database path")
    parser.add_argument("--include-gamma-curve", type=int, default=1, choices=(0, 1))
    parser.add_argument("--skip-key-levels", action="store_true")
    parser.add_argument("--skip-equities", action="store_true")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        summary = run(
            db_path=args.db,
            include_gamma_curve=bool(args.include_gamma_curve),
            do_key_levels=not args.skip_key_levels,
            do_equities=not args.skip_equities,
            timeout=args.timeout,
        )
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
