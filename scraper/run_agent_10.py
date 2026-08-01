"""mq-agent-10 work unit: gamma-insights-index."""
import sys
import time

sys.path.insert(0, 'scraper')
from mq_api import get, path_of
from mq_db import finish_run, save_endpoint, save_response, start_run

SERVICE = 'clickhouse-api'
TICKERS = ['SPX', 'SPY', 'QQQ', 'NDX', 'IWM', 'VIX']

run_id = start_run('mq-agent-10', 'gamma-insights-index')
print(f'run_id={run_id}', flush=True)

calls = 0
ok = 0
summary = []

def do(path):
    global calls, ok
    status, data = get(SERVICE, path)
    calls += 1
    if 200 <= status < 300:
        ok += 1
    save_response(run_id, SERVICE, path_of(SERVICE, path), status, data)
    time.sleep(0.4)
    return status, data

for t in TICKERS:
    p1 = f'/api/web/v1/gamma-insights/{t}?limit=20'
    s1, d1 = do(p1)
    n1 = len(d1) if isinstance(d1, list) else (len(d1.get('data') or d1.get('insights') or []) if isinstance(d1, dict) else '?')
    save_endpoint(SERVICE, '/api/web/v1/gamma-insights/{ticker}',
                  example_url=path_of(SERVICE, p1), params='limit=20',
                  status=s1, discovered_via='agent-scrape')

    p2 = f'/api/web/v1/gamma-insights/{t}/expirations?frequency=eod'
    s2, d2 = do(p2)
    n2 = len(d2) if isinstance(d2, list) else (len(d2.get('data') or d2.get('expirations') or []) if isinstance(d2, dict) else '?')
    save_endpoint(SERVICE, '/api/web/v1/gamma-insights/{ticker}/expirations',
                  example_url=path_of(SERVICE, p2), params='frequency=eod',
                  status=s2, discovered_via='agent-scrape')

    summary.append((t, s1, n1, s2, n2))
    print(f'{t}: insights={s1}(n={n1}) expirations={s2}(n={n2})', flush=True)

status = 'ok' if ok == calls else ('blocked' if ok == 0 else 'partial')
finish_run(run_id, status, f'calls={calls} ok={ok}')
print(f'FINISH {status} calls={calls} ok={ok}', flush=True)

# verification
from mq_db import _connect

with _connect() as con:
    rows = con.execute(
        "SELECT http_status, LENGTH(payload_json) FROM raw_responses WHERE run_id=? ORDER BY id",
        (run_id,)).fetchall()
print('verify rows:', len(rows))
for r in rows:
    print(' ', r)
