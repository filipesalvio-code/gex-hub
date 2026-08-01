#!/usr/bin/env python3
"""Digitize Volatility Skew curve; save snapshot."""
import json
import sys

sys.path.insert(0, "scraper")
from db_writer import save_snapshot

RUN_ID = 16
URL = ("https://dashboard.spotgamma.com/ivol?ivol_tab=vol_skew"
       "&vs_lines=[{\"key\":\"2026-07-24-1787601600000\",\"tradeDate\":\"2026-07-24\",\"expiryDate\":\"1787601600000\",\"color\":\"#00BBAA\"}]"
       "&vs_asof=2026-07-24")

pts = json.load(open("scraper/skew_pts.json"))["pts"]

# X: $4000 @ px65, $8200 @ px1080.6363637
def px_to_strike(x):
    return 4000 + (x - 65) * (8200 - 4000) / (1080.6363637 - 65)

# Y: 7.42% @ py470, 76.47% @ py45
m = (7.42 - 76.47) / (470 - 45)
c = 76.47 - m * 45
def py_to_pct(y):
    return round(c + m * y, 2)

curve = [{"strike": round(px_to_strike(x)), "iv_pct": py_to_pct(y)} for x, y in pts]
# thin: nearest-25-strike buckets, keep mean
buckets = {}
for p in curve:
    k = round(p["strike"] / 25) * 25
    buckets.setdefault(k, []).append(p["iv_pct"])
thin = [{"strike": k, "iv_pct": round(sum(v) / len(v), 2)} for k, v in sorted(buckets.items())]

payload = {
    "title": "SPX Volatility Dashboard - SpotGamma",
    "url": URL,
    "widget": "Volatility Skew",
    "tab": "Volatility Skew",
    "chart_type": "recharts SVG line chart (smooth curve, no point markers)",
    "chart_only": True,
    "derivation": "Curve digitized via SVG getPointAtLength sampling + linear axis calibration; values rounded to nearest $25 strike, ~0.1pp accuracy.",
    "x_axis": {"label": "Strike", "range_usd": [4000, 8400]},
    "y_axis": {"label": "Implied Volatility", "ticks_pct": [7.42, 27.42, 47.42, 76.47]},
    "series_meta": {"trade_date": "2026-07-24", "expiry": "2026-08-24", "dte": 31,
                    "legend": "2026-07-24 | 08-24 , 31 DTE", "underlying": "SPX"},
    "reference_line": {"label": "Current Price: $7,408.3", "strike_usd": 7408.3},
    "skew_points": thin,
    "min_iv_pct": min(p["iv_pct"] for p in thin),
    "max_iv_pct": max(p["iv_pct"] for p in thin),
}
sid = save_snapshot(RUN_ID, URL, "volatility-dashboard/volatility-skew", payload)
print("snapshot_id=", sid, "points=", len(thin))
print("ATM-ish:", [p for p in thin if abs(p["strike"] - 7400) <= 25])
print("min:", min(thin, key=lambda p: p["iv_pct"]))
