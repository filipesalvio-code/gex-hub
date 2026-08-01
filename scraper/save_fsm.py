#!/usr/bin/env python3
"""Save the Fixed Strike Matrix snapshot to spotgamma.db."""
import json
import sys

sys.path.insert(0, "scraper")
from db_writer import save_snapshot

RUN_ID = 16

d = json.load(open("scraper/fsm_data.json"))
headers = [c["header"] for c in d["columns"]]
rows = []
for r in d["rows"]:
    row = []
    for c in d["columns"]:
        v = r["cells"].get(c["field"], "")
        row.append(v if v != "" else None)
    rows.append(row)

payload = {
    "title": d["title"],
    "url": d["url"],
    "widget": "Fixed Strike Matrix",
    "tab": "Fixed Strike Matrix",
    "description": "Implied volatility (%) by expiry date (rows) x strike (columns). null = blank in UI.",
    "headers": headers,
    "rows": rows,
    "nCols": d["nCols"],
    "nRows": d["nRows"],
}
sid = save_snapshot(RUN_ID, d["url"], "volatility-dashboard/fixed-strike-matrix", payload)
print("snapshot_id=", sid)
