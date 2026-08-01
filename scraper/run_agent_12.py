"""mq-agent-12 work unit: metrics-index.

GET /api/web/v1/metrics/{t}/eod for 8 tickers with field groups
option, momentum, volatility, seasonality. Save every response, register
endpoint template, finish run, verify.
"""
import sys
import time

sys.path.insert(0, 'scraper')
from mq_api import get, path_of
from mq_db import finish_run, save_endpoint, save_response, start_run

TICKERS = ["SPX", "SPY", "QQQ", "NDX", "IWM", "RUT", "DIA", "VIX"]
SERVICE = "clickhouse-api"
TEMPLATE = "/api/web/v1/metrics/{ticker}/{frequency}"
QS = "fields=option&fields=momentum&fields=volatility&fields=seasonality&limit=30"

run_id = start_run('mq-agent-12', 'metrics-index')
print(f"run_id={run_id}")

results = {}
calls = 0
ok = 0
for t in TICKERS:
    path = f"/api/web/v1/metrics/{t}/eod?{QS}"
    status, data = get(SERVICE, path)
    calls += 1
    if 200 <= status < 300:
        ok += 1
    save_response(run_id, SERVICE, path_of(SERVICE, path), status, data)
    save_endpoint(SERVICE, TEMPLATE, example_url=path_of(SERVICE, path),
                  status=status, discovered_via='agent-scrape')
    # summarize which field groups contain data
    groups = {}
    if isinstance(data, dict):
        payload = data.get('data', data)
        if isinstance(payload, dict):
            for g in ('option', 'momentum', 'volatility', 'seasonality'):
                v = payload.get(g)
                if v is None:
                    groups[g] = 'absent'
                elif isinstance(v, (list, dict)):
                    groups[g] = f"{type(v).__name__}[{len(v)}]"
                else:
                    groups[g] = type(v).__name__
        else:
            groups = {'payload_type': type(payload).__name__}
    results[t] = (status, groups)
    print(f"{t}: status={status} groups={groups}")
    time.sleep(0.4)

run_status = 'ok' if ok == calls else ('blocked' if ok == 0 else 'partial')
finish_run(run_id, run_status, f"calls={calls} ok={ok}")
print(f"finished: status={run_status} calls={calls} ok={ok}")
