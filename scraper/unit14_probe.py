"""mq-agent-14 work unit: metrics-intraday-probe.

Probe GET clickhouse-api /api/web/v1/metrics/{t}/intraday for SPX, SPY, QQQ,
NVDA with fields=option&fields=volatility&limit=30. Persist every response,
including 4xx bodies. If intraday works, also try fields=momentum&
fields=seasonality for SPX.
"""
import sys
import time

sys.path.insert(0, 'scraper')
from mq_api import get, path_of
from mq_db import finish_run, save_endpoint, save_response, start_run

SERVICE = 'clickhouse-api'
TICKERS = ['SPX', 'SPY', 'QQQ', 'NVDA']
TEMPLATE = '/api/web/v1/metrics/{ticker}/intraday'


def call(run_id, path, params_desc):
    status, data = get(SERVICE, path)
    url = path_of(SERVICE, path)
    save_response(run_id, SERVICE, url, status, data)
    save_endpoint(SERVICE, TEMPLATE, example_url=url, params=params_desc,
                  status=status, discovered_via='agent-scrape')
    return status, data


def main():
    run_id = start_run('mq-agent-14', 'metrics-intraday-probe')
    print(f'run_id={run_id}', flush=True)

    calls = 0
    ok = 0
    results = {}
    for t in TICKERS:
        path = f'/api/web/v1/metrics/{t}/intraday?fields=option&fields=volatility&limit=30'
        status, data = call(run_id, path, 'fields=option&fields=volatility&limit=30')
        calls += 1
        results[t] = (status, data)
        ok += 1 if 200 <= status < 300 else 0
        size = len(str(data))
        preview = str(data)[:200].replace('\n', ' ')
        print(f'{t}: status={status} size={size} preview={preview}', flush=True)
        time.sleep(0.4)

    # If intraday works for SPX, also probe momentum & seasonality fields.
    spx_status, spx_data = results.get('SPX', (0, None))
    spx_works = 200 <= spx_status < 300 and bool(spx_data)
    if spx_works:
        path = '/api/web/v1/metrics/SPX/intraday?fields=momentum&fields=seasonality&limit=30'
        status, data = call(run_id, path, 'fields=momentum&fields=seasonality&limit=30')
        calls += 1
        ok += 1 if 200 <= status < 300 else 0
        preview = str(data)[:200].replace('\n', ' ')
        print(f'SPX momentum/seasonality: status={status} preview={preview}', flush=True)
    else:
        print('intraday not working for SPX; skipping momentum/seasonality probe', flush=True)

    run_status = 'ok' if ok == calls else 'partial'
    finish_run(run_id, run_status, f'calls={calls} ok={ok}')
    print(f'finished: calls={calls} ok={ok}', flush=True)


if __name__ == '__main__':
    main()
