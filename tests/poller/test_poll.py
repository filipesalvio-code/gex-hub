import json
from datetime import UTC, datetime

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
        "ticker": "NVDA", "reference_timestamp": "2026-08-03", "net_gex": 1.0,
        "net_dex": 2.0, "gex_dte_0_7d": 0.1, "gex_dte_8_30d": 0.2,
        "gex_dte_over_30d": 0.3}}),
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

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)


def test_run_cycle_writes_all_families(fake_mcp, tmp_path):
    conn = init_db(tmp_path / "t.db")
    with fake_mcp(FIX) as m, fake_mcp(FIX) as sg:
        rep = run_cycle({"m": m, "sg": sg}, conn,
                        JsonlLogger(tmp_path / "l.jsonl"), now=NOW)
    assert rep["errors"] == 0 and rep["calls"] == len(CAPTURE)
    for t in ("gamma_levels", "dealer_positioning", "key_levels",
              "put_call_ratio", "snapshots"):
        assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] >= 1


def test_run_cycle_records_errors_and_continues(fake_mcp, tmp_path):
    broken = dict(FIX, spotgamma_zero_dte="Error: unauthorized")
    conn = init_db(tmp_path / "t.db")
    with fake_mcp(broken) as m, fake_mcp(broken) as sg:
        rep = run_cycle({"m": m, "sg": sg}, conn,
                        JsonlLogger(tmp_path / "l.jsonl"), now=NOW)
    assert rep["errors"] == 1
    errs = conn.execute("SELECT COUNT(*) FROM scrape_runs WHERE error IS NOT NULL").fetchone()[0]
    assert errs == 1
