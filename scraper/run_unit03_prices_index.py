"""mq-agent-03 work unit: prices-index — batched prices call with per-ticker fallback."""
import sys
import time

sys.path.insert(0, 'scraper')
from mq_api import get, path_of
from mq_db import finish_run, save_endpoint, save_response, start_run

TICKERS = ["SPX", "SPY", "QQQ", "NDX", "IWM", "RUT", "DIA", "VIX"]
SERVICE = "clickhouse-api"

run_id = start_run('mq-agent-03', 'prices-index')
calls = 0
ok = 0
statuses = []

batch_path = "/api/web/v1/prices?tickers=" + ",".join(TICKERS)
status, data = get(SERVICE, batch_path)
calls += 1
save_response(run_id, SERVICE, path_of(SERVICE, batch_path), status, data)
save_endpoint(SERVICE, "/api/web/v1/prices", example_url=path_of(SERVICE, batch_path),
              params="tickers={csv}", status=status, discovered_via='agent-scrape')
statuses.append(f"batch={status}")
if 200 <= status < 300:
    ok += 1
else:
    # fallback: per-ticker calls
    for t in TICKERS:
        time.sleep(0.4)
        p = f"/api/web/v1/prices?tickers={t}"
        s, d = get(SERVICE, p)
        calls += 1
        save_response(run_id, SERVICE, path_of(SERVICE, p), s, d)
        statuses.append(f"{t}={s}")
        if 200 <= s < 300:
            ok += 1

final = 'ok' if ok == calls else ('partial' if ok > 0 else 'blocked')
finish_run(run_id, final, f"calls={calls} ok={ok} statuses={','.join(statuses)}")

# verify
import json
import sqlite3

con = sqlite3.connect('menthorq.db')
rows = con.execute("SELECT http_status, length(payload_json), payload_json FROM raw_responses WHERE run_id=?", (run_id,)).fetchall()
print("run_id:", run_id)
print("rows:", len(rows), "expected:", calls)
for st, ln, payload in rows:
    print("status:", st, "payload_len:", ln)
# summarize batch payload structure
if rows and statuses[0].startswith("batch=2"):
    d = json.loads(rows[0][2])
    print("type:", type(d).__name__)
    if isinstance(d, dict):
        print("keys:", list(d.keys())[:20])
        for k, v in list(d.items())[:2]:
            print(f"sample[{k}]:", json.dumps(v)[:300])
    elif isinstance(d, list):
        print("len:", len(d), "sample:", json.dumps(d[0])[:300] if d else "empty")
con.close()
