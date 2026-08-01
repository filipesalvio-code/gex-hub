"""mq-agent-02 unit: market-status across exchanges."""
import sys, time
sys.path.insert(0, 'scraper')
from mq_db import start_run, finish_run, save_response, save_endpoint
from mq_api import get, path_of

SERVICE = 'clickhouse-api'
EXCHANGES = ['NYSE', 'NASDAQ', 'CME', 'CBOT', 'NYMEX', 'COMEX', 'CBOE',
             'ICE', 'BINANCE', 'COINBASE', 'OANDA']

run_id = start_run('mq-agent-02', 'market-status')
calls = ok = 0
results = {}
for exch in EXCHANGES:
    path = f'/api/web/v1/market-status/{exch}'
    status, data = get(SERVICE, path)
    calls += 1
    if 200 <= status < 300:
        ok += 1
    results[exch] = status
    save_response(run_id, SERVICE, path_of(SERVICE, path), status, data)
    time.sleep(0.4)

# register endpoint template once, using the first exchange as example
save_endpoint(SERVICE, '/api/web/v1/market-status/{exchange}',
              example_url=path_of(SERVICE, '/api/web/v1/market-status/NYSE'),
              status=results.get('NYSE'), discovered_via='agent-scrape')

valid = [e for e, s in results.items() if 200 <= s < 300]
invalid = {e: s for e, s in results.items() if not (200 <= s < 300)}
finish_run(run_id, 'ok' if ok == calls else 'partial',
           f'calls={calls} ok={ok} valid={len(valid)}')
print('run_id', run_id)
print('results', results)
print('valid', valid)
