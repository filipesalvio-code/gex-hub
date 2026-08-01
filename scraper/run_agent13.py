import sys, time, json
sys.path.insert(0, 'scraper')
from mq_db import start_run, save_response, save_endpoint, finish_run
from mq_api import get, path_of

TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "AVGO"]
QS = "fields=option&fields=momentum&fields=volatility&fields=seasonality&limit=30"

run_id = start_run('mq-agent-13', 'metrics-stocks')
results = {}
calls = 0
ok = 0
for t in TICKERS:
    path = f"/api/web/v1/metrics/{t}/eod?{QS}"
    status, data = get('clickhouse-api', path)
    calls += 1
    if status == 200:
        ok += 1
    save_response(run_id, 'clickhouse-api', path_of('clickhouse-api', path), status, data)
    save_endpoint('clickhouse-api', '/api/web/v1/metrics/{ticker}/{frequency}',
                  example_url=path_of('clickhouse-api', path), status=status,
                  discovered_via='agent-scrape')
    # summarize field groups
    groups = []
    if isinstance(data, dict):
        d = data.get('data', data)
        if isinstance(d, dict):
            for g in ['option', 'momentum', 'volatility', 'seasonality']:
                v = d.get(g)
                if v:
                    n = len(v) if hasattr(v, '__len__') else 1
                    groups.append(f"{g}:{n}")
        elif isinstance(d, list) and d:
            keys = set()
            for row in d[:5]:
                if isinstance(row, dict):
                    keys.update(row.keys())
            groups = sorted(keys)
    results[t] = (status, groups)
    time.sleep(0.4)

status_run = 'ok' if ok == calls else ('partial' if ok > 0 else 'blocked')
finish_run(run_id, status_run, f'calls={calls} ok={ok}')
print(json.dumps({'run_id': run_id, 'results': {t: {'status': s, 'groups': g} for t, (s, g) in results.items()}}, indent=1))
