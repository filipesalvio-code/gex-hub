#!/usr/bin/env python3
"""Digitize VIX Term Structure chart; save snapshot."""
import json
import sys
from datetime import date, timedelta

sys.path.insert(0, "scraper")
from db_writer import save_snapshot

RUN_ID = 16
URL = "https://dashboard.spotgamma.com/ivol?ivol_tab=vix&vs_asof=2026-07-24"

raw = json.load(open("scraper/vix_raw.json"))
curves = json.load(open("scraper/vix_pts.json"))

# X: 2026-07-31 @112.172, 2027-03-02 @1068.065
x_ticks, y_ticks, events = [], [], []
for t in raw["texts"]:
    v, x, y, cls = t["v"], float(t["x"]), float(t["y"]), t["cls"]
    if "axis-tick-value" in cls and v.startswith("20"):
        x_ticks.append((date.fromisoformat(v), x))
    elif "axis-tick-value" in cls:
        y_ticks.append((float(v), y))
    elif "recharts-label" in cls and v not in ("Expiration Date", "Implied Volatility") and not v.startswith("20"):
        events.append((v, x))

x_ticks.sort(key=lambda p: p[1])
d0, x0 = x_ticks[0]
d1, x1 = x_ticks[-1]
slope = (d1 - d0).days / (x1 - x0)
def px_to_date(x):
    return (d0 + timedelta(days=round(slope * (x - x0)))).isoformat()

y_ticks.sort(key=lambda p: p[1])
(p_lo, y_lo), (p_hi, y_hi) = y_ticks[0], y_ticks[-1]
m = (p_lo - p_hi) / (y_lo - y_hi)
c = p_hi - m * y_hi
def py_to_pct(y):
    return round(c + m * y, 3)

series_names = {"#00BBAA": "2026-07-24", "#7f7f7f": "2026-07-23"}

# canonical points from dots
dot_series = {}
for dot in curves["dots"]:
    nm = series_names.get(dot["stroke"], dot["stroke"])
    dot_series.setdefault(nm, []).append(
        {"date": px_to_date(dot["cx"]), "iv": py_to_pct(dot["cy"])})
for v in dot_series.values():
    v.sort(key=lambda p: p["date"])

# sampled curves thinned (every 5th point)
curve_series = {}
for stroke, pts in curves["series"].items():
    nm = series_names.get(stroke, stroke)
    curve_series[nm] = [
        {"date": px_to_date(x), "iv": py_to_pct(y)} for x, y in pts[::5]
    ]

payload = {
    "title": "SPX Volatility Dashboard - SpotGamma",
    "url": URL,
    "widget": "VIX Term Structure",
    "tab": "VIX Term Structure",
    "chart_type": "recharts SVG line chart, 2 series + economic event markers",
    "chart_only": True,
    "derivation": "Points from SVG dot positions + curve sampling via getPointAtLength, linear axis calibration; ~0.02 accuracy.",
    "x_axis": {"label": "Expiration Date", "range": ["2026-07-23", "2027-03-19"]},
    "y_axis": {"label": "Implied Volatility", "ticks": [p for p, _ in y_ticks]},
    "series_points": dot_series,
    "series_curves_thinned": curve_series,
    "macro_event_markers": [
        {"event": v, "date": px_to_date(x)} for v, x in sorted(events, key=lambda e: e[1])
    ],
    "legend": raw["legend"],
}
sid = save_snapshot(RUN_ID, URL, "volatility-dashboard/vix-term-structure", payload)
print("snapshot_id=", sid)
for nm, pts in dot_series.items():
    print(nm, len(pts), pts)
