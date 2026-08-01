import sys, time
sys.path.insert(0, 'scraper')
from mq_db import start_run, finish_run, save_response, save_endpoint
from mq_api import get, path_of

TICKERS = ["SPX", "SPY", "QQQ", "NDX", "IWM", "RUT", "DIA", "VIX"]
QS = "?fields=option&fields=momentum&fields=volatility&fields=seasonality&limit=30"
TEMPLATE = "/api/web/v1/metrics/{ticker}/{frequency}"

run_id = start_run('mq-agent-12', 'metrics-index')
print("run_id:", run_id)

ok = 0
results = {}
for t in TICKERS:
    path = f"/api/web/v1/metrics/{t}/eod{QS}"
    status, data = get('clickhouse-api', path)
    save_response(run_id, 'clickhouse-api', path_of('clickhouse-api', path), status, data)
    save_endpoint('clickhouse-api', TEMPLATE,
                  example_url=path_of('clickhouse-api', path), status=status,
                  discovered_via='agent-scrape')
    # summarize field groups present
    groups = []
    if isinstance(data, dict):
        d = data.get('data', data)
        if isinstance(d, dict):
            for g in ('option', 'momentum', 'volatility', 'seasonality'):
                v = d.get(g)
                if v:
                    groups.append(f"{g}({len(v) if hasattr(v,'__len__') else 'y'})")
        elif isinstance(d, list) and d:
            keys = set()
            for row in d[:5]:
                if isinstance(row, dict):
                    keys.update(row.keys())
            groups = sorted(keys)
    results[t] = (status, ','.join(groups) if groups else '-')
    print(t, status, results[t][1])
    if status == 200:
        ok += 1
    time.sleep(0.4)

notes = f"calls={len(TICKERS)} ok={ok}"
finish_run(run_id, 'ok' if ok == len(TICKERS) else ('partial' if ok else 'blocked'), notes)
print("finish:", notes)
