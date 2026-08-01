import sys, time
sys.path.insert(0, 'scraper')
from mq_db import start_run, save_response, save_endpoint, finish_run
from mq_api import get, path_of

TICKERS = ["SPX", "SPY", "QQQ", "NVDA", "TSLA", "AAPL"]
ENDPOINTS = [
    ("/api/web/v1/options/put-call-ratio/{t}", "/api/web/v1/options/put-call-ratio/{ticker}"),
    ("/api/web/v1/dealer-positioning/{t}", "/api/web/v1/dealer-positioning/{ticker}"),
]

run_id = start_run('mq-agent-16', 'options-putcall-dealer')
print("run_id:", run_id)
calls = ok = 0
results = {}
for tmpl, reg in ENDPOINTS:
    stats = []
    for t in TICKERS:
        path = tmpl.format(t=t)
        status, data = get('clickhouse-api', path)
        calls += 1
        if status and 200 <= status < 300:
            ok += 1
        save_response(run_id, 'clickhouse-api', path_of('clickhouse-api', path), status, data)
        stats.append((t, status))
        print(tmpl, t, status)
        time.sleep(0.4)
    results[reg] = stats
    # register with the most common non-zero status observed
    nonzero = [s for _, s in stats if s]
    reg_status = max(set(nonzero), key=nonzero.count) if nonzero else 0
    save_endpoint('clickhouse-api', reg,
                  example_url=path_of('clickhouse-api', tmpl.format(t='SPX')),
                  status=reg_status, discovered_via='agent-scrape')

final = 'ok' if ok == calls else ('partial' if ok > 0 else 'blocked')
if all(s in (401, 403, 0) for st in results.values() for _, s in st):
    final = 'blocked'
finish_run(run_id, final, f'calls={calls} ok={ok}')
print('FINAL', final, f'calls={calls} ok={ok}')

# verify
import sqlite3, json
con = sqlite3.connect('menthorq.db')
n = con.execute("SELECT COUNT(*) FROM raw_responses WHERE run_id=?", (run_id,)).fetchone()[0]
print('raw_responses rows for run:', n)
for row in con.execute("SELECT url, http_status, LENGTH(payload_json) FROM raw_responses WHERE run_id=? ORDER BY id", (run_id,)):
    print(row)
