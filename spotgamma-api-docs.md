# SpotGamma API — Full Reference Documentation

Reverse-engineered from the SpotGamma dashboard (`dashboard.spotgamma.com`) on 2026-07-25.
Every endpoint below was **called live with a real subscriber session**; all response samples are actual API returns for **SPX** (trade date 2026-07-23/24), trimmed for readability. Full untrimmed samples are in `probes.json` in this workspace.

---

## Contents

1. [Architecture & hosts](#1-architecture--hosts)
2. [Authentication](#2-authentication)
3. [Conventions & gotchas](#3-conventions--gotchas)
4. [Core GEX & key levels](#4-core-gex--key-levels)
5. [Greeks, skew & IV](#5-greeks-skew--iv)
6. [Open interest & synthetic OI](#6-open-interest--synthetic-oi)
7. [HIRO order flow](#7-hiro-order-flow)
8. [Market data & quotes](#8-market-data--quotes)
9. [Scanners, compass & trending](#9-scanners-compass--trending)
10. [Calendars & alerts](#10-calendars--alerts)
11. [Streaming platform (api.stream + WebSocket)](#11-streaming-platform)
12. [Content & account](#12-content--account)
13. [Error reference](#13-error-reference)
14. [Local tooling](#14-local-tooling)

---

## 1. Architecture & hosts

The dashboard is a React SPA. All data comes from two REST hosts plus one WebSocket host:

| Host | Role | Discovered via |
|---|---|---|
| `https://api.spotgamma.com` | Main API — GEX, greeks, HIRO, quotes, calendars, account | network capture |
| `https://api.stream.spotgamma.com` | Streaming/intraday platform — intraday OI, candles, VIX, manifest, TNS flow | bundle (`Oo.BASE`) |
| `wss://bbg.stream.spotgamma.com` | Real-time WebSocket push (`/stream?token=<sgToken>`) | bundle |

The main API serves JSON. Several heavy endpoints instead return **binary columnar payloads** (see §3.4).

## 2. Authentication

### 2.1 Required headers (every request)

```http
x-json-web-token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE2NjgxMjgyNDJ9.0VtbQW99MELrgb4JW56xtbRdh1LAbDBlB1T78dJlILA
Content-Type: application/json
Version: 5613
App-Type: web
Authorization: Bearer <sgToken>
```

- **`x-json-web-token`** — static, hardcoded application token found in the dashboard JS bundle. Identical for all users.
- **`Authorization: Bearer <sgToken>`** — your session token. Obtained at login; stored by the dashboard in `localStorage["sgToken"]` (also set as the `sgToken` cookie on `.spotgamma.com`).
- `Version: 5613` / `App-Type: web` — app version markers sent by the dashboard.

### 2.2 Token lifecycle

The `sgToken` is a JWT. Decode its payload to see scope and expiry:

```json
// GET https://api.stream.spotgamma.com/validate_bearer  (live response)
{
  "user_id": "0542f012-...",
  "userType": 1,
  "is_institutional": false,
  "iss": "SpotGamma",
  "exp": 1785208341,
  "roles": ["subscriber"],
  "memberships": ["Alpha"],
  "wpID": 30787
}
```

- Lifetime is ~3 days from issue. When it expires, re-login (or re-read `localStorage["sgToken"]` from an open, logged-in dashboard tab — `gex_scraper.py` automates this via WebBridge).
- **Verified:** public/free endpoints (e.g. `v1/futures/mostRecentMarketOpen`) work with static headers only; subscription endpoints return `403 {"error":{"message":"Invalid authorization: <empty>"}}` without the Bearer token.

### 2.3 Access tiers — `free_` endpoints

Almost every paid endpoint has an unpaid-tier twin used by the dashboard when the account lacks access:

| Paid | Free fallback |
|---|---|
| `v4/equities` | `v1/free_equities` |
| `v4/historical` | `v1/free_historical` |
| `v6/running_hiro` | `v1/free_running_hiro` |
| `v11/hiro` | `v1/free_hiro`, `v1/free_latest_hiro` |
| `v2/latest_greeks` | `v2/free_latest_greeks` |
| `v2/daily_greeks` | `v2/free_daily_greeks` |
| `v2/skew` | `v2/free_skew` |
| `v1/rr` | `v1/free_rr` |
| `v1/iv_stats` | `v1/free_iv_stats` |
| `v1/earnings` | `v1/free_earnings` |
| `v1/equityScanners` | `v1/free_equityScanners` |
| `synth_oi/v1/equities` | `synth_oi/v1/free_equities` |
| `synth_oi/v1/historical` | `synth_oi/v1/free_historical` |

## 3. Conventions & gotchas

### 3.1 Dates
- `trade_date`/`quote_date` are UTC ISO strings at midnight (`2026-07-23T00:00:00.000Z`).
- Query dates use `YYYY-MM-DD`. GEX data is **EOD** — for date `D`, data appears on the evening of `D` (US ET) at the earliest; the dashboard itself requests the *previous* day.
- Epoch fields (`utc_time`, `exp`, `day`) are **milliseconds**.

### 3.2 Symbol encoding
- Query params must be URL-encoded: `S&P ES=F` → `S%26P%20ES%3DF`.
- `v1/prices` takes **dash-separated** lists: `?syms=SPX-QQQ-AAPL`. Most others take comma-separated or single symbols — noted per endpoint.

### 3.3 JSON strings inside JSON
Many records embed arrays as **stringified JSON** that must be parsed a second time: `strike_list`, `current_list`, `levels_with_pct`, `cg_list`, `hist_px`, …

### 3.4 Binary payloads (not JSON!)

**All of these decode cleanly with `gex_binary.py` in this workspace** (see §14).

| Endpoint | Format | Decoder |
|---|---|---|
| `v1/oi?sym=` | **MessagePack** (~16 MB for SPX) — `expiry_ms → strike → [put, call] → 22 per-actor OI fields` | `gex_binary.py oi SPX` |
| `v1/oi/{intradayStrikeOI,intradayStrikeGEX}?sym=` | MessagePack (same family) | `fetch_msgpack()` |
| `v2/latest_greeks`, `v2/daily_greeks` | **MessagePack** — `expiry_ms → strike → [call_row, put_row]` (~8 values/row) | `gex_binary.py greeks SPX` |
| `v1/iv_stats` | **MessagePack** — `tenor(30/60/90) → day-key → delta → 9 floats` | `gex_binary.py ivstats SPX` |
| `…/intraday_strike_bars` | **Parquet** (`PAR1` magic, ~2.6 MB) — columns: `strike_price, timestamp, {bd,cust,firm,mm,procust}_gamma, *_gamma_0` | `gex_binary.py bars SPX gamma` (duckdb) |

MessagePack identification: first byte `0xDE`/`0x83` (msgpack map headers). The dashboard decodes these in JS/WASM and converts to Arrow in-browser — the wire format itself is msgpack, not Arrow.

**`v1/oi` semantics (verified):** fields follow the OCC participant taxonomy — `bd` (broker-dealer), `mm` (market maker), `cust` (customer), `procust` (professional customer), `firm`. `*_buy_oi`/`*_sell_oi` are gross positions; per-side buys ≈ sells as expected. The `cust_lt_100`/`cust_100_199`/`cust_gt_199` buckets are **signed net** figures by trade-size class (can be negative — not components of `cust_buy_oi`). Totals run ~25–115% above SpotGamma's modeled `callsum`/`putsum` (v4), so treat the two as different universes: OCC-style full-chain positions vs the modeled dashboard subset.

### 3.5 Compression
Some endpoints (`v2/*greeks`, `v1/iv_stats`) gzip even without `Accept-Encoding`. If you get garbled bytes, send `Accept-Encoding: gzip, deflate` and decompress.

### 3.6 Sign conventions
- `gamma_not` (key_levels): net $ gamma, negative = net short-gamma regime.
- `call_gnot_list_absg` / `put_gnot_list_absg` (equities): per-strike gamma notional, all ≤ 0 (dealer-short-negative convention) — compare **magnitudes**, not sign.

---

## 4. Core GEX & key levels

These endpoints are the heart of the product — gamma walls, flip levels, and per-symbol positioning.

### 4.1 `GET /home/keyLevels?includeGammaCurve={0|1}`

The headline dataset: key gamma levels for the six index underlyings (SPX, SPY, NDX, QQQ, RUT, IWM). Fired by the dashboard on every home load. **Auth:** paid.

| Param | Values | Meaning |
|---|---|---|
| `includeGammaCurve` | `0` / `1` | `1` includes the `strike_list` + `current_list` gamma curve arrays |

```bash
curl "https://api.spotgamma.com/home/keyLevels?includeGammaCurve=1" -H "$HEADERS"
```

**Sample (SPX record, 2026-07-23):**

```json
{
  "sym": "SPX", "trade_date": "2026-07-23T00:00:00.000Z", "upx": 7408,
  "callwallstrike": 7600, "putwallstrike": 7300,
  "callwallgam": 13714176, "putwallgam": -39917882,
  "zero_g_strike": 7420, "max_g_strike": 7510, "topabs_strike": 7000,
  "gamma_not": -388559157, "rr": -0.0658,
  "atm_g_calls": 938085689, "atm_g_puts": -1149912826,
  "atm_Theta": 792592244038, "atm_Vega": -3217383024924,
  "L1": 7000, "L2": 7500, "L3": 8000, "L4": 7600,
  "C1": 7297, "C2": 7379, "C3": 7327, "C4": 7349,
  "calls_OI": 9311912, "puts_OI": 12685300,
  "calls_vol": 825848, "puts_vol": 1050252,
  "sig": 0.0063, "sig5": 0.0178,
  "futuresSym": "/ESU26", "futuresDiff": 35.875,
  "levels_with_pct": "[[7749.0, 87.32], ...]",
  "strike_list": "[8889.96, 8823.29, ...]",
  "current_list": "[886841071.0, 964420738.0, ...]",
  "next_exp_list": "[886481370.0, ...]",
  "keyLevelTradeDate": "...", "gammaTradeDate": "..."
}
```

**Field guide (SPX):**

| Field | Meaning |
|---|---|
| `upx` | Underlying price used for the snapshot |
| `callwallstrike` / `putwallstrike` | Call wall / put wall strikes |
| `zero_g_strike` | Zero-gamma flip level |
| `max_g_strike` | Strike of maximum total gamma |
| `topabs_strike` | Largest absolute gamma strike on the map (7000) |
| `gamma_not` | Net gamma notional ($); negative = short-gamma regime |
| `L1`–`L4` | SpotGamma's four "levels" (support/resistance ladder) |
| `C1`–`C4` | Four closer "combo" levels |
| `sig` / `sig5` | Implied 1-day / 5-day expected move (fraction) |
| `rr` | Risk reversal |
| `strike_list` + `current_list` | **JSON strings**: parallel arrays = total gamma per strike bucket (54 log-spaced points) |
| `next_exp_list` | Same curve, next-expiry model only |
| `levels_with_pct` | **JSON string**: `[strike, percentile]` pairs |

### 4.2 `GET /home/allData`

Aggregate home payload; its `keyLevels` array is the same records as §4.1 plus additional home-screen sections. **Auth:** paid. Prefer §4.1 unless you need everything at once.

### 4.3 `GET /v3/equitiesBySyms?syms={LIST}&date={YYYY-MM-DD}`

Full GEX profile for one or more symbols on a given date. This is what the dashboard loads for the selected symbol (it requests the *previous* day). **Auth:** paid.

```bash
curl "https://api.spotgamma.com/v3/equitiesBySyms?syms=SPX&date=2026-07-23" -H "$HEADERS"
```

**Sample (2026-07-23) — response is keyed by symbol:**

```json
{"SPX": {
  "sym": "SPX", "name": "S&P 500", "upx": 7408.3,
  "callsum": 9311912, "putsum": 12685300,
  "cws": 7600, "pws": 7300, "keyg": 7000, "maxfs": 7510, "minfs": 400, "keyd": 6000,
  "largeCoi": 7000, "largePoi": 7000,
  "put_call_ratio": 1.3623, "volume_ratio": 1.2717,
  "gamma_ratio": 0.8158, "delta_ratio": -1.4779, "totaldelta": -901892503478,
  "skew": -0.4256, "cskew": -0.1708, "pskew": 0.2549, "ne_skew": -0.1754,
  "atm_iv30": 0.1546, "rv30": 0.1014, "fwd_garch": 0.1315,
  "iv_pct": 0.752, "iv_rank": 0.3282, "skew_rank": 0.2,
  "options_implied_move": 72.29,
  "next_exp_call_gamma": 144350128, "next_exp_put_gamma": 372431633,
  "max_exp_g_date": "2026-09-18T20:00:00.000Z",
  "...": "~95 fields total, incl. per-strike JSON-string lists"
}}
```

**Key field guide:** `cws`/`pws` = call/put wall strike · `keyg` = key gamma (biggest) strike · `maxfs`/`minfs` = max/min gamma "flip strikes" · `keyd` = key delta strike · `largeCoi`/`largePoi` = strikes of largest call/put OI · `callsum`/`putsum` = total call/put OI · `atmgc`/`atmgp` = ATM gamma calls/puts · `gamma_ratio` = call gamma ÷ put gamma · `options_implied_move` = ±1-day implied move in points · `iv_rank`, `skew_rank` = 0–1 percentiles · `hist_*` + `strike_list`, `cg_list`, `pg_list`, `mf_list` = JSON-string arrays (per-strike and history).

### 4.4 `GET /v4/equities`

The entire equities GEX table — **4,987 symbols** at last count, same ~95-field schema as §4.3, latest trade date only. **Auth:** paid. Big response (~40 MB); filter client-side.

```python
data = fetch_json("v4/equities", token)
spx = next(r for r in data if r["sym"] == "SPX")
```

Note the payload is **one day fresher than keyLevels** in our captures: on 2026-07-25 it already carried `trade_date 2026-07-24` (`upx 7411.98`, `maxfs 7465`, `prev_maxfs 7510`).

### 4.5 `GET /v4/historical?sym={SYM}`

Daily history of the v4 record for one symbol (same schema subset incl. per-strike lists). **Auth:** paid. `sym=SPX` returns an array ordered by `trade_date`. Free tier: `v1/free_historical`.

### 4.6 `GET /v2/comboLevels?sym={SYM}(&model=next_exp)`

SpotGamma's "combo" gamma profile: parallel JSON-string arrays — `current_list`/`next_exp_list` = strike grid, `strike_list` = gamma values. `model=combo_profile` (default) or `combo_profile_ne` (`model=next_exp`). **Auth:** paid.

```json
[{"trade_date": "2026-07-23T00:00:00.000Z", "model": "combo_profile", "sym": "SPX",
  "strike_list": "[-723936.19, -5601028.86, ...]",
  "current_list": "[7045.0, 7053.0, 7060.0, ...]",
  "next_exp_list": "[7045.0, 7053.0, ...]"}]
```

### 4.7 `GET /absGammaLevels?sym={SYM}`

Absolute-gamma distribution for calls and puts separately. Returns **two records** (`model: "absCalls"`, `model: "absPuts"`); each `current_list`/`next_exp_list` is a JSON string of `[strike, gamma]` pairs. **Auth:** paid.

### 4.8 `GET /v1/zeroDTE?sym={SYM}`

Daily 0DTE share history back to 2018: `zero_dte_volume`, `all_volume`, `zero_dte_oi`, `all_oi`, `percent_total`. Pass `sym=Equity` for the equity-universe aggregate (dashboard behavior).

```json
[{"trade_date": "2018-01-03T00:00:00.000Z", "zero_dte_volume": 101175,
  "all_volume": 1422583, "zero_dte_oi": 160606, "all_oi": 12814282,
  "percent_total": 0.0711, "sym": "SPX"}, ...]
```

---

## 5. Greeks, skew & IV

### 5.1 `GET /v2/latest_greeks?sym={SYM}` — binary (MessagePack)

Latest per-strike greeks snapshot. **MessagePack** (~2.3 MB for SPX): `expiry_ms → strike → [call_row, put_row]`, ~8 values per row (v0/v1 bid/ask-like, v7 epoch-ms; per-position semantics unpublished). Decodes to 61 expiries × 791 strikes for SPX via `gex_binary.py greeks SPX`. Free tier: `v2/free_latest_greeks?sym=`.

### 5.2 `GET /v2/daily_greeks?sym={SYM}&date={YYYY-MM-DD}(&mkt_close={...})` — binary (MessagePack)

Same MessagePack layout for a historical day (~2.4 MB): `gex_binary.py greeks SPX 2026-07-23`. Free tier: `v2/free_daily_greeks`.

> If you only need walls/sums in JSON, `v3/equitiesBySyms` (§4.3) or `v1/concentration` (§6.4) remain the lighter options.

### 5.3 `GET /v2/skew?sym={SYM}`

Live skew surface snapshot. Nested structure `{today: {next: {day, dte, exp, greeks: {"<strike>": [[bid, ask, ...], [delta?...], ...]}}}}` — per-strike quote/greeks arrays. Free tier: `v2/free_skew`.

```json
{"today": {"next": {"day": 1784922270058, "dte": 3.01, "exp": 1785182400000,
  "greeks": {"3000": [[4395.5, 4414.7, "..."], [0, 0.05, "..."], "..."],
             "6325": [[1071, 1090.1, "..."], [0.05, 0.1, "..."], "..."]}}}}
```

### 5.4 `GET /v1/tilt?sym={SYM}`

Daily delta/gamma tilt history since 2018: `[{trade_date, upx, delta_tilt, gamma_tilt}, ...]`.

### 5.5 `GET /v1/optionsRiskReversal?sym={SYM}`

Daily risk-reversal history since 2020: `[{trade_date, rr}, ...]` (e.g. `{"trade_date": "2020-04-13T00:00:00.000Z", "rr": -0.15}`).

### 5.6 `GET /v1/rr?sym={SYM}`

RR with underlying price since 2021: `[{trade_date, rr, upx}, ...]`. Free tier: `v1/free_rr`.

### 5.7 `GET /v1/iv_stats?sym={SYM}(&date=...)` — binary (MessagePack)

IV statistics bundle, **MessagePack** (~296 KB, gzip in transit): `{30|60|90: {day_key: {delta: [9 floats]}}}` — three tenors, ~35–38 day-keys each, 31 delta points per day. Decode with `gex_binary.py ivstats SPX`. Free tier: `v1/free_iv_stats`. For ready-made JSON IV stats see `v3/equitiesBySyms` fields (`atm_iv30`, `iv_rank`, `rv30`, `fwd_garch`, `skew`, …).

---

## 6. Open interest & synthetic OI

### 6.1 `GET /v1/oi?sym={SYM}` — binary (MessagePack)

The deepest dataset in the product: **full OI by expiry × strike × market actor**, ~16 MB for SPX (519 expiries × ~10k strikes → ~39k populated records). **MessagePack**: `{expiry_ms: {strike: [put_record, call_record]}}`; each record has 22 fields — `bd_*` (broker-dealer), `mm_*` (market maker), `cust_*`, `procust_*`, `firm_*` gross buy/sell OI plus signed `cust_lt_100/100_199/gt_199` size-bucket nets (see §3.4 for verified semantics). Decode: `gex_binary.py oi SPX` → long-format parquet. `GET /v1/oi_syms` (JSON) lists covered symbols: `["A", "AA", ...]`.

### 6.2 `GET /v1/oi/{intradayStrikeOI|intradayStrikeGEX}?sym={SYM}&date={YYYY-MM-DD}` — binary (MessagePack)

Intraday per-strike OI / GEX, same MessagePack family as §6.1 (the app decodes it with the same msgpack reader). Discovered in the EquityHub OI view.

### 6.3 `GET /v2/curve?sym={SYM}&models={LIST}&limit={N}`

Gamma curve models (used by the options-calculator view). `models` is a comma-separated model list.

### 6.4 `GET /v1/concentration?syms={LIST}&groupBy={strike|expiration}`

OI/volume/delta/gamma aggregated per strike or per expiry — **JSON, immediately usable**:

```json
// groupBy=strike
[{"underlying": "SPX", "type": "put", "strike": 200, "oi": "45642", "volume": "1",
  "delta": -9015.94, "gamma": 7.04}, ...]
// groupBy=expiration
[{"underlying": "SPX", "type": "put", "expiration": "2026-07-27T00:00:00.000Z",
  "oi": "254385", "volume": "243413", "delta": -21943543786.68, "gamma": 179153473.24}, ...]
```

### 6.5 `GET /synth_oi/v1/equities?date={YYYY-MM-DD}`

SpotGamma's **synthetic OI** model per symbol — richer variants of the v4 metrics (different sums/ratios). Full-table response; the dashboard calls it on home load. Free tier: `synth_oi/v1/free_equities`.

```json
[{"quote_date": "2026-07-23T04:00:00.000Z", "sym": "SPX", "upx": 7408.3,
  "callsum": 11095875, "putsum": 14268235, "cv": 825848, "pv": 1050252,
  "stock_volume": 3390767785, "put_call_ratio": 1.2859,
  "gamma_ratio": "0.7411", "delta_ratio": "0.5312",
  "large_call_oi": 7000, "large_put_oi": 7000,
  "skew": -0.4291, "atm_iv30": 0.1547, "rv30": 0.1039, "...": "..."}]
```

### 6.6 `GET /synth_oi/v1/chart_data?sym={SYM}(&date={YYYY-MM-DD})`

Pre-computed chart series for the synthetic-OI view: cumulative `curves` (delta/gamma × all/monthly/next_exp over a `spot_prices` axis) and per-strike `bars` (OI plus delta/gamma contributions by puts/calls).

### 6.7 `GET /synth_oi/v1/historical` / `GET /synth_oi/v1/last_update`

Historical synthetic-OI series (free tier: `free_historical`). `last_update` returns **plain text**, not JSON:

```
"2026-07-25T08:54:55-04:00"
```

### 6.8 `GET /synth_oi/v1/eh_symbols` and `GET /v1/eh_symbols`

Symbol → company-name map for EquityHub: `{"A": "Agilent Technologies, Inc.", "AA": "Alcoa Corp", ...}` (nulls for unnamed symbols).

---

## 7. HIRO order flow

HIRO is SpotGamma's real-time option order-flow signal. Signals: `mid_signal` (mid-price directional pressure), `gamma_signal`, `vega_signal`; `option_type` is `C`/`P`; `utc_time` is epoch **ms**.

### 7.1 `GET /v6/running_hiro`

The live HIRO watchlist table (all symbols, current day), polled by the dashboard. **Auth:** paid; free tier `v1/free_running_hiro`.

```json
[{"symbol": "AA", "day": "2026-07-24", "lastClose": 44.3,
  "companyName": "Alcoa Corporation", "sector": "Basic Materials",
  "low1": -827848.49, "high1": 281388.76,
  "low5": -5554570.64, "high5": 1244159.65,
  "low20": -9591872.86, "high20": 3812282.34,
  "currentDaySignal": "-824646.91", "currentDayPrice": "44.32"}]
```

`lowN`/`highN` = signal range over the last N days → where today's signal sits vs recent history.

### 7.2 `GET /v11/hiro?all=1&nextExp=1&retail=1&syms={SYM}&start={D}&end={D}`

HIRO history for one symbol over a date range. Response: `{SYM: {all: [...], nextExp: [...], retail: [...]}}` — each bucket present only if requested (`all=1` etc.). Free tier: `v1/free_hiro`.

```json
{"SPX": {"all": [
  {"instrument": "SPX", "mid_signal": -62176, "gamma_signal": -2958,
   "vega_signal": -369989, "option_type": "C", "stock_price": 7490.55,
   "utc_time": 1784779200000},
  {"instrument": "SPX", "mid_signal": -6868168, "gamma_signal": 100406,
   "vega_signal": 15174080, "option_type": "P", "stock_price": 7490.55,
   "utc_time": 1784779200000}]}}
```

### 7.3 `GET /v4/latestHiro?syms={LIST}&all=1&limit={N}`

The most recent HIRO prints (polled every ~60 s by the dashboard; `syms` dash-separated, `limit` up to 720 observed). Free tier: `v1/free_latest_hiro`.

```json
{"SPX": {"all": [
  {"instrument": "SPX", "mid_signal": 694633, "gamma_signal": 18169,
   "vega_signal": 7199996, "option_type": "C", "stock_price": 7409.9,
   "utc_time": 1784924080000}]}}
```

### 7.4 `GET /v3/trending?` (&interval=30)

Symbols ranked by HIRO trend strength: `[{symbol, trend, trend_abs, instrument}, ...]` (e.g. UBER at −3.27 on 2026-07-24). Polled every 30 s by the dashboard.

---

## 8. Market data & quotes

### 8.1 `GET /v1/prices?syms={DASH-LIST}`

Batch last prices — the watchlist endpoint. **Dash-separated** symbols:

```json
// v1/prices?syms=SPX
{"SPX": "7409.4"}
```

### 8.2 `GET /v1/twelve_quote?symbol={SYM}`

Full quote via Twelve Data. **Gotcha:** index symbols resolve to whatever instrument Twelve Data lists under that ticker — `symbol=SPX` returned an *Amundi S&P 500 UCITS ETF in EUR on Borsa Italiana*. For the CBOE index, prefer `v1/prices` or the futures endpoints.

### 8.3 `GET /v1/twelve_series?symbol={SYM}&interval={1min|1day}&...`

OHLCV candles (Twelve Data proxied). Variants observed in the app:

| Query | Use |
|---|---|
| `interval=1day&start_date={D}(&end_date={D})&order=asc` | daily history (home chart requests 7 years) |
| `interval=1min&outputsize=390&order=asc(&date={D})` | one full US session of 1-min bars |
| `interval=1min&outputsize={N}&order=desc(&start_date={D}&end_epoch={ms})` | latest N minutes |

```json
{"SPX": {"meta": {"symbol": "SPX", "interval": "1day", "exchange_timezone": "America/New_York"},
  "values": [{"datetime": "2026-07-20", "open": 7489.18, "high": 7513.23,
              "low": 7440.53, "close": 7443.28, "volume": "2741338417"}, "..."]}}
```

### 8.4 Futures endpoints

| Endpoint | Sample | Notes |
|---|---|---|
| `GET /v1/futures?sym={SYM}` | `{"S&P ES=F": {"all": [{stock_price, utc_time}, ...]}}` | recent tick series (today) |
| `GET /v1/futures/realtime?sym={SYM}` | same shape | latest tick polled repeatedly |
| `GET /v1/futures/mostRecentMarketOpen` | `[{"sym":"SPX","price":7407.75,"date":"2026-07-24"}, {"sym":"SPY",...}]` | **public** — works without Bearer |

Symbol encoding: `S&P ES=F` → `S%26P%20ES%3DF`. The keyLevels record's `futuresSym` (e.g. `/ESU26`) + `futuresDiff` tell you the active contract and spread vs spot.

### 8.5 `GET /v1/treasury_rates?date={YYYY-MM-DD}`

Bond-equivalent yields curve: `{"date": "2026-07-22", "days": [30, 45, ...], "be_yields": [0.0376, 0.0382, ...]}` (note the returned `date` can lag the requested one).

### 8.6 `GET /v1/dividends?sym={SYM}&start={D}&end={D}(&exclude_forecast=true)`

Dividend events in range (empty array for SPX in Jul 2026).

### 8.7 `GET /v1/equityPutCallRatio`

Market-wide equity put/call ratios since 2020: `[{trade_date, vol_ratio, oi_ratio}, ...]`.

### 8.8 `GET /v1/correlation_regime?sym={SYM}`

Referenced by the dashboard bundle, but **returned 404 on both hosts** during live probing (2026-07-25) — treat as deprecated/unavailable.

---

## 9. Scanners, compass & trending

### 9.1 `GET /v1/equityScanners`

Scanner-ranked equities (garch/vrp/squeeze flags + full metric set), latest `quote_date`. Free tier: `v1/free_equityScanners`.

```json
[{"quote_date": "2026-07-24T00:00:00.000Z", "sym": "SLS",
  "name": "SELLAS Life Sciences Group Inc", "upx": 11.32,
  "atm_iv30": 2.3525, "rv30": 1.4717, "iv_rank": 0.9703,
  "garch_scanner": 1, "vrp_scanner_high": 1, "squeeze_scanner": null,
  "callsum": 624265, "putsum": 259022, "delta_ratio": -12.2453, "...": "..."}]
```

Scanner flag fields: `garch_scanner`, `vrp_scanner`, `vrp_scanner_high`, `squeeze_scanner` (`1` = triggered, `null` = not).

### 9.2 `GET /v1/compass?syms={LIST}&x={price|skew}`

Compass quadrant placement per symbol: `[{"bollingerBand": "0.20408802", "sym": "SPX", "rsi": "45.22759"}]`. `x` selects the x-axis metric.

### 9.3 `GET /v1/compass_hist?syms={LIST}&lookback={DAYS}`

Daily compass history per symbol — handy for wall/IV tracking:

```json
{"SPX": [
  {"close": 7411.98, "trade_date": "2026-07-24T00:00:00.000Z",
   "iv_rank": 0.2797, "skew_rank": 0.196, "cws": 7600, "pws": 7300,
   "atm_iv30": 0.1471, "rv30": 0.1013}, "..."]}
```

### 9.4 `GET /v3/trending?`

HIRO trend ranking — see §7.4.

---

## 10. Calendars & alerts

### 10.1 `GET /v1/earnings?start={D}&end={D}` or `?syms={LIST}`

Earnings calendar. Two forms: date range (home widget uses ±1 month) or symbol list. Empty array when nothing matches (`syms=SPX` → `[]`). Free tier: `v1/free_earnings`.

### 10.2 `GET /v1/fmp/api/v3/economic_calendar?from={D}&to={D}`

Macro calendar (Financial Modeling Prep proxied through SpotGamma):

```json
[{"date": "2026-08-01 00:00:00", "country": "KR", "event": "Imports YoY (Jul)",
  "currency": "KRW", "previous": 30.1, "estimate": null, "actual": null,
  "impact": "Low", "unit": "%"}, "..."]
```

### 10.3 `GET /v1/alerts?syms={LIST}&start={D}&end={D}`

Triggered SpotGamma alerts for symbols in range (empty for SPX on 2026-07-23/24).

### 10.4 Alert management (account, all Bearer-gated)

`GET /v1/me/alerts` · `GET /v1/me/alerts?limit=100&alertID={N}` · `GET /v1/me/alertsByDays?days={1|5}` · `POST /v1/me/markOlderAlertsSeen` · `POST /v1/users/saveAlertsSettings`. The dashboard also polls `GET /v1/me/notifications?days={N}` and `GET /v1/me/pollUpdate?features={url-encoded JSON}` for badge counts.

---

## 11. Streaming platform

A separate backend at `https://api.stream.spotgamma.com` powers the intraday/streaming features. Same Bearer `sgToken` (its `TOKEN` getter reads `localStorage.sgToken`), same static headers. Verified live.

### 11.1 Infra

| Endpoint | Live result |
|---|---|
| `GET /status` | `{"repo_git_hash": "9bc6a142...", "able_to_decode_jwt": true}` |
| `GET /validate_bearer` | Decodes your token — see §2.2 (`roles`, `memberships`, `exp`) |
| `GET /auth` | 400 with only Authorization header — expects a different auth header |
| `GET /sg/manifest` | Streaming universe: `underlyings` (e.g. `/ESH27:XCME`) and `combos` mapping display names to shards/symbols (`"S&P 500" → price_sym "SPX"`) |

### 11.2 Intraday open interest (JSON)

From the generated OpenAPI client in the bundle — all `GET /v2/open_interest/...`:

| Endpoint | Query params | Live status |
|---|---|---|
| `intraday_stats` | `sym`, `date` | **200** — distribution stats per greek (charm etc.): `{charm: {"180": {bd: {charm_neg: {max, mean, min, percentiles, std}, ...}}}}` |
| `intraday_strike_bars` | `symbol`, `bar_type`, `date` | **200** — **Parquet** (~2.6 MB, duckdb-readable): `strike_price, timestamp, {bd,cust,firm,mm,procust}_{gamma|delta}` + `*_0` variants. Returns a trailing multi-day window, not just `date`. Decode: `gex_binary.py bars SPX gamma` |
| `intraday_gamma` | `symbol`, `date`, `ts`, `mkt_actor` | 400 without `ts` — timestamp required |
| `intraday_delta` | `symbol`, `date`, `ts`, `mkt_actor` | 400 without `ts` |
| `intraday_timestamps` | `symbol`, `greek`, `date`, `mkt_actor` | 400 — likely needs a valid `greek` enum value |

### 11.3 Intraday series (JSON)

| Endpoint | Query params (from client spec) | Live status |
|---|---|---|
| `GET /candles` | `sym, stream, field, option, filter, limit, start, end` | **200** — `{"symbol": "SPX", "candles": [[ts_ms, price, ...], ...]}` with just `sym` + `limit` |
| `GET /prices` | `symbol, time_gte, time_lt, candle_duration_ms, limit` | 400 without time bounds |
| `GET /delta_signal` | `symbol, option_accumulation_type, option_origin, is_filtered, time_gte, time_lt, candle_duration_ms, limit` | 400 without time bounds |
| `GET /vix_quote` | `dates` | **200** — VX futures term structure: `{"items": [{"sym": "/VXF27:XCBF", "time": "...", "open": 22.175, ..., "expiration_date": "2027-01-20"}, ...]}` |
| `GET /sg/tns_contracts`, `/sg/tns_feed`, `/sg/tns_flow_sum` | `filters, sorting, offset, limit` | TNS (unusual-flow) feed; `filters` is a JSON-encoded object |
| `GET /sg/tns_highlights` | `start, end` | TNS highlights by date range |

### 11.4 WebSocket

```
wss://bbg.stream.spotgamma.com/stream?token=<url-encoded sgToken>
```

Used by the dashboard for live HIRO/EHIRO streaming and TNS push. Discovered in the bundle (`G2e="bbg.stream.spotgamma.com"`); not exercised in probing.

---

## 12. Content & account

### 12.1 Content

| Endpoint | Notes |
|---|---|
| `GET /home/contentForCategory?category={tooltips\|...}` | UI copy blocks for the home screen |
| `GET /foundersNotes?page={N}&perPage={N}(&month=&year=)` | Founder's Notes archive — `{status, page, hasNextPage, data: [{title, category, html, key, date, id}]}` (verified) |
| `GET /foundersNotes/id?id={N}` / `GET /foundersNotes/preview?previewKey={K}` | Single note / unpublished preview |
| `GET /v1/zendesk_article?id={N}` | Support article body |
| `GET /v1/allReviews` | User reviews/testimonials |

### 12.2 Account (`/v1/me/*`, all Bearer-gated)

`GET /v1/login` · `GET /v1/me/user` — profile & entitlements · `GET /v1/me/refresh` — session refresh · `GET /v1/me/settings` / save preferences · `GET /v1/me/position(s)` / `?ids=` — saved positions · `GET /v1/me/watchlists` · `GET /v1/me/tnsFilters` (CRUD, `POST/PUT/DELETE` variants) · `GET/POST /v1/me/canvas/workspaces` (+ `/containers/{id}/components`) — dashboard layouts · `GET /v1/me/institutionalForm`, `/saveIsInstitutional` · `GET /v1/me/review?key=`, `POST /v1/me/submitReview` · `POST /v1/me/markNotificationsSeen`.

### 12.3 Discord integration

`GET /discord_login?redir={path}` (OAuth start) · `GET /discord_login_callback?code={}&redir={}` · `POST /discord/updateRole?auth={}&userid={}`.

---

## 13. Error reference

| Situation | Response |
|---|---|
| Missing/expired Bearer on gated endpoint | `403` `{"error":{"message":"Invalid authorization: <empty>"}}` (or the token string when present-but-invalid) |
| Endpoint on wrong host / removed path | `404` Express HTML page (`Cannot GET /...`) — e.g. stream-host paths on `api.spotgamma.com`, or `v1/correlation_regime` anywhere |
| Missing required query param (stream host) | `400` with compressed/plain error body (e.g. `invalid HTTP header (authorization)` for `/auth`) |
| Garbled response bytes | gzip/brotli: send `Accept-Encoding: gzip, deflate` and decompress (§3.5) |
| `application/octet-stream` | Binary payload by design (§3.4) — Arrow IPC, Parquet, or custom packed format |

Retry guidance from the app's own fetch wrapper: it retries idempotent GETs once on network failure; it does **not** hammer 4xx. Follow the same courtesy — and re-read the token instead of retrying 403s.

---

## 14. Local tooling

Everything in this workspace is built on this API:

| File | What it does |
|---|---|
| `gex_scraper.py` | Pulls §4.1 + §4.4 nightly (weekdays 22:17 ET via Automation) into `gex_data.db` (`key_levels`, `equities_gex`, `scrape_runs`). Auto-refreshes the token via WebBridge. CLI: `python3 gex_scraper.py [--skip-equities] [--db PATH]` |
| `plot_spx_gamma.py` | Renders the per-strike gamma map (walls/flip/spot) from the DB: `python3 plot_spx_gamma.py [--sym QQQ] [--date 2026-07-23]` |
| `probe_api.py` → `probes.json` | The live probe run behind this document — 61 endpoint results with real SPX samples |
| `gex_binary.py` | Decoders for every binary endpoint (§3.4): `oi`, `greeks`, `ivstats`, `bars` subcommands; reuses the scraper's auth. Needs `msgpack` (pip) + `duckdb` (already in the runtime). Outputs long-format parquet under `data/` |
| nightly archive | The scheduled «GEX Scraper → SQLite» task (weekdays 22:17 ET) also archives the full SPX per-actor OI matrix each run via `gex_binary.archive_oi()` → `data/oi/oi_spx_{date}.parquet` (~0.7 MB/day, deduped by ET date); optional inputs: `skip_oi`, `oi_sym` |
| `sg_token.txt` | Current session token (gitignore this; ~3-day lifetime) |
| `spotgamma-api-endpoints.md` | Compact endpoint index (quick lookup companion to this doc) |

**Minimal request recipe:**

```python
import urllib.request, json

BASE = "https://api.spotgamma.com"
HEADERS = {
    "x-json-web-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                        "eyJpYXQiOjE2NjgxMjgyNDJ9."
                        "0VtbQW99MELrgb4JW56xtbRdh1LAbDBlB1T78dJlILA",
    "Content-Type": "application/json",
    "Version": "5613",
    "App-Type": "web",
    "Authorization": f"Bearer {open('sg_token.txt').read().strip()}",
}
req = urllib.request.Request(f"{BASE}/home/keyLevels?includeGammaCurve=1", headers=HEADERS)
data = json.loads(urllib.request.urlopen(req, timeout=30).read())
spx = next(r for r in data["data"] if r["sym"] == "SPX")
print(spx["callwallstrike"], spx["putwallstrike"], spx["zero_g_strike"])
# -> 7600 7300 7420
```

---

*Document generated 2026-07-25 from live probing of the SpotGamma dashboard API (subscription: Alpha). Endpoint availability and schemas can change without notice — the `Version: 5613` header pins the app version these findings were captured against.*
