"""mq-agent-05 — work unit 5, key 'screener-catalog'."""
import sys, time, json

sys.path.insert(0, 'scraper')
from mq_db import start_run, save_response, save_endpoint, finish_run
from mq_api import get, path_of

CALLS = [
    ("clickhouse-api", "/api/web/v1/screeners/columns",
     "/api/web/v1/screeners/columns"),
    ("clickhouse-api",
     "/api/web/v1/screeners?columns=name,quote_type,sector,industry,market_cap,volume&tickers=SPX,SPY,QQQ,NVDA,TSLA,AAPL,MSFT,AMZN,META,GOOGL",
     "/api/web/v1/screeners?columns={columns}&tickers={tickers}"),
    ("chat-service", "/api/web/v1/screeners", "/api/web/v1/screeners"),
]

def main():
    run_id = start_run('mq-agent-05', 'screener-catalog')
    results = []
    for service, path, template in CALLS:
        status, data = get(service, path)
        save_response(run_id, service, path_of(service, path), status, data)
        params = ""
        if "?" in path:
            params = path.split("?", 1)[1]
        save_endpoint(service, template,
                      example_url=path_of(service, path), params=params,
                      status=status, discovered_via='agent-scrape')
        results.append((service, path, status, data))
        time.sleep(0.4)

    ok = sum(1 for r in results if 200 <= r[2] < 300)
    status = 'ok' if ok == len(results) else ('blocked' if ok == 0 else 'partial')
    finish_run(run_id, status, f'calls={len(results)} ok={ok}')

    summary = {"run_id": run_id, "run_status": status, "calls": []}
    for service, path, st, data in results:
        entry = {"service": service, "path": path[:80], "status": st}
        if isinstance(data, dict):
            entry["keys"] = list(data.keys())[:10]
            for k, v in data.items():
                if isinstance(v, list):
                    entry[f"len_{k}"] = len(v)
        elif isinstance(data, list):
            entry["list_len"] = len(data)
            if data and isinstance(data[0], dict):
                entry["first_keys"] = list(data[0].keys())[:15]
        entry["snippet"] = json.dumps(data, ensure_ascii=False)[:400]
        summary["calls"].append(entry)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
