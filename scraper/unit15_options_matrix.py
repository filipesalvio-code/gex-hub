"""mq-agent-15 · unit 'options-matrix' — /api/web/v1/options/matrix/{ticker}?frequency=."""
import sys, time, json

sys.path.insert(0, 'scraper')
from mq_db import start_run, finish_run, save_response, save_endpoint
from mq_api import get, path_of

SERVICE = 'clickhouse-api'
TEMPLATE = '/api/web/v1/options/matrix/{ticker}'
TICKERS = ['SPX', 'SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL']
FREQS = ['intraday', 'eod']


def describe(data):
    """Best-effort summary of matrix dimensions without dumping data."""
    try:
        if isinstance(data, dict):
            for key in ('data', 'matrix', 'rows', 'result'):
                if isinstance(data.get(key), list):
                    rows = data[key]
                    ncols = len(rows[0]) if rows and isinstance(rows[0], (list, dict)) else 0
                    return f"rows={len(rows)} cols~{ncols} keys={sorted(data.keys())[:8]}"
            return f"dict keys={sorted(data.keys())[:10]}"
        if isinstance(data, list):
            ncols = len(data[0]) if data and isinstance(data[0], (list, dict)) else 0
            return f"list rows={len(data)} cols~{ncols}"
        return f"type={type(data).__name__}"
    except Exception as e:  # noqa: BLE001
        return f"describe-error {e!r}"


def main():
    run_id = start_run('mq-agent-15', 'options-matrix')
    calls = ok = 0
    report = []
    for t in TICKERS:
        dims = []
        for f in FREQS:
            path = f'/api/web/v1/options/matrix/{t}?frequency={f}'
            status, data = get(SERVICE, path)
            calls += 1
            ok += 1 if status == 200 else 0
            save_response(run_id, SERVICE, path_of(SERVICE, path), status, data)
            save_endpoint(SERVICE, TEMPLATE,
                          example_url=path_of(SERVICE, path),
                          params='frequency=intraday|eod',
                          status=status, discovered_via='agent-scrape')
            dims.append(f"{f}:{status} {describe(data)}")
            report.append(f"{t} {f} -> {status}")
            time.sleep(0.4)
        print(f"DIM {t} | " + ' ; '.join(dims))
    status = 'ok' if ok == calls else ('blocked' if ok == 0 else 'partial')
    finish_run(run_id, status, f'calls={calls} ok={ok}')
    print(f"run_id={run_id} status={status} calls={calls} ok={ok}")
    for r in report:
        print(' ', r)


if __name__ == '__main__':
    main()
