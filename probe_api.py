#!/usr/bin/env python3
"""One-shot probe of SpotGamma endpoints with SPX examples -> probes.json."""
import json
import os
import urllib.error
import urllib.request

import gex_scraper as gs

DATE = "2026-07-23"
ES = "S%26P%20ES%3DF"

PROBES = [
    # core GEX
    ("home/keyLevels?includeGammaCurve=1", "json"),
    ("home/allData", "json"),
    (f"v3/equitiesBySyms?syms=SPX&date={DATE}", "json"),
    ("v4/equities", "json-spx"),
    (f"v4/historical?sym=SPX", "json"),
    ("v2/comboLevels?sym=SPX", "json"),
    ("v2/comboLevels?sym=SPX&model=next_exp", "json"),
    ("absGammaLevels?sym=SPX", "json"),
    ("v1/zeroDTE?sym=SPX", "json"),
    # greeks / skew
    ("v2/latest_greeks?sym=SPX", "json"),
    (f"v2/daily_greeks?sym=SPX&date={DATE}", "json"),
    ("v2/skew?sym=SPX", "json"),
    ("v1/tilt?sym=SPX", "json"),
    ("v1/optionsRiskReversal?sym=SPX", "json"),
    ("v1/rr?sym=SPX", "json"),
    ("v1/iv_stats?sym=SPX", "json"),
    # open interest
    (f"v2/open_interest/intraday_stats?sym=SPX&date={DATE}", "json"),
    (f"v2/open_interest/intraday_gamma?symbol=SPX&date={DATE}", "json"),
    (f"v2/open_interest/intraday_delta?symbol=SPX&date={DATE}", "json"),
    (f"v2/open_interest/intraday_strike_bars?symbol=SPX&bar_type=gamma&date={DATE}", "json"),
    (f"v2/open_interest/intraday_timestamps?symbol=SPX&greek=gamma&date={DATE}", "json"),
    ("v1/oi?sym=SPX", "raw"),
    ("v1/oi_syms", "json"),
    ("v1/concentration?syms=SPX&groupBy=strike", "json"),
    ("v1/concentration?syms=SPX&groupBy=expiration", "json"),
    (f"synth_oi/v1/equities?date={DATE}", "json-spx"),
    (f"synth_oi/v1/chart_data?sym=SPX&date={DATE}", "json"),
    ("synth_oi/v1/last_update", "text"),
    ("synth_oi/v1/eh_symbols", "count"),
    ("v1/eh_symbols", "count"),
    # HIRO
    ("v6/running_hiro", "json-spx"),
    (f"v11/hiro?all=1&nextExp=1&retail=1&syms=SPX&start={DATE}&end={DATE}", "json"),
    ("v4/latestHiro?syms=SPX&all=1&limit=10", "json"),
    # market data
    ("v1/prices?syms=SPX", "json"),
    ("v1/twelve_quote?symbol=SPX", "json"),
    ("v1/twelve_series?symbol=SPX&interval=1day&start_date=2026-07-20&order=asc", "json"),
    (f"v1/futures?sym={ES}", "json"),
    (f"v1/futures/realtime?sym={ES}", "json"),
    ("v1/futures/mostRecentMarketOpen", "json"),
    (f"v1/treasury_rates?date={DATE}", "json"),
    (f"v1/dividends?sym=SPX&start=2026-07-01&end=2026-08-01", "json"),
    ("v1/equityPutCallRatio", "json"),
    ("v1/correlation_regime?sym=SPX", "json"),
    ("v3/trending?", "json"),
    (f"vix_quote?dates={DATE}", "json"),
    # scanners / compass / alerts / calendars
    (f"v1/earnings?syms=SPX", "json"),
    ("v1/fmp/api/v3/economic_calendar?from=2026-07-24&to=2026-07-31", "json"),
    ("v1/equityScanners", "count"),
    ("v1/compass?syms=SPX&x=price", "json"),
    ("v1/compass_hist?syms=SPX&lookback=30", "json"),
    (f"v1/alerts?syms=SPX&start={DATE}&end=2026-07-24", "json"),
    # infra / auth (GET only)
    ("status", "json"),
    ("validate_bearer", "json"),
    ("sg/manifest", "json"),
    # content
    ("foundersNotes?page=1&perPage=2", "json"),
]


def trim(obj, depth=0):
    if isinstance(obj, dict):
        return {k: trim(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [trim(v, depth + 1) for v in obj[:2]] + (["..."] if len(obj) > 2 else [])
    if isinstance(obj, str) and len(obj) > 160:
        return obj[:160] + "...[truncated]"
    return obj


def main():
    token = os.environ.get("SG_TOKEN", "").strip() or None
    headers = dict(gs.STATIC_HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    results = {}
    for path, mode in PROBES:
        url = f"{gs.BASE_URL}/{path}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read()
                ct = resp.headers.get("Content-Type", "")
                entry = {"status": resp.status, "content_type": ct}
                if mode == "raw":
                    entry["bytes"] = len(body)
                    entry["note"] = "binary payload (Arrow IPC), not JSON"
                elif mode == "text":
                    entry["sample"] = body.decode("utf-8", "replace")[:200]
                else:
                    data = json.loads(body)
                    if mode == "json-spx":
                        if isinstance(data, list):
                            data = [r for r in data if isinstance(r, dict)
                                    and str(r.get("sym", "")).upper() == "SPX"][:1] or data[:1]
                        elif isinstance(data, dict) and "SPX" in data:
                            data = {"SPX": data["SPX"]}
                    if mode == "count" and isinstance(data, list):
                        entry["count"] = len(data)
                        entry["sample"] = trim(data[:3])
                    else:
                        entry["sample"] = trim(data)
                results[path] = entry
                print(f"OK   {resp.status} {path}")
        except urllib.error.HTTPError as e:
            detail = e.read()[:200].decode("utf-8", "replace")
            results[path] = {"status": e.code, "error": detail}
            print(f"HTTP {e.code} {path} :: {detail[:80]}")
        except Exception as e:
            results[path] = {"status": None, "error": str(e)}
            print(f"ERR  {path} :: {e}")

    with open("probes.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    print(f"\nsaved probes.json ({len(results)} endpoints)")


if __name__ == "__main__":
    main()
