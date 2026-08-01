#!/usr/bin/env python3
"""Scroll the Fixed Strike Matrix grid step by step, merging captured cells."""
import json
import sys

sys.path.insert(0, "scraper")
from wb_eval import evaluate

SESSION = "spotgamma-scrape-15"

with open("scraper/fsm_step.js") as f:
    template = f.read()

max_x, step_x = 10761 - 1174, int(1174 * 0.7)
max_y, step_y = 805 - 496, int(496 * 0.7)

x_steps = sorted(set(list(range(0, max_x, step_x)) + [max_x]))
y_steps = sorted(set(list(range(0, max_y, step_y)) + [max_y]))

cols = {}
rows = {}
for y in y_steps:
    for x in x_steps:
        code = template.replace("__X__", str(x)).replace("__Y__", str(y))
        res = evaluate(SESSION, code, 60)
        val = res.get("data", {}).get("value", "{}")
        try:
            data = json.loads(val)
        except Exception as e:
            print(f"PARSE FAIL x={x} y={y}: {e}; raw={val[:200]!r}", file=sys.stderr)
            continue
        for f, c in data.get("cols", {}).items():
            if f not in cols or not cols[f].get("header"):
                cols[f] = c
        for ri, r in data.get("rows", {}).items():
            rows.setdefault(ri, {"cells": {}})["cells"].update(r.get("cells", {}))
        print(f"x={x} y={y} cols={len(cols)} rows={len(rows)}", file=sys.stderr)

col_list = sorted(
    ({"field": f, "header": c["header"], "colIndex": c["colIndex"]} for f, c in cols.items()),
    key=lambda c: c["colIndex"],
)
row_list = [
    {"rowIndex": int(ri), "cells": r["cells"]}
    for ri, r in sorted(rows.items(), key=lambda kv: int(kv[0]))
]
out = {
    "title": "SPX Volatility Dashboard - SpotGamma",
    "url": "https://dashboard.spotgamma.com/ivol",
    "widget": "Fixed Strike Matrix",
    "columns": col_list,
    "rows": row_list,
    "nCols": len(col_list),
    "nRows": len(row_list),
}
with open("scraper/fsm_data.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps({"nCols": len(col_list), "nRows": len(row_list)}))
