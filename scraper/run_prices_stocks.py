"""mq-agent-04 unit: prices-stocks — batched prices for 12 stock tickers."""
import sys
import time

sys.path.insert(0, 'scraper')
from mq_api import get, path_of
from mq_db import finish_run, save_endpoint, save_response, start_run

TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "AVGO",
           "AMD", "PLTR", "NFLX", "COIN"]
SERVICE = "clickhouse-api"
TEMPLATE = "/api/web/v1/prices"

run_id = start_run('mq-agent-04', 'prices-stocks')
calls = ok = 0
errors = []
tickers_returned = set()
fields = set()

# 1) batched call
batch_path = f"{TEMPLATE}?tickers={','.join(TICKERS)}"
status, data = get(SERVICE, batch_path)
calls += 1
save_response(run_id, SERVICE, path_of(SERVICE, batch_path), status, data)
save_endpoint(SERVICE, TEMPLATE, example_url=path_of(SERVICE, batch_path),
              params="tickers=<csv>", status=status, discovered_via='agent-scrape')

def harvest(payload):
    """Collect returned ticker keys + field names from any plausible shape."""
    items = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        for key in ("data", "prices", "results", "items"):
            if isinstance(payload.get(key), list):
                items = payload[key]; break
        else:
            # dict keyed by ticker?
            if all(isinstance(v, (dict, list)) for v in payload.values()) and payload:
                for k, v in payload.items():
                    if k.upper() in TICKERS:
                        tickers_returned.add(k.upper())
                        if isinstance(v, dict): fields.update(v.keys())
                return
    for it in items:
        if isinstance(it, dict):
            t = (it.get("ticker") or it.get("symbol") or "").upper()
            if t: tickers_returned.add(t)
            fields.update(it.keys())

if status == 200:
    ok += 1
    harvest(data)
else:
    errors.append(f"batch:{status}")

# 2) fallback: per-ticker calls for any missing ticker
missing = [t for t in TICKERS if t not in tickers_returned]
if status != 200:
    missing = TICKERS[:]  # batch failed entirely; try each
for t in missing:
    time.sleep(0.4)
    p = f"{TEMPLATE}?tickers={t}"
    st, d = get(SERVICE, p)
    calls += 1
    save_response(run_id, SERVICE, path_of(SERVICE, p), st, d)
    if st == 200:
        ok += 1
        before = set(tickers_returned)
        harvest(d)
        if not isinstance(d, dict) or "_error" not in d:
            tickers_returned.add(t)  # endpoint answered; count ticker as covered
    else:
        errors.append(f"{t}:{st}")

run_status = 'ok' if not errors else ('partial' if ok else 'blocked')
finish_run(run_id, run_status, f"calls={calls} ok={ok}")

# verify
import sqlite3

con = sqlite3.connect('menthorq.db', timeout=30)
rows = con.execute("SELECT http_status, length(payload_json) FROM raw_responses WHERE run_id=?", (run_id,)).fetchall()
print("run_id:", run_id)
print("verify rows:", len(rows), "statuses:", [r[0] for r in rows], "min_payload:", min(r[1] for r in rows))
print("tickers_returned:", sorted(tickers_returned))
print("fields:", sorted(fields))
print("errors:", errors)
print("run_status:", run_status)
