import json
import sys
import time

sys.path.insert(0, 'scraper')
from mq_api import get, path_of
from mq_db import finish_run, save_endpoint, save_response, start_run

TICKERS = ['SPX', 'SPY', 'QQQ', 'NDX', 'IWM', 'RUT', 'DIA', 'VIX']
SERVICE = 'clickhouse-api'
TEMPLATE = '/api/web/v1/gamma-levels/{ticker}/{frequency}'

run_id = start_run('mq-agent-06', 'gamma-levels-index-eod')
print('run_id:', run_id)

calls = 0
ok = 0
results = []
for t in TICKERS:
    path = f'/api/web/v1/gamma-levels/{t}/eod'
    try:
        status, data = get(SERVICE, path)
    except Exception as e:
        status, data = -1, {'error': str(e)}
    calls += 1
    if 200 <= status < 300:
        ok += 1
    save_response(run_id, SERVICE, path_of(SERVICE, path), status, data)
    save_endpoint(SERVICE, TEMPLATE,
                  example_url=path_of(SERVICE, path), status=status,
                  discovered_via='agent-scrape')
    # field summary
    fields = None
    if isinstance(data, dict):
        fields = list(data.keys())[:10]
    results.append((t, status, fields,
                    (len(json.dumps(data)) if data is not None else 0)))
    time.sleep(0.4)

state = 'ok' if ok == calls else ('blocked' if ok == 0 else 'partial')
finish_run(run_id, state, f'calls={calls} ok={ok}')
for t, s, f, sz in results:
    print(f'{t}: status={s} bytes={sz} fields={f}')
print('RUN_STATE:', state)
