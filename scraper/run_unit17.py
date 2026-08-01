"""mq-agent-17 work unit: volatility-insights x8 tickers + probes."""
import sys
import time

sys.path.insert(0, 'scraper')
from mq_db import start_run, save_response, save_endpoint, finish_run
from mq_api import get, path_of

SVC = 'clickhouse-api'
run_id = start_run('mq-agent-17', 'volatility-insights')
print(f'run_id={run_id}', flush=True)

calls = 0
ok = 0
results = []

def do(path, template, params=''):
    global calls, ok
    status, data = get(SVC, path)
    calls += 1
    if status and 200 <= status < 300:
        ok += 1
    save_response(run_id, SVC, path_of(SVC, path), status, data)
    save_endpoint(SVC, template, example_url=path_of(SVC, path), params=params,
                  status=status, discovered_via='agent-scrape')
    results.append((path, status, data))
    print(f'{status} {path}', flush=True)
    time.sleep(0.4)
    return status, data

# 1. volatility-insights for 8 tickers
for t in ['SPX', 'SPY', 'QQQ', 'NDX', 'IWM', 'VIX', 'NVDA', 'TSLA']:
    do(f'/api/web/v1/volatility-insights/{t}', '/api/web/v1/volatility-insights/{ticker}')

# 2a. probe: price-ratios
do('/api/web/v1/price-ratios?tickers=SPX,SPY', '/api/web/v1/price-ratios',
   params='tickers')

# 2b. probe: levels-report
do('/api/web/v1/levels-report?ticker=SPX', '/api/web/v1/levels-report',
   params='ticker')

# 2c. probe: put-call-ratio with frequency param
do('/api/web/v1/options/put-call-ratio/SPX?frequency=eod',
   '/api/web/v1/options/put-call-ratio/{ticker}', params='frequency')
do('/api/web/v1/options/put-call-ratio/SPX?frequency=intraday',
   '/api/web/v1/options/put-call-ratio/{ticker}', params='frequency')

finish = 'ok' if ok == calls else ('blocked' if ok == 0 else 'partial')
finish_run(run_id, finish, f'calls={calls} ok={ok}')

# summarize payload shapes
print('\n--- summary ---')
for path, status, data in results:
    if isinstance(data, dict):
        keys = list(data.keys())[:12]
        n = len(data)
    elif isinstance(data, list):
        keys = f'list[{len(data)}]'
        n = len(data)
    else:
        keys = type(data).__name__
        n = 0
    print(f'{status} {path} :: {keys}')
