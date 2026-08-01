# API Reference

This workspace exposes two kinds of callable surfaces: **MCP tool servers**
(for AI assistants) and **Python CLIs** (for scheduled/interactive scraping
and analysis). For the upstream REST endpoints themselves, see the catalogs:
[../API_ENDPOINTS.md](../API_ENDPOINTS.md) (MenthorQ),
[../spotgamma-api-endpoints.md](../spotgamma-api-endpoints.md) and
[../spotgamma-api-docs.md](../spotgamma-api-docs.md) (SpotGamma, with live
response samples).

---

## 1. MenthorQ MCP server — `mcp/menthorq_mcp.py`

Transport: newline-delimited JSON-RPC 2.0 on stdio, MCP protocol
`2024-11-05`. Zero dependencies, Python 3.8+. Registered in Kimi's `mcp.json`
as server `menthorq`.

### Authentication

Resolved per call, in order:

1. `MENTHORQ_TOKEN` env var — explicit Cognito `accessToken` (highest priority).
2. Kimi WebBridge — reads `/api/auth/session` from an open, logged-in
   `dashboard.menthorq.io` Chrome tab. Auto-opens a fresh tab if the probe
   lands on the wrong tab. Cached in memory 5 minutes; never written to disk.

Optional overrides: `MENTHORQ_BRIDGE_URL` (default
`http://127.0.0.1:10086/command`), `MENTHORQ_BRIDGE_SESSION` (default
`menthorq-scrape`).

### Response and error shape

Every tool returns text content of the form:

```json
{"http_status": 200, "data": { "...": "..." }}
```

- Non-2xx or unreachable-after-retries (`http_status: 0`) → `isError: true`.
- 429/5xx are retried up to 3 times with linear backoff (2 s, 4 s, 6 s) and a
  forced token refresh on retry.
- Session expiry surfaces as an actionable error:
  `"MenthorQ session expired — … log in again, then retry (or set MENTHORQ_TOKEN)."`
- Unknown tool name → JSON-RPC `-32602`; unknown method → `-32601`.

### Tools (24)

Full per-tool reference with real examples: [../mcp/MCP_DOCS.md](../mcp/MCP_DOCS.md)
(regenerate with `python3 mcp/gen_docs.py`).

| Group | Tools |
|---|---|
| Universe & prices | `menthorq_tickers`, `menthorq_prices`, `menthorq_market_status` |
| Gamma | `menthorq_gamma_levels`, `menthorq_gamma_insights`, `menthorq_gamma_insights_expirations` |
| Metrics | `menthorq_metrics_eod`, `menthorq_metrics_intraday` |
| Options | `menthorq_options_matrix`, `menthorq_put_call_ratio`, `menthorq_dealer_positioning` |
| Volatility | `menthorq_volatility_insights` |
| Charts | `menthorq_candles`, `menthorq_tradingview` |
| Screeners | `menthorq_screener`, `menthorq_screener_columns`, `menthorq_screener_templates` |
| News/events | `menthorq_qbot_assets`, `menthorq_events`, `menthorq_company_news` |
| Account | `menthorq_user_me`, `menthorq_watchlists`, `menthorq_chats`, `menthorq_chat_templates` |

**Upstream quirks to remember:** `market-status` supports NYSE/NASDAQ only;
`put-call-ratio` returns the latest snapshot, not a series; intraday metrics
accept only the literal fields `iv_1m_50d, iv_3m_50d, iv_0dte_50d, skew_1m,
skew_3m, skew_0dte`; candle intervals are case-sensitive (`1m..45m, 1h..4h,
1D, 1W, 1M`); futures tickers use provider format (`DATABENTO#ES`).

### Example (raw JSON-RPC on stdio)

```
→ {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"menthorq_gamma_levels","arguments":{"ticker":"SPX","frequency":"eod"}}}
← {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\"http_status\":200,\"data\":{...}}"}]}}
```

Tests: `python3 mcp/test_mcp.py` (5-call smoke), `python3 mcp/test_all.py`
(all 24 tools via the registered `mcp.json` command).

---

## 2. SpotGamma MCP server — `spotgamma-mcp/server.js`

Transport: stdio via `@modelcontextprotocol/sdk` (Node 18+, ESM, zod
schemas). Registered in Kimi's `mcp.json` as server `spotgamma`.

### Authentication

Every request sends the static app headers (`x-json-web-token`,
`Version: 5613`, `App-Type: web`). Additionally:

| Env var | Purpose |
|---|---|
| `SPOTGAMMA_SG_TOKEN` | Bearer token = `localStorage["sgToken"]` from a logged-in dashboard session. Sent on **every** request when present (mirrors the web app). Refreshed daily by `token_refresh.py`. |
| `SPOTGAMMA_OPEN_HOUSE_TOKEN` | Optional `x-open-house-token` header. |

Gated endpoints (`/v4/*`, `/v6/*`, `/v3/equitiesBySyms`, `/v1/me/*`) fail with
a clear "set SPOTGAMMA_SG_TOKEN" error when no token is set. Most have
unpaid-tier variants reachable via each tool's `use_free: true` flag.

### Response and error shape

- Success: text content with pretty-printed JSON, truncated at **200 KB**
  (with a truncation notice; narrow the query or use `spotgamma_raw_get`).
- Failure: `isError: true` with `Error: SpotGamma API <status> <statusText>: <body>`.
- `spotgamma_equities_gex` supports `syms_filter` (client-side row filtering).

### Tools (45)

Full per-tool reference with live SPX examples:
[../spotgamma-mcp/DOCUMENTATION.md](../spotgamma-mcp/DOCUMENTATION.md)
(regenerate with `node examples-runner.js && node generate-docs.js`).

| Group | Tools |
|---|---|
| GEX / Gamma | `spotgamma_key_levels`, `spotgamma_equities_gex`, `spotgamma_equities_by_syms` 🔒, `spotgamma_historical_gex`, `spotgamma_combo_levels`, `spotgamma_home_all_data` |
| Greeks / Skew / IV | `spotgamma_latest_greeks`, `spotgamma_daily_greeks`, `spotgamma_skew`, `spotgamma_tilt`, `spotgamma_risk_reversal`, `spotgamma_rr`, `spotgamma_iv_stats` |
| Open Interest | `spotgamma_oi`, `spotgamma_oi_syms`, `spotgamma_concentration`, `spotgamma_synth_oi_*` (6 tools), `spotgamma_oi_intraday` ⚠ |
| HIRO | `spotgamma_running_hiro`, `spotgamma_hiro_history`, `spotgamma_latest_hiro` |
| Market data | `spotgamma_prices`, `spotgamma_quote`, `spotgamma_series`, `spotgamma_futures`, `spotgamma_most_recent_market_open`, `spotgamma_treasury_rates`, `spotgamma_dividends`, `spotgamma_zero_dte`, `spotgamma_equity_put_call_ratio`, `spotgamma_correlation_regime` ⚠, `spotgamma_trending` |
| Calendars | `spotgamma_earnings`, `spotgamma_economic_calendar` |
| Scanners / Compass | `spotgamma_equity_scanners`, `spotgamma_compass`, `spotgamma_compass_hist` |
| Content / misc | `spotgamma_content_for_category`, `spotgamma_founders_notes`, `spotgamma_raw_get` (escape hatch for any path) |

🔒 = auth required, no free variant. ⚠ = route currently returns 404
upstream (verified 2026-07-25); kept for when it comes back.

### Example

```json
{"name": "spotgamma_key_levels", "arguments": {"include_gamma_curve": true}}
→ {"callwallstrike": 7600, "putwallstrike": 7300, "zero_g_strike": 7420, ...}

{"name": "spotgamma_equities_gex", "arguments": {"use_free": true, "syms_filter": ["SPX"]}}
→ [ {"sym": "SPX", "upx": 7409.4, "callsum": 3.15e9, ...} ]
```

Tests: `cd spotgamma-mcp && node test-client.js` (boot + 2 public calls),
`node test-auth.js` (token path).

---

## 3. Python CLIs

### `gex_scraper.py` — SpotGamma GEX → `gex_data.db`

```bash
python3 gex_scraper.py                  # full scrape (key levels + ~10k-symbol GEX)
python3 gex_scraper.py --skip-equities  # SPX key levels only
python3 gex_scraper.py --db other.db    # different database
python3 gex_scraper.py --quiet
```

Exit codes: `0` ok, `2` partial, `1` nothing scraped. Prints a JSON summary
(`status`, `trade_date`, row counts, errors, `token_refreshed`).
Auth: `SG_TOKEN` env → automatic WebBridge refresh on
401/403 or near-expiry (6 h margin). Stdlib only.
Schema: `key_levels(sym, trade_date, …curated cols…, raw_json)`,
`equities_gex(…)`, `scrape_runs` — upsert keyed on `(sym, trade_date)`.

### `gex_binary.py` (now in `attic/`) — binary payload decoders → `data/*.parquet`

```bash
python3 attic/gex_binary.py oi SPX          # per-actor OI matrix (MessagePack) → data/oi_spx.parquet
python3 attic/gex_binary.py greeks SPX      # latest greeks → data/greeks_spx_latest.parquet
python3 attic/gex_binary.py greeks SPX 2026-07-24   # dated greeks
python3 attic/gex_binary.py ivstats SPX     # IV stats summary (printed)
python3 attic/gex_binary.py bars SPX gamma  # intraday strike bars (Parquet) → data/strike_bars_spx_gamma.parquet
```

Requires `msgpack` and `duckdb` (Kimi managed runtime). Reuses
`gex_scraper.py` token handling. Library function
`archive_oi(sym)` writes deduped per-day files to `data/oi/` and never
raises — check `summary["status"]`. Greeks rows are positional (`v0..vN`);
per-position semantics are unpublished (see docstring).

### `plot_spx_gamma.py` — gamma-curve chart

```bash
python3 plot_spx_gamma.py                          # latest SPX → spx_gamma_curve.png
python3 plot_spx_gamma.py --sym QQQ --window 800
python3 plot_spx_gamma.py --date 2026-07-23 --out q.png
```

Reads `gex_data.db` only (offline). Two panels: per-strike call/put gamma
bars ($M, 25-pt bins) + SpotGamma total gamma curve ($B), with spot/call
wall/put wall/zero-gamma reference lines.

### `positioning_artifact.py` — dashboard artifact

`build_artifact()` → dict `{generated_at, oi_date, regime, walls, indices,
positioning, drift}` from `gex_data.db` + latest `data/oi/*.parquet`
(duckdb, offline). Consumed by the *SPX Positioning · MM vs Customer*
widget task.

---

## 4. Rate limits and politeness

- MenthorQ gateway: unknown formal limits; the client retries 429/5xx and
  campaign agents sleep ~0.4 s between calls, ≤5 agents concurrent.
- SpotGamma: no documented limits; `gex_scraper.py` makes 2 requests per run;
  the MCP server mirrors interactive app traffic.
- Neither server paginates: MenthorQ endpoints are single-shot; SpotGamma
  responses are truncated client-side at 200 KB.

## 5. Versioning

The SpotGamma static headers pin `Version: 5613` (hardcoded in
`gex_scraper.py` and `API_VERSION` in `server.js`). If the dashboard app
bundle updates, bump both. The endpoint catalogs date from 2026-07-25;
`probes.json` holds the raw probe results used to build them.
