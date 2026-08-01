import json
import sys
import time

sys.path.insert(0, 'scraper')
from mq_api import get, path_of
from mq_db import finish_run, save_endpoint, save_response, start_run

run_id = start_run('mq-agent-11', 'gamma-insights-stocks')
tickers = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'META']
calls = 0; ok = 0
try:
    for t in tickers:
        for path, template, params in [
            (f'/api/web/v1/gamma-insights/{t}?limit=20',
             '/api/web/v1/gamma-insights/{ticker}', {'limit': '20'}),
            (f'/api/web/v1/gamma-insights/{t}/expirations?frequency=eod',
             '/api/web/v1/gamma-insights/{ticker}/expirations', {'frequency': 'eod'}),
        ]:
            status, data = get('clickhouse-api', path)
            calls += 1
            if status == 200:
                ok += 1
            save_response(run_id, 'clickhouse-api', path_of('clickhouse-api', path), status, data)
            save_endpoint('clickhouse-api', template,
                          example_url=path_of('clickhouse-api', path), status=status,
                          discovered_via='agent-scrape', params=json.dumps(params))
            n = len(data) if isinstance(data, (list, dict)) else '?'
            print(f'{t} {path.split("?")[0]} -> {status} len={n}')
            time.sleep(0.4)
    finish_run(run_id, 'ok' if ok == calls else 'partial', f'calls={calls} ok={ok}')
    print(f'RUN {run_id} done calls={calls} ok={ok}')
except Exception as e:
    finish_run(run_id, 'blocked', f'calls={calls} ok={ok} err={e}')
    print(f'RUN {run_id} FAILED: {e}')
    raise
