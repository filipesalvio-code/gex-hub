import re
from pathlib import Path

WS = Path('/Users/filipesalvio/gex-hub')
PAGES = WS / 'presentation' / 'pages'

# Confirmed changes from scrape vs current deck:
# IV Rank changed from 33% to 28.26% (Equity Hub v2)
# All other levels/data unchanged since Fri Jul 24 close

iv_rank_old = "33%"
iv_rank_new = "28.26%"

def update_page(filename, replacements):
    path = PAGES / filename
    text = path.read_text()
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new)
            print(f"  Updated {filename}: '{old[:50]}...' -> '{new[:50]}...'")
        else:
            print(f"  Skipped {filename}: pattern not found: '{old[:50]}...'")
    path.write_text(text)

print("=== Updating presentation pages ===")

# Page 4 - Positioning: IV Rank update
update_page('04_positioning.page', [
    (f'IV Rank sits at <strong>{iv_rank_old}</strong>', f'IV Rank sits at <strong>{iv_rank_new}</strong>'),
])

print("\nDone.")
