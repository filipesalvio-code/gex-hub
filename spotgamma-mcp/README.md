# spotgamma-mcp

MCP server (stdio) for the **SpotGamma Dashboard API**, generated from
[`../spotgamma-api-endpoints.md`](../spotgamma-api-endpoints.md) — the endpoint
catalog discovered 2026-07-25 from `https://dashboard.spotgamma.com/home`.

Exposes **45 tools** covering every endpoint group in the catalog: GEX/gamma
levels, greeks, skew/IV, open interest (incl. synthetic OI), HIRO order flow,
market data, calendars, scanners/Compass, content, plus a `spotgamma_raw_get`
escape hatch for any remaining path (e.g. `v1/me/*` account endpoints).

📖 **[DOCUMENTATION.md](DOCUMENTATION.md)** — full per-tool reference with live
SPX examples for all 45 tools (regenerate with `node examples-runner.js &&
node generate-docs.js`).

## Install

```bash
cd spotgamma-mcp
npm install
```

Requires Node.js 18+ (developed on Node 24; uses global `fetch`).

## Configuration

Public/free endpoints work with the static app token baked into the SpotGamma
web bundle (already included). Gated endpoints (`/v4/*`, `/v6/*`,
`/v3/equitiesBySyms`, `/v1/me/*`, …) additionally need your user token:

| Env var | Purpose |
|---|---|
| `SPOTGAMMA_SG_TOKEN` | Bearer token = value of `localStorage["sgToken"]` after logging in at dashboard.spotgamma.com (DevTools → Application → Local Storage). |
| `SPOTGAMMA_OPEN_HOUSE_TOKEN` | Optional `x-open-house-token` header. |

Endpoints with unpaid-tier variants (`v1/free_equities`, `v1/free_running_hiro`,
`v2/free_skew`, …) are reachable via each tool's `use_free` flag and work
without a Bearer token.

## Client config

**Kimi Work**: already registered at
`~/Library/Application Support/kimi-desktop/daimon-share/daimon/runtime/kimi-code/home/mcp.json`
(file mode `600`) with `SPOTGAMMA_SG_TOKEN` in `env`. Restart Kimi (or start a
new session) to pick it up. The sgToken JWT expires ~3 days after issue — when
gated tools start returning 403, re-copy `localStorage["sgToken"]` from an
active dashboard.spotgamma.com session into that `env` block.

Claude Desktop / any other MCP client:

```json
{
  "mcpServers": {
    "spotgamma": {
      "command": "node",
      "args": ["/Users/filipesalvio/gex-hub/spotgamma-mcp/server.js"],
      "env": {
        "SPOTGAMMA_SG_TOKEN": "<your sgToken — optional>"
      }
    }
  }
}
```

## Tool groups

| Group | Tools |
|---|---|
| GEX / Gamma | `spotgamma_key_levels`, `spotgamma_equities_gex`, `spotgamma_equities_by_syms` 🔒, `spotgamma_historical_gex`, `spotgamma_combo_levels`, `spotgamma_home_all_data` |
| Greeks / Skew / IV | `spotgamma_latest_greeks`, `spotgamma_daily_greeks`, `spotgamma_skew`, `spotgamma_tilt`, `spotgamma_risk_reversal`, `spotgamma_rr`, `spotgamma_iv_stats` |
| Open Interest | `spotgamma_oi_intraday` ⚠, `spotgamma_oi`, `spotgamma_oi_syms`, `spotgamma_concentration`, `spotgamma_synth_oi_equities`, `spotgamma_synth_oi_chart_data`, `spotgamma_synth_oi_historical`, `spotgamma_synth_oi_last_update`, `spotgamma_synth_oi_eh_symbols`, `spotgamma_synth_oi_equity_scanners` |
| HIRO | `spotgamma_running_hiro`, `spotgamma_hiro_history`, `spotgamma_latest_hiro` |
| Market data | `spotgamma_prices`, `spotgamma_quote`, `spotgamma_series`, `spotgamma_futures`, `spotgamma_most_recent_market_open`, `spotgamma_treasury_rates`, `spotgamma_dividends`, `spotgamma_zero_dte`, `spotgamma_equity_put_call_ratio`, `spotgamma_correlation_regime`, `spotgamma_trending` |
| Calendars | `spotgamma_earnings`, `spotgamma_economic_calendar` |
| Scanners / Compass | `spotgamma_equity_scanners`, `spotgamma_compass`, `spotgamma_compass_hist` |
| Content / misc | `spotgamma_content_for_category`, `spotgamma_founders_notes`, `spotgamma_raw_get` |

🔒 = auth required, no free variant. ⚠ = `/v2/open_interest/intraday_*`
currently returns **404 even with a token** (verified 2026-07-25); the tool is
kept with the exact query schema from the app bundle in case the routes come
back.

## Verified live (2026-07-25, no Bearer token)

- `spotgamma_most_recent_market_open` → SPX/SPY last open ✅
- `spotgamma_key_levels` → SPX call/put walls, zero-gamma, levels_with_pct ✅
- `spotgamma_equities_gex` (`use_free: true`) ✅
- `spotgamma_running_hiro` (`use_free: true`) ✅
- `spotgamma_trending`, `spotgamma_prices`, `spotgamma_earnings` (free) ✅
- `spotgamma_equities_by_syms` → 403 without token (correctly flagged 🔒)

## Test

```bash
node test-client.js
```

Spawns the server over stdio, lists all tools, and calls two public endpoints.

## Notes

- Responses are JSON, truncated at ~200 KB with a notice (narrow the query or
  use `spotgamma_raw_get` with tighter params).
- `spotgamma_equities_gex` supports `syms_filter` for client-side row filtering
  of the large GEX table.
- The static app token and `Version: 5613` header are hardcoded per the
  catalog; bump `API_VERSION` in `server.js` if the app bundle updates.
