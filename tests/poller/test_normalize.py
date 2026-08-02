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


def test_gamma_levels_missing_timestamp_raises_valueerror():
    r = parse_tool_text("menthorq_gamma_levels", _env(
        {"ticker": "SPX", "frequency": "eod", "gex_1": 7500}))
    with pytest.raises(ValueError, match="missing required field 'timestamp'"):
        to_rows("menthorq_gamma_levels", r, CAP)


def test_gamma_levels_missing_frequency_raises_valueerror():
    r = parse_tool_text("menthorq_gamma_levels", _env(
        {"ticker": "SPX", "timestamp": "2026-08-01"}))
    with pytest.raises(ValueError, match="missing required field 'frequency'"):
        to_rows("menthorq_gamma_levels", r, CAP)


def test_dealer_positioning_missing_reference_timestamp_raises_valueerror():
    r = parse_tool_text("menthorq_dealer_positioning", _env(
        {"ticker": "SPX", "net_gex": 1.0}))
    with pytest.raises(ValueError, match="missing required field 'reference_timestamp'"):
        to_rows("menthorq_dealer_positioning", r, CAP)


def test_dealer_positioning_row_maps_optional_fields():
    r = parse_tool_text("menthorq_dealer_positioning", _env(
        {"ticker": "SPX", "reference_timestamp": "2026-08-01T00:00:00Z",
         "net_gex": 1.5, "net_dex": -0.5}))
    table, rows = to_rows("menthorq_dealer_positioning", r, CAP)
    assert table == "dealer_positioning"
    assert rows[0]["ts"] == "2026-08-01T00:00:00Z"
    assert rows[0]["net_gex"] == 1.5 and rows[0]["gex_dte_0_7d"] is None


def test_dealer_positioning_null_ticker_raises_valueerror():
    r = parse_tool_text("menthorq_dealer_positioning", _env(
        {"ticker": None, "reference_timestamp": "2026-08-01T00:00:00Z"}))
    with pytest.raises(ValueError, match="ticker"):
        to_rows("menthorq_dealer_positioning", r, CAP)


def test_dealer_positioning_missing_ticker_raises_valueerror():
    r = parse_tool_text("menthorq_dealer_positioning", _env(
        {"reference_timestamp": "2026-08-01T00:00:00Z"}))
    with pytest.raises(ValueError, match="ticker"):
        to_rows("menthorq_dealer_positioning", r, CAP)


def test_dealer_positioning_blank_ticker_raises_valueerror():
    r = parse_tool_text("menthorq_dealer_positioning", _env(
        {"ticker": "  ", "reference_timestamp": "2026-08-01T00:00:00Z"}))
    with pytest.raises(ValueError, match="ticker"):
        to_rows("menthorq_dealer_positioning", r, CAP)


def test_gamma_levels_null_timestamp_raises_valueerror():
    r = parse_tool_text("menthorq_gamma_levels", _env(
        {"ticker": "SPX", "frequency": "eod", "timestamp": None}))
    with pytest.raises(ValueError, match="timestamp"):
        to_rows("menthorq_gamma_levels", r, CAP)
