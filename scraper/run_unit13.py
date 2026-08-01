"""Unit 13 - metrics-stocks: EOD metrics (option/momentum/volatility/seasonality) for 8 tickers."""
import sys, time, json
sys.path.insert(0, 'scraper')
from mq_api import get, path_of
from mq_db import start_run, save_response, save_endpoint, finish_run

TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "AVGO"]
SERVICE = "clickhouse-api"
TEMPLATE = "/api/web/v1/metrics/{ticker}/eod?fields=option&fields=momentum&fields=volatility&fields=seasonality&limit=30"

run_id = start_run('mq-agent-13', 'metrics-stocks')
results = {}
calls = ok = 0
for t in TICKERS:
    path = f"/api/web/v1/metrics/{t}/eod?fields=option&fields=momentum&fields=volatility&fields=seasonality&limit=30"
    try:
        status, data = get(SERVICE, path)
    except Exception as e:
        status, data = -1, {"error": repr(e)}
    calls += 1
    if 200 <= status < 300:
        ok += 1
    save_response(run_id, SERVICE, path_of(SERVICE, path), status, data)
    save_endpoint(SERVICE, TEMPLATE,
                  example_url=path_of(SERVICE, path), status=status,
                  discovered_via='agent-scrape')
    # summarize field groups
    groups = {}
    if isinstance(data, dict):
        for g in ("option", "momentum", "volatility", "seasonality"):
            v = data.get(g)
            if v is None and isinstance(data.get("data"), dict):
                v = data["data"].get(g)
            if isinstance(v, list):
                groups[g] = len(v)
            elif v is not None:
                groups[g] = "present"
            else:
                groups[g] = None
    elif isinstance(data, list):
        groups["_rows"] = len(data)
    results[t] = {"status": status, "groups": groups,
                  "top_keys": list(data.keys())[:10] if isinstance(data, dict) else None}
    time.sleep(0.4)

finish_run(run_id, 'ok' if ok == calls else ('blocked' if ok == 0 else 'partial'),
           f'calls={calls} ok={ok}')
print(f"run_id={run_id} calls={calls} ok={ok}")
for t, r in results.items():
    print(t, r["status"], "groups:", {k: v for k, v in r["groups"].items()}, "top_keys:", r["top_keys"])
