"""One polling cycle: call core MCP tools, normalize, store, audit."""
import argparse
import sqlite3
import sys
from datetime import UTC, datetime

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
    ("sg", "spotgamma_compass", {}),
    ("sg", "spotgamma_equity_put_call_ratio", {}),
    ("sg", "spotgamma_zero_dte", {}),
]


def run_cycle(clients: dict[str, McpClient], conn, logger: JsonlLogger,
              now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
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
        except (McpError, ValueError, KeyError, OSError, sqlite3.Error) as e:
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

    if not ns.once and not in_market_window(datetime.now(UTC)):
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
