#!/usr/bin/env python3
"""Calibrate Term Structure chart pixels to data values; save snapshot."""
import json
import sys
from datetime import date, timedelta

sys.path.insert(0, "scraper")
from db_writer import save_snapshot

RUN_ID = 16
URL = "https://dashboard.spotgamma.com/ivol?ivol_tab=term_structure"

d = json.load(open("scraper/ts_chart_raw.json"))

# X calibration: tick dates
x_ticks = []
y_ticks = []
events = []
for t in d["texts"]:
    v, x, y, cls = t["v"], float(t["x"]), float(t["y"]), t["cls"]
    if "axis-tick-value" in cls and v.startswith("2026"):
        x_ticks.append((date.fromisoformat(v), x))
    elif "axis-tick-value" in cls and v.endswith("%"):
        y_ticks.append((float(v.rstrip("%")), y))
    elif "recharts-label" in cls and not v.endswith("Date") and v != "Implied Volatility" and not v.startswith("2026"):
        events.append((v, x, y))

# linear fit x = a + b*days
x_ticks.sort(key=lambda p: p[1])
d0, x0 = x_ticks[0]
d1, x1 = x_ticks[-1]
b = ((d1 - d0).days) / (x1 - x0)
def px_to_date(x):
    return d0 + timedelta(days=round(b * (x - x0)))

# y fit: pct = c + m*y
y_ticks.sort(key=lambda p: p[1])
(p_lo, y_lo), (p_hi, y_hi) = y_ticks[0], y_ticks[-1]
m = (p_lo - p_hi) / (y_lo - y_hi)
c = p_hi - m * y_hi
def py_to_pct(y):
    return round(c + m * y, 2)

points = []
for cdot in d["circles"]:
    if "line-dot" not in cdot["cls"]:
        continue
    x, y = float(cdot["cx"]), float(cdot["cy"])
    points.append({"date": px_to_date(x).isoformat(), "iv_pct": py_to_pct(y)})
points.sort(key=lambda p: p["date"])

ev = [{"event": v, "date": px_to_date(x).isoformat()} for v, x, y in sorted(events, key=lambda e: e[1])]

payload = {
    "title": "SPX Volatility Dashboard - SpotGamma",
    "url": URL,
    "widget": "Term Structure",
    "tab": "Term Structure",
    "chart_type": "recharts SVG line chart",
    "chart_only": True,
    "derivation": "Values reverse-engineered from SVG dot pixel positions via linear axis calibration; ~0.05pp accuracy.",
    "x_axis": {"label": "Expiration Date", "range": ["2026-07-26", "2026-10-15"]},
    "y_axis": {"label": "Implied Volatility", "ticks_pct": [p for p, _ in sorted(y_ticks)]},
    "series": {"name": "SPX Implied Volatility term structure", "points": points},
    "macro_event_markers": ev,
    "axis_tick_dates": [dt.isoformat() for dt, _ in x_ticks],
}
sid = save_snapshot(RUN_ID, URL, "volatility-dashboard/term-structure", payload)
print("snapshot_id=", sid, "points=", len(points), "events=", len(ev))
print("first/last:", points[0], points[-1])
