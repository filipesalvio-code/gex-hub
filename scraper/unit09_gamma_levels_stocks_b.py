"""Unit 9: gamma-levels-stocks-b — GOOGL, AVGO, AMD, PLTR, NFLX, COIN eod+intraday."""
import json
import sys
import time

sys.path.insert(0, 'scraper')
from mq_api import get, path_of
from mq_db import finish_run, save_endpoint, save_response, start_run

TICKERS = ["GOOGL", "AVGO", "AMD", "PLTR", "NFLX", "COIN"]
FREQS = ["eod", "intraday"]
SVC = "clickhouse-api"

run_id = start_run('mq-agent-09', 'gamma-levels-stocks-b')
print(f"run_id={run_id}", flush=True)

calls = ok = 0
results = []
for t in TICKERS:
    for f in FREQS:
        path = f"/api/web/v1/gamma-levels/{t}/{f}"
        status, data = get(SVC, path)
        calls += 1
        if 200 <= status < 300:
            ok += 1
        save_response(run_id, SVC, path_of(SVC, path), status, data)
        save_endpoint(SVC, '/api/web/v1/gamma-levels/{ticker}/{frequency}',
                      example_url=path_of(SVC, path), status=status,
                      discovered_via='agent-scrape')
        size = len(json.dumps(data)) if data is not None else 0
        results.append((t, f, status, size))
        print(f"{t} {f}: status={status} bytes={size}", flush=True)
        time.sleep(0.4)

finish_run(run_id, 'ok' if ok == calls else 'partial', f"calls={calls} ok={ok}")
print(f"DONE calls={calls} ok={ok}", flush=True)
for r in results:
    print(r, flush=True)
