"""mq-agent-15 work unit: options-matrix."""
import sys
import time

sys.path.insert(0, 'scraper')
from mq_api import get, path_of
from mq_db import finish_run, save_endpoint, save_response, start_run

TICKERS = ["SPX", "SPY", "QQQ", "NVDA", "TSLA", "AAPL"]
FREQS = ["intraday", "eod"]
SVC = "clickhouse-api"
TEMPLATE = "/api/web/v1/options/matrix/{ticker}"

run_id = start_run('mq-agent-15', 'options-matrix')
print("run_id", run_id)

calls = ok = 0
results = []
for t in TICKERS:
    for f in FREQS:
        path = f"/api/web/v1/options/matrix/{t}?frequency={f}"
        status, data = get(SVC, path)
        url = path_of(SVC, path)
        calls += 1
        if status == 200:
            ok += 1
        save_response(run_id, SVC, url, status, data)
        save_endpoint(SVC, TEMPLATE, example_url=url, params="frequency=intraday|eod",
                      status=status, discovered_via='agent-scrape')
        # dimension summary
        dims = ""
        if isinstance(data, dict):
            dims = "keys=" + ",".join(list(data.keys())[:8])
            for k in ("matrix", "data", "rows", "strikes", "expiries"):
                if k in data and isinstance(data[k], list):
                    dims += f" len({k})={len(data[k])}"
        elif isinstance(data, list):
            dims = f"list len={len(data)}"
        results.append((t, f, status, dims))
        print(t, f, status, dims)
        time.sleep(0.4)

status = 'ok' if ok == calls else ('partial' if ok else 'blocked')
finish_run(run_id, status, f"calls={calls} ok={ok}")
print("DONE", run_id, status, f"calls={calls} ok={ok}")
for r in results:
    print(r)
