"""mq-agent-07 work unit: gamma-levels-index-intraday."""
import sys, time, json
sys.path.insert(0, 'scraper')
from mq_db import start_run, save_response, save_endpoint, finish_run
from mq_api import get, path_of

TICKERS = ["SPX", "SPY", "QQQ", "NDX", "IWM", "RUT", "DIA", "VIX"]
SERVICE = "clickhouse-api"
TEMPLATE = "/api/web/v1/gamma-levels/{ticker}/intraday"

run_id = start_run('mq-agent-07', 'gamma-levels-index-intraday')
results = []
ok = 0
for t in TICKERS:
    path = f"/api/web/v1/gamma-levels/{t}/intraday"
    status, data = get(SERVICE, path)
    save_response(run_id, SERVICE, path_of(SERVICE, path), status, data)
    save_endpoint(SERVICE, TEMPLATE, example_url=path_of(SERVICE, path),
                  status=status, discovered_via='agent-scrape')
    # summarize shape
    info = ""
    if isinstance(data, dict):
        info = "keys=" + ",".join(list(data.keys())[:10])
        if "data" in data and isinstance(data["data"], list):
            info += f" rows={len(data['data'])}"
            if data["data"]:
                info += " fields=" + ",".join(list(data["data"][0].keys())[:15])
    elif isinstance(data, list):
        info = f"list rows={len(data)}"
        if data and isinstance(data[0], dict):
            info += " fields=" + ",".join(list(data[0].keys())[:15])
    results.append((t, status, info[:300]))
    if 200 <= status < 300:
        ok += 1
    time.sleep(0.4)

status = 'ok' if ok == len(TICKERS) else ('partial' if ok > 0 else 'blocked')
finish_run(run_id, status, f"calls={len(TICKERS)} ok={ok}")
print(f"run_id={run_id} status={status}")
for t, s, i in results:
    print(f"  {t}: {s} {i}")
