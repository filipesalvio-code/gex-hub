"""mq-agent-18 work unit: candles (5m + 1d) for SPX, SPY, QQQ, NVDA, TSLA
plus SPX tradingview. Saves all responses and registers endpoint templates."""
import sys
import time

sys.path.insert(0, 'scraper')
from mq_api import get, path_of          # noqa: E402
from mq_db import start_run, save_response, save_endpoint, finish_run  # noqa: E402

TICKERS = ["SPX", "SPY", "QQQ", "NVDA", "TSLA"]

NOW_MS = int(time.time() * 1000)
FROM_MS = NOW_MS - 48 * 3600 * 1000  # last 48h


def needs_window(status, data):
    """Heuristic: response indicates a missing/invalid time window."""
    if status != 200:
        return True
    if isinstance(data, dict):
        err = str(data.get("_error", "")) + str(data.get("error", "")) + str(data.get("message", ""))
        if "from" in err.lower() or "to" in err.lower() or "window" in err.lower() or "range" in err.lower():
            return True
        # empty payload with no candles
        if not data or all(not v for v in data.values() if isinstance(v, (list, dict))):
            keys = set(data.keys())
            if not (keys & {"candles", "bars", "data", "t", "timestamps"}):
                return True
    if isinstance(data, list) and len(data) == 0:
        return True
    return False


def count_bars(data):
    """Best-effort bar count from a candles payload."""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for k in ("candles", "bars", "data", "t", "timestamps", "time"):
            v = data.get(k)
            if isinstance(v, list):
                return len(v)
        lists = [len(v) for v in data.values() if isinstance(v, list)]
        if lists:
            return max(lists)
    return 0


def main():
    run_id = start_run('mq-agent-18', 'candles')
    calls = 0
    ok = 0
    lines = []

    for t in TICKERS:
        for interval, cb in (("5m", 288), ("1d", 60)):
            path = f"/api/web/v1/tickers/{t}/candles?interval={interval}&countBack={cb}"
            status, data = get('clickhouse-api', path)
            calls += 1
            save_response(run_id, 'clickhouse-api',
                          path_of('clickhouse-api', path), status, data)
            if needs_window(status, data) and interval == "5m":
                time.sleep(0.4)
                path2 = path + f"&from={FROM_MS}&to={NOW_MS}"
                status, data = get('clickhouse-api', path2)
                calls += 1
                save_response(run_id, 'clickhouse-api',
                              path_of('clickhouse-api', path2), status, data)
                path = path2
            save_endpoint(
                'clickhouse-api',
                '/api/web/v1/tickers/{ticker}/candles',
                example_url=path_of('clickhouse-api', path),
                params='interval,countBack,from,to',
                status=status, discovered_via='agent-scrape')
            good = status == 200 and not (isinstance(data, dict) and "_error" in data)
            ok += 1 if good else 0
            lines.append(f"{t} {interval}: status={status} bars={count_bars(data)}")
            time.sleep(0.4)

    # SPX tradingview
    path = "/api/web/v1/tickers/SPX/tradingview"
    status, data = get('clickhouse-api', path)
    calls += 1
    save_response(run_id, 'clickhouse-api', path_of('clickhouse-api', path),
                  status, data)
    save_endpoint('clickhouse-api', '/api/web/v1/tickers/{ticker}/tradingview',
                  example_url=path_of('clickhouse-api', path),
                  status=status, discovered_via='agent-scrape')
    ok += 1 if status == 200 else 0
    lines.append(f"SPX tradingview: status={status}")

    final = 'ok' if ok == calls else ('partial' if ok else 'blocked')
    finish_run(run_id, final, f"calls={calls} ok={ok}")
    print(f"run_id={run_id} status={final} calls={calls} ok={ok}")
    for ln in lines:
        print(ln)


if __name__ == '__main__':
    main()
