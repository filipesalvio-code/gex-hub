# SpotGamma Scrape Database — Documentation

**Database:** `spotgamma.db` (SQLite)
**Location:** `/Users/filipesalvio/gex-hub/spotgamma.db`
**Collected:** 2026-07-25 (Saturday) by a 20-agent fleet via Kimi WebBridge, from an authenticated SpotGamma dashboard session.
**Data as-of:** last trading session, **2026-07-24** (the market was closed during collection — see *Caveats*).
**Size:** 86 snapshots, ~618 KB of JSON payload across 20 dashboard sections.

---

## 1. Schema

Two tables. All scraped content lives in `raw_snapshots.payload_json` as JSON text; every snapshot belongs to one run in `scrape_runs`.

### `scrape_runs` — one row per agent execution

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | run id |
| `started_at` / `finished_at` | TEXT (ISO-8601 UTC) | run window |
| `agent_name` | TEXT | `sg-agent-01` … `sg-agent-20` |
| `source_url` | TEXT | dashboard URL the agent scraped |
| `status` | TEXT | `ok` / `failed` / `running` |
| `notes` | TEXT | item counts and agent remarks |

### `raw_snapshots` — one row per captured data chunk

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | snapshot id (referenced throughout this doc) |
| `run_id` | INTEGER FK → `scrape_runs.id` | owning run |
| `captured_at` | TEXT (ISO-8601 UTC) | capture time |
| `source_url` | TEXT | page URL at capture |
| `section` | TEXT | tool/section label, e.g. `equityhub-spx`, `hiro-spx`, `volatility-dashboard/fixed-strike-matrix` |
| `payload_json` | TEXT (JSON) | the scraped data |

Common payload conventions (most snapshots): `url`, `title`, `date_updated`, and — for chart widgets whose numbers exist only as SVG/canvas pixels — `chart_only: true` with axis/legend text preserved.

### Quick start

```python
import sqlite3, json
con = sqlite3.connect("spotgamma.db")
payload = json.loads(con.execute(
    "SELECT payload_json FROM raw_snapshots WHERE section='equityhub-spx' LIMIT 1"
).fetchone()[0])
print(payload["metric_cards"]["Call Gamma"])   # -> 3.15B
```

```sql
-- SQLite JSON1 works directly on payload_json:
SELECT json_extract(payload_json, '$.metric_cards."Call Gamma"') AS call_gamma
FROM raw_snapshots
WHERE section = 'equityhub-spx';
-- -> 3.15B
```

> Note: metric values are stored **as displayed on the dashboard** — strings with units/commas (`"3.15B"`, `"$7,409.4"`, `"15.47%"`). Parse them before math (see §4 helper).

---

## 2. Tool-by-tool reference (SPX examples)

### 2.1 Market Overview — `/home`

**Snapshots:** #7 (Index Levels), #8 (Events Calendar), #9 (page state)
**Section:** `market-overview`

The landing page. Snapshot #7 holds the flagship **SG key-levels table for 6 indices** (SPX, SPY, NDX, QQQ, RUT, IWM): Call Wall, Put Wall, Zero Gamma, Volatility Trigger, Large Gamma 1–4, Combo 1–4 — with both SPX and /ES futures prices.

**SPX structure** (`payload.symbols.SPX`):

```json
{
  "headers": ["SPX", "/ES", "Level ID"],
  "rows": [
    ["8000", "8036", "Large Gamma 3"],
    ["7600", "7636", "Call Wall"],
    ["7510", "7546", "Volatility Trigger"],
    ["7420", "7456", "Zero Gamma"],
    ["7300", "7336", "Put Wall"],
    ["7000", "7036", "Large Gamma 1"]
  ]
}
```

*(12 rows total; excerpt above. Snapshot #8 adds 15 macro calendar events — FOMC, PCE, GDP, NFP — as `events[]` with datetime/importance/title.)*

```sql
SELECT json_extract(value, '$[0]') AS spx_level,
       json_extract(value, '$[2]') AS level_id
FROM raw_snapshots,
     json_each(json_extract(payload_json, '$.symbols.SPX.rows'))
WHERE raw_snapshots.id = 7 AND level_id = 'Call Wall';
-- -> 7600 | Call Wall
```

---

### 2.2 Equity Hub — `/equityhub?sym=SPX`

**Snapshots:** #3 (metrics + key daily levels), #4 (history)
**Section:** `equityhub-spx`, `equityhub-spx-history`

Per-symbol options positioning under the Synthetic OI model. Snapshot #3 has **20 metric cards** plus the SPX row of the 4,802-symbol Key Daily Levels grid; #4 has the 12-day history table.

**SPX metric cards** (`payload.metric_cards`, all 20 shown):

```json
{
  "Current Price": "$7,409.4",  "Previous Close": "$7,408.3",
  "Call Gamma": "3.15B",        "Put Gamma": "-4.25B",
  "High Vol Point": "$8,325",   "Low Vol Point": "$9,010",
  "Top Gamma Exp": "2026-08-20","Top Delta Exp": "2027-02-18",
  "Call Volume": "825.85K",     "Put Volume": "1.05M",
  "Put/Call OI Ratio": "1.29",  "1 M IV": "15.47%",
  "1 M RV": "10.39%",           "IV Rank": "33.09%",
  "Garch Rank": "29.44%",       "Skew Rank": "18.18%",
  "Options Implied Move": "$72.34",
  "Options Impact": "-",        "Earnings Date": "-"
}
```

**Key Daily Levels row** (`payload.sg_key_daily_levels_table.spx_row`):
`["SPX", "$7,409.40", "$7,408.30", "3,390,767,785", "$7620.90", "$0.00", "", "$9,010", "$8,325", "", "3.1B"]` — headers in `.headers` (Symbol, Current Price, Previous Close, Stock Volume, 52wk High/Low, Earnings, Low/High Vol Point, Options Impact, Call Gamma).

```sql
SELECT json_extract(payload_json, '$.metric_cards."Put/Call OI Ratio"') AS pc_oi,
       json_extract(payload_json, '$.metric_cards."Options Implied Move"') AS implied_move
FROM raw_snapshots WHERE section = 'equityhub-spx';
```

The same shape exists for 7 more symbols: `equityhub-spy`, `equityhub-qqq`, `equityhub-ndx`, `equityhub-iwm`, `equityhub-vix`, `equityhub-nvda`, `equityhub-tsla` (+ SPY bonus snapshot #6 `equityhub-spy-gamma-profile`: 322-strike full profile with per-strike OI/gamma/delta).

---

### 2.3 HIRO — `/hiro?sym=SPX`

**Snapshots:** #20 (metric panel + SG levels), #21 (Flow Data), #22 (Contracts Data), #23 (Trending/Watchlists/Alerts/Screener)
**Section:** `hiro-spx`

Real-time order-flow indicator. Snapshot #20 holds the metric panel and the **SpotGamma Levels** block; #21/#22 hold 23-row flow and contracts tables.

**SPX metric panel** (`payload.metric_panel`):

```json
{
  "symbol": "SPX", "name": "Standard & Poors 500 index",
  "current_price": "$7,409.40", "daily_move": "$0 (0.00%)",
  "current_hiro": "683M", "30_day_hiro_range": "-13B : 7.2B"
}
```

**SpotGamma Levels** (`payload.spotgamma_levels`):

```json
{"hedge_wall": "7510", "call_wall": "7600", "put_wall": "7300",
 "key_gamma_strike": "7000", "key_delta_strike": "6000"}
```

```sql
SELECT json_extract(payload_json, '$.spotgamma_levels.call_wall')  AS call_wall,
       json_extract(payload_json, '$.spotgamma_levels.put_wall')   AS put_wall,
       json_extract(payload_json, '$.metric_panel.current_hiro')   AS hiro
FROM raw_snapshots WHERE section = 'hiro-spx' AND id = 20;
-- -> 7600 | 7300 | 683M
```

Same shape for `hiro-spy` (#32–36) and `hiro-qqq` (#37–42), including 405-row stock screeners.

---

### 2.4 TRACE — `/trace`

**Snapshots:** #45 (page state + controls), #46 (chart metadata)
**Section:** `trace`

SPX gamma-exposure heatmap tool (fixed to SPX, no symbol selector). Chart-driven: series values are pixels only, so the payloads capture metric cards, full control state, and axis/legend calibration text.

**SPX example** (`payload.metric_cards`, #45):

```json
[{"label": "Stability", "value": "13%", "type": "gauge"},
 {"label": "0DTE GEX", "value": "0"}]
```

`payload.controls` records the full reproducible state: chart type `Gamma`, overlay `GEX`, counterparty `Market Makers`, timeframe `5m`, date `2026-07-24`, toggles (0DTE off, Key levels on), slider positions. Snapshot #46 records axis ranges: heatmap strikes 7380–7480, gamma −2B…1.5B; GEX-by-Strike −25.5B…24.5B — useful as calibration bounds if you later digitize the SVG.

---

### 2.5 Tape — `/tape`

**Snapshot:** #43
**Section:** `tape`

Real-time options trade feed (Friday's extended-hours prints). One rich snapshot: `live_flow` (30 rendered rows, 24 unique, 13 columns), `put_call_summary`, four "top" tables, and the filter-bar state.

**SPX flow row** (`payload.live_flow.rows[0]`):

```json
{"Time": "17:25:42, 07-24ETH", "Symbol": "SPX", "Side": "ABOVE ASK",
 "Buy/Sell": "BUY", "C/P": "CALL", "Strike": "7,445", "Volume": "3.7K",
 "OI": "2.8K", "Expiration": "2026-09-18", "Size": "13",
 "Premium": "$228K", "Spot": "$7,408.3", "Option Price": "$175"}
```

**Put/Call summary** (`payload.put_call_summary`): Volume 75K/52K/23K, Premium $82M/$58M/$24K→M, Delta $4.9B, Gamma $53M, Vega $61B (All/Call/Put).

```sql
SELECT json_extract(value, '$.Strike') AS strike,
       json_extract(value, '$.Premium') AS premium
FROM raw_snapshots, json_each(json_extract(payload_json, '$.live_flow.rows'))
WHERE section = 'tape'
  AND json_extract(value, '$.Symbol') = 'SPX'
  AND json_extract(value, '$.C/P') = 'CALL';
```

---

### 2.6 Volatility Dashboard — `/ivol`

**Snapshots:** #48 (Fixed Strike Matrix), #49 (Term Structure), #50 (Volatility Skew), #51 (VIX Term Structure), #52 (overview)
**Sections:** `volatility-dashboard/*`

The richest numerical capture — the agent digitized the SVG charts. All SPX-based:

- **#48 Fixed Strike Matrix:** full grid, **19 expiries (2026-07-27 → 2027-03-31) × 142 strikes (6675–8150)** of IV% cells. `headers[0]` = `"Expiry | Strike"`, each row = `[expiry, iv@6675, iv@6700, …]`. Example row start: `["2026-07-27", "39.59%", "38.38%", "37.19%", …]`.
- **#49 Term Structure:** 32 digitized points, SPX IV 9.71% (2026-07-26) → 15.17% (2026-10-15), + 14 macro-event markers.
- **#50 Volatility Skew:** 177 strike→IV points ($4,000–8,400) for 2026-08-24 expiry; ATM ≈ 15.05% @ 7400; reference line "Current Price: $7,408.3".
- **#52 Overview:** `spx_current_price: 7409.4`, **Implied Vol Z-Score 2.298** (as of 2026-07-24).

```sql
-- IV of the 7400 strike at the 2026-07-27 expiry (strike col index = (7400-6675)/25 + 2 = 31)
SELECT json_extract(value, '$[0]') AS expiry, json_extract(value, '$[31]') AS iv_7400
FROM raw_snapshots, json_each(json_extract(payload_json, '$.rows'))
WHERE raw_snapshots.id = 48 AND expiry = '2026-07-27';
-- -> 2026-07-27 | 17.73%
```

```python
# Skew curve into pandas
d = json.loads(con.execute("SELECT payload_json FROM raw_snapshots WHERE id=50").fetchone()[0])
skew = pd.DataFrame(d["skew_points"], columns=["strike", "iv_pct"])
```

> Digitized series carry `chart_only: true` and a `derivation` field describing the axis-calibration method — treat values as approximations (accuracy noted per payload).

---

### 2.7 Scanners — `/scanners`

**Snapshots:** #44 (All Symbols grid), #47 (Compass + inventory), #53–69 (individual scanners)
**Sections:** `scanner_*`, `scanners_*`

17 scanners inventoried (12 SG + 5 stock). Populated on capture (8): Highest Options Impact (50 rows), IV Percent Change (50), Earnings IV Crush (44), Volatility Risk Premium (30), Top Gamma % Expiring Friday (29), Cross Asset Summary (16), Sector ETFs (11), ETFs watchlist (14). Empty on the weekend (9, recorded honestly in `scanner_empty` snapshots): Squeeze, Reverse VRP, Call/Put Wall ±, Hedge Wall ±, 1% Margin of Hedge Wall, Top Delta % Expiring.

Each populated scanner payload: `scanner` name, `history` window (3 Days), `columns`, `rows` (Symbol/Price/X=IV-Percentile/Y=1M-IV), `scatter_dots` count. Snapshot #44 samples 96 rows of the 4,796-row All-Symbols grid.

```sql
SELECT DISTINCT json_extract(payload_json, '$.scanner') AS scanner_name,
       json_extract(payload_json, '$.row_count')        AS rows
FROM raw_snapshots WHERE section LIKE 'scanner_%' AND section != 'scanner_empty';
```

**SPX note:** index symbols rarely appear in equity scanners; check #69 Cross Asset Summary and #66 Sector ETFs for index-adjacent rows.

---

### 2.8 Founder's Notes — `/foundersNotes`

**Snapshots:** #73 (archive list), #70 / #77 / #80 (full note texts)
**Section:** `founders-notes`

#73 lists 15 July-2026 notes (AM + PM). #70/#77/#80 hold the **3 latest notes in full text** (7.2–9.5 K chars each) plus structured extractions: `sg_key_levels`, `key_support_resistance`, and `metrics_tables` (3 per note — gamma, vol trigger, walls, volumes/OI for SPX/SPY/NDX/QQQ).

```sql
SELECT json_extract(payload_json, '$.note_title'),
       json_extract(payload_json, '$.sg_key_levels')
FROM raw_snapshots
WHERE section = 'founders-notes' AND json_extract(payload_json, '$.kind') = 'full_text';
-- PM Note Fri Jul 24 … | SG Resistance/Pivot/Support incl. Pivot 7,480 (SPX)
```

---

### 2.9 Reports — `/reports`

**Snapshots:** #85 (inventory), #86 (latest report inline)
**Section:** `reports`

#85 inventories **196 FlowPatrol reports** (2025-09-26 → 2026-07-24) with names/dates and the S3 access pattern (signed GETs, `X-Amz-Expires=600`). #86 holds the latest — **FlowPatrol 2026-07-24**, full 40,842-char inline text with executive summary, 16-section TOC, and 3 position-change tables (Index / Single-Stock / Asset ETFs) covering SPX-family positioning.

```sql
SELECT json_extract(payload_json, '$.report_count') FROM raw_snapshots WHERE id = 85;  -- 196
SELECT substr(json_extract(payload_json, '$.inline_text'), 1, 500)
FROM raw_snapshots WHERE id = 86;  -- first 500 chars of the latest FlowPatrol
```

---

### 2.10 Indices — `/indices`

**Snapshots:** #71–84 (9 snapshots: SPX Greeks/Volatility/OI; NDX Greeks/OI; QQQ/RUT/IWM/SPY Greeks)
**Section:** `indices`

Per-index chart consoles. All series are SVG-path-only, so payloads preserve every chart's **legend + axis calibration** (usable as digitization bounds) — e.g. SPX Greeks view (#71): Gamma/Delta/Vanna Models (legend Jul 24/23/22), Absolute Gamma (strikes $5,990–8,105), Combo Strikes, Gamma Tilt (2015→2026), Expiration Concentration. Concentration/Strike tables were empty (weekend) and are recorded as such.

```sql
SELECT json_extract(payload_json, '$.symbol'), json_extract(payload_json, '$.view_tab')
FROM raw_snapshots WHERE section = 'indices';
-- SPX Greeks | SPX Volatility | SPX Open Interest | NDX Greeks | …
```

---

### 2.11 Options Calculator — `/optionsCalculator`

**Snapshots:** #75 (inputs/defaults), #76 (chart + computed outputs)
**Section:** `options-calculator/*`

Read-only capture of the default SPX position: **BTO 1× SPX 7440 Call, exp 2026-08-24, @ $121.8** (underlying $7,409.4, ATM IV 13.99%).

**Greeks & outputs:**

```json
// #75 payload.leg_greeks
{"iv": "14.59%", "delta": 0.501, "gamma": 0.001, "vega": 8.484, "theta": -9.075}
// #76 payload.computed
{"breakeven_at_expiration": 7561.8, "net_debit": "$12,180", "max_loss": "-$12,180", "max_profit": "unlimited"}
```

Chart annotations include Last Closing $7,408.3, Hedge Wall $7,510, Call Wall $7,600 — consistent with the HIRO/Overview levels. The PnL curve lives in a closed shadow root → `chart_only: true`.

---

## 3. Snapshot map (id → section)

| Tool | Snapshot ids |
|---|---|
| Market Overview | 7, 8, 9 |
| Equity Hub SPX/SPY/QQQ/NDX/IWM/VIX/NVDA/TSLA | 3–4 / 5–6 / 10–12 / 1–2 / 13–16 / 28–31 / 17–19 / 24–27 |
| HIRO SPX/SPY/QQQ | 20–23 / 32–36 / 37–42 |
| TRACE | 45, 46 |
| Tape | 43 |
| Volatility Dashboard | 48–52 |
| Scanners | 44, 47, 53–69 |
| Founder's Notes | 70, 73, 77, 80 |
| Reports | 85, 86 |
| Indices | 71, 72, 74, 78, 79, 81–84 |
| Options Calculator | 75, 76 |

## 4. Caveats & parsing helpers

1. **Weekend capture:** collected Saturday 2026-07-25; live widgets were frozen at Friday's close or blank (e.g. quote strips, HIRO SIGNAL column, several scanners). These states are recorded honestly in the payloads (`market_state`, `note`, or `scanner_empty`).
2. **`chart_only: true`** means the numbers exist only as SVG/canvas pixels on the dashboard; the payload preserves legends/axes/annotations. iVol series (#49–51) were additionally digitized with stated accuracy.
3. **Display strings:** numbers keep units (`3.15B`, `$7,409.4`, `15.47%`). Helper:

```python
def parse_sg(v):
    """'3.15B' -> 3.15e9 ; '$7,409.4' -> 7409.4 ; '15.47%' -> 15.47 ; '-' -> None"""
    if v in (None, "", "-"): return None
    s = str(v).replace("$", "").replace(",", "").replace("%", "").strip()
    mult = {"B": 1e9, "M": 1e6, "K": 1e3}.get(s[-1:], 1)
    if mult != 1: s = s[:-1]
    try: return float(s) * mult
    except ValueError: return None
```

4. **Virtualized grids:** some tables render only viewport rows (noted per payload, e.g. Equity Hub history "12 of 4,802", Tape "30 rendered / 24 unique").
5. **Runs 7 & 9** in `scrape_runs` are `failed` first attempts (transient API quota); their work completed as runs 13 & 14 — use `status='ok'` when joining.

## 5. Reusable query snippets

```sql
-- Latest snapshot per section
SELECT section, MAX(id) AS snapshot_id, MAX(captured_at) AS captured
FROM raw_snapshots GROUP BY section;

-- Everything captured for SPX across all tools
SELECT id, section, substr(payload_json, 1, 120)
FROM raw_snapshots
WHERE section LIKE '%spx%' OR payload_json LIKE '%"SPX"%';

-- Full audit trail: runs with their snapshot counts
SELECT r.id, r.agent_name, r.status, COUNT(s.id) AS snapshots
FROM scrape_runs r LEFT JOIN raw_snapshots s ON s.run_id = r.id
GROUP BY r.id ORDER BY r.id;
```
