# SpotGamma Dashboard API — Endpoint Catalog

Discovered: 2026-07-25 from `https://dashboard.spotgamma.com/home` via live network capture + static analysis of the app bundle (`index-CuGCoWOa.js`, `PollingWorker-CpJqDE6X.js`).

## Base configuration

| Item | Value |
|---|---|
| Base URL | `https://api.spotgamma.com` |
| Static app token (hardcoded in bundle) | `x-json-web-token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE2NjgxMjgyNDJ9.0VtbQW99MELrgb4JW56xtbRdh1LAbDBlB1T78dJlILA` |
| Required headers | `Content-Type: application/json`, `Version: 5613`, `App-Type: web` |
| User auth (gated endpoints) | `Authorization: Bearer <sgToken>` — token stored in `localStorage["sgToken"]` (set from the `sgToken` cookie after login) |
| Optional header | `x-open-house-token` (when present) |

### Verified behavior
- `GET /v1/futures/mostRecentMarketOpen` with static headers only → **200** (public/free data).
- `GET /v4/equities` with static headers only → **403** `{"error":{"message":"Invalid authorization: <empty>"}}`.
- `GET /v4/equities` with static headers + `Bearer <sgToken>` → **200** full dataset.
- Endpoints prefixed `free_` are the unpaid-tier variants the app falls back to (e.g. `v1/free_equities` vs `v4/equities`, `v1/free_running_hiro` vs `v6/running_hiro`).

## GEX / Gamma (core)

| Endpoint | Notes |
|---|---|
| `GET /home/keyLevels?includeGammaCurve={0\|1}` | SPX key levels: `callwallstrike`, `putwallstrike`, `zero_g_strike`, `max_g_strike`, `gamma_not`, `upx`, `levels_with_pct`, `strike_list` + `current_list` (gamma curve), `futuresSym`, greeks (theta/vega/delta). Verified live. |
| `GET /v3/equitiesBySyms?syms={SYM}&date={YYYY-MM-DD}` | Per-symbol GEX profile for a date (app requests previous day). |
| `GET /v4/equities` | Full equity GEX table: `sym`, `name`, `upx`, `callsum`, `putsum`, `minfs`, `earnings_utc`, … Verified live (auth required). |
| `GET /v4/historical` | Historical GEX series. |
| `GET /v2/comboLevels?sym={SYM}(&nextExp…)` | Combined gamma levels per symbol. |
| `GET /home/allData` | Aggregate home payload. |
| Free variants | `GET /v1/free_equities`, `GET /v1/free_historical` |

## Greeks / Skew / IV

| Endpoint | Notes |
|---|---|
| `GET /v2/latest_greeks?sym={SYM}` | Latest greeks snapshot. |
| `GET /v2/daily_greeks?sym={SYM}&date={YYYY-MM-DD}(&mkt_close={...})` | Daily greeks history. |
| `GET /v2/skew` / `GET /v2/free_skew` | Skew data. |
| `GET /v1/tilt?sym={SYM}` | Tilt metric. |
| `GET /v1/optionsRiskReversal?sym={SYM}` | Risk reversal. |
| `GET /v1/rr?sym={SYM}` / `GET /v1/free_rr?sym={SYM}` | RR chart series. |
| `GET /v1/iv_stats?sym={SYM}(&date=…)` / `GET /v1/free_iv_stats?sym={SYM}` | IV statistics. |
| `GET /v2/free_latest_greeks?sym={SYM}`, `GET /v2/free_daily_greeks?sym={SYM}&date={D}&mkt_close={T}` | Free variants. |

## Open Interest (incl. synthetic OI)

| Endpoint | Notes |
|---|---|
| `GET /v2/open_interest/intraday_gamma` | Intraday gamma OI. |
| `GET /v2/open_interest/intraday_delta` | Intraday delta OI. |
| `GET /v2/open_interest/intraday_stats` | Intraday OI stats. |
| `GET /v2/open_interest/intraday_strike_bars` | Per-strike intraday bars. |
| `GET /v2/open_interest/intraday_timestamps` | Available intraday timestamps. |
| `GET /v1/oi?sym={SYM}` / `GET /v1/oi/{exp}?{params}` / `GET /v1/oi_syms` | OI data & symbol list. |
| `GET /v1/concentration?syms={LIST}&groupBy={strike\|expiration}` | OI concentration. |
| `GET /synth_oi/v1/equities?date={YYYY-MM-DD}` | Synthetic OI equities (fired on home load). |
| `GET /synth_oi/v1/free_equities?date={D}` | Free variant (`{param}equities` = `free_` toggle). |
| `GET /synth_oi/v1/chart_data?{params}` | Synthetic OI chart data. |
| `GET /synth_oi/v1/historical` / `GET /synth_oi/v1/free_historical` | Historical synthetic OI. |
| `GET /synth_oi/v1/last_update` | Last update timestamp. |
| `GET /synth_oi/v1/eh_symbols` | Equity Hub symbol list. |
| `GET /synth_oi/v1/equityScanners` | Scanner definitions/results. |

## HIRO (order flow)

| Endpoint | Notes |
|---|---|
| `GET /v6/running_hiro` | Live running HIRO list (polled). Auth required. |
| `GET /v1/free_running_hiro` | Free variant. |
| `GET /v11/hiro?all=1&nextExp=1&retail=1&syms={SYM}&start={…}` | HIRO history per symbol. |
| `GET /v4/latestHiro?all=1&limit=720` / `?syms={LIST}&all=1&limit={N}` | Latest HIRO ticks. |
| `GET /v1/free_hiro?{params}` / `GET /v1/free_latest_hiro?{params}` | Free variants. |

## Market data

| Endpoint | Notes |
|---|---|
| `GET /v1/prices?syms={DASH-SEPARATED-LIST}` | Batch quotes (watchlist). Observed live. |
| `GET /v1/twelve_quote?symbol={SYM}` | Single quote (Twelve Data proxied). |
| `GET /v1/twelve_series?symbol={S}&interval=1min&outputsize=390&order=asc(&date={D})` | Intraday bars. |
| `GET /v1/twelve_series?symbol={S}&interval=1day&start_date={D}(&end_date={D})&order=asc` | Daily bars. Observed live (ES futures 1day). |
| `GET /v1/futures?sym={SYM}` | Futures snapshot (e.g. `sym=S%26P%20ES%3DF`). |
| `GET /v1/futures/realtime?sym={SYM}` | Realtime futures. |
| `GET /v1/futures/mostRecentMarketOpen` | SPX/SPY last open. Public. |
| `GET /v1/treasury_rates?date={D}` | Treasury rates. |
| `GET /v1/dividends?{params}` | Dividends. |
| `GET /v1/zeroDTE?sym={SYM…}` | 0DTE data. |
| `GET /v1/equityPutCallRatio` | Equity put/call ratio chart. |
| `GET /v1/correlation_regime?sym={SYM}` | Correlation regime. |
| `GET /v3/trending?&interval=30` | Trending symbols. |

## Calendars

| Endpoint | Notes |
|---|---|
| `GET /v1/earnings?start={D}&end={D}` / `?syms={LIST}` | Earnings calendar. Observed live. |
| `GET /v1/free_earnings?start={D}&end={D}` | Free variant. |
| `GET /v1/fmp/api/v3/economic_calendar?from={D}&to={D}` | Macro calendar (FMP proxied). Observed live. |

## Scanners / Compass

| Endpoint | Notes |
|---|---|
| `GET /v1/equityScanners` / `GET /v1/free_equityScanners` | Equity scanners. |
| `GET /v1/compass?syms={LIST}` / `GET /v1/compass_hist?syms={LIST}` | Compass data. |

## Auth / account (`v1/me/*` — all Bearer-gated)

`GET /v1/login` · `GET /v1/me/user` · `GET /v1/me/refresh` · `GET /v1/me/settings` · `GET /v1/me/pollUpdate?features={JSON}` · `GET /v1/me/position(s)` · `GET /v1/me/positions?ids={…}` · `GET /v1/me/watchlists` · `GET /v1/me/alerts` · `GET /v1/me/alerts?limit=100&alertID={N}` · `GET /v1/me/alertsByDays?days={1\|5}` · `GET /v1/me/notifications?days={N}` · `POST /v1/me/markNotificationsSeen` · `POST /v1/me/markOlderAlertsSeen` · `/v1/me/tnsFilters` (CRUD) · `/v1/me/canvas/workspaces` (CRUD) · `/v1/me/institutionalForm` · `/v1/me/review?key={K}` · `/v1/me/submitReview` · `POST /v1/users/saveAlertsSettings` · Discord: `/discord_login?redir={…}` · `/discord_login_callback?code={…}&redir={…}` · `/discord/updateRole?auth={…}&userid={…}`

## Content / misc

`GET /home/contentForCategory?category={tooltips|…}` · `GET /foundersNotes?page={N}&perPage={N}&month={M}&year={Y}` · `GET /foundersNotes/id?id={N}` · `GET /foundersNotes/preview?previewKey={K}` · `GET /v1/zendesk_article?id={N}` · `GET /v1/allReviews` · `GET /v2/occ` · `POST /v1/moviefone/chat` (+ `/followup`)

## Observed live on `/home` load (2026-07-23 session)

`v1/me/refresh` → `v1/me/user` → `v4/equities` → `v6/running_hiro` → `home/keyLevels` (×2) → `v3/equitiesBySyms?syms=SPX` → `v1/futures` + `v1/futures/realtime` + `mostRecentMarketOpen` → `v1/twelve_series` (ES 1day) → `v1/earnings` → `v1/fmp/.../economic_calendar` → `synth_oi/v1/equities` + `eh_symbols` + `equityScanners` → `home/contentForCategory?category=tooltips` → `v1/prices` (watchlist) → `v1/me/alerts` → `v1/me/pollUpdate` (polled).

## Minimal scraping recipe (Python)

```python
import requests

BASE = "https://api.spotgamma.com"
HEADERS = {
    "x-json-web-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE2NjgxMjgyNDJ9.0VtbQW99MELrgb4JW56xtbRdh1LAbDBlB1T78dJlILA",
    "Content-Type": "application/json",
    "Version": "5613",
    "App-Type": "web",
    "Authorization": f"Bearer {SG_TOKEN}",  # from localStorage["sgToken"] after login
}
r = requests.get(f"{BASE}/home/keyLevels?includeGammaCurve=1", headers=HEADERS)
levels = r.json()["data"][0]  # callwallstrike, putwallstrike, zero_g_strike, gamma curve, ...
```
