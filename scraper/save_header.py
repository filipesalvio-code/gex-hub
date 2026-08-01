#!/usr/bin/env python3
"""Save page header/overview snapshot."""
import sys

sys.path.insert(0, "scraper")
from db_writer import save_snapshot

RUN_ID = 16

payload = {
    "title": "SPX Volatility Dashboard - SpotGamma",
    "url": "https://dashboard.spotgamma.com/ivol",
    "widget": "page-header",
    "section": "Volatility Dashboard (iVol)",
    "spx_current_price": 7409.40,
    "implied_vol_zscore": {"value": 2.298, "as_of": "2026-07-24",
                           "note": "card shows '2026-07-24 - 2.298' / 'Implied Vol Z-Score 2.298'"},
    "ticker_strip": {
        "^SPX": None, "^NDX": None, "^VIX": None, "WTI": None, "Gold": None,
        "note": "strip labels render but all values empty (market closed, weekend)",
    },
    "page_meta": {
        "version": "82036d0f8b (5613)",
        "page_timestamp": "Wed Jul 22 20:14:05 UTC 2026",
        "data_as_of": "2026-07-24",
    },
    "tabs": ["Fixed Strike Matrix", "Term Structure", "Volatility Skew", "VIX Term Structure"],
    "notes": "Market closed (weekend); latest data as of 2026-07-24. No watchlist tables, no percentile/rank cards on this page.",
}
sid = save_snapshot(RUN_ID, "https://dashboard.spotgamma.com/ivol",
                    "volatility-dashboard/overview", payload)
print("snapshot_id=", sid)
