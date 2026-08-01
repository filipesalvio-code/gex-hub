// Generates DOCUMENTATION.md from per-tool metadata + live captured examples
// (examples-output.json). Run: node generate-docs.js
import { readFileSync, writeFileSync } from "node:fs";

const examples = JSON.parse(readFileSync("examples-output.json", "utf8"));
const TODAY = "2026-07-25";

// --- helpers ---------------------------------------------------------------

function mask(text) {
  return text
    // strip control chars (except \t \n \r) that leak in from API payloads
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "")
    .replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, "<email>")
    .replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, "<jwt>");
}

function sampleBlock(name) {
  const ex = examples[name];
  if (!ex) return "_no example captured_\n";
  let s = mask(ex.sample);
  if (ex.error) {
    // keep only the meaningful first line of API errors
    const firstLine = s.split("\n").find((l) => l.trim().length > 0) ?? s;
    return `\`\`\`\n${firstLine.trim()}\n\`\`\`\n`;
  }
  const CAP = 900;
  if (s.length > CAP) {
    s = s.slice(0, CAP).replace(/\n[^\n]*$/, ""); // cut at line boundary
    s += `\n… [truncated — full response ${ex.bytes.toLocaleString()} chars]`;
  }
  return `\`\`\`json\n${s}\n\`\`\`\n`;
}

function argsBlock(name) {
  const ex = examples[name];
  return `\`\`\`json\n${JSON.stringify({ name, arguments: ex.args }, null, 2)}\n\`\`\`\n`;
}

function paramsTable(rows) {
  if (!rows || rows.length === 0) return "_No parameters._\n";
  const esc = (s) => String(s).replace(/\|/g, "\\|");
  let out = "| Parameter | Type | Required | Description |\n|---|---|---|---|\n";
  for (const [n, ty, req, d] of rows) out += `| \`${n}\` | ${esc(ty)} | ${req} | ${esc(d)} |\n`;
  return out;
}

// --- metadata ---------------------------------------------------------------
// [endpoint, explanation, params, notes]

const GROUPS = [
  {
    title: "GEX / Gamma (core)",
    blurb:
      "Gamma-exposure data: SPX key levels, the full equity GEX table, per-symbol profiles, and historical series.",
    tools: {
      spotgamma_key_levels: [
        "GET /home/keyLevels",
        "The dashboard's headline SPX gamma map. Returns the call wall, put wall, zero-gamma strike (`zero_g_strike`), max-gamma strike, gamma notional, UPX, `levels_with_pct` (strike + strength score), the strike list, greeks (theta/vega/delta), and — when `include_gamma_curve` is set — the full per-strike gamma curve (`current_list`). This is the tool to reach for first when asked “where are the SPX gamma levels?”.",
        [["include_gamma_curve", "boolean", "no", "Include the full gamma curve (`current_list`). Default false."]],
        "Public endpoint — works without a token. SPX-only by design.",
      ],
      spotgamma_equities_gex: [
        "GET /v4/equities (free: /v1/free_equities)",
        "Full equity GEX table — one row per symbol with `upx` (expected move / “UPX”), `callsum`, `putsum`, `minfs`, earnings timestamp, next-expiry gamma split (`next_exp_call_gamma` / `next_exp_put_gamma`), ATM gamma/delta per side (`atmgc/atmgp/atmdc/atmdp`), put/call volume (`pv/cv`) and more. Large payload (~115 KB even filtered); use `syms_filter` to keep only the rows you need.",
        [
          ["use_free", "boolean", "no", "Use the unpaid-tier `/v1/free_equities` (works without a token, fewer fields)."],
          ["syms_filter", "string[]", "no", "Client-side row filter, e.g. `[\"SPX\"]`. Case-insensitive."],
        ],
        "Gated (403 without token). Free variant verified working without a token.",
      ],
      spotgamma_equities_by_syms: [
        "GET /v3/equitiesBySyms",
        "Per-symbol GEX profile for a specific trade date — same field family as the equities table but date-addressed. The app requests the previous trading day.",
        [
          ["syms", "string", "yes", "Symbol, e.g. `SPX`."],
          ["date", "YYYY-MM-DD", "no", "Profile date; API default when omitted."],
        ],
        "Gated (403 without token; no free variant).",
      ],
      spotgamma_historical_gex: [
        "GET /v4/historical (free: /v1/free_historical)",
        "Historical GEX time series. Very large payload (hits the ~200 KB server cap) — pass narrowing params via `params` (e.g. symbol/date filters as accepted by the API).",
        [
          ["use_free", "boolean", "no", "Use `/v1/free_historical`."],
          ["params", "object", "no", "Extra query params passed through as-is."],
        ],
        "Gated. The example call passed `{\"sym\":\"SPX\"}` and still returned a multi-symbol payload — server-side filtering is limited; expect to post-filter.",
      ],
      spotgamma_combo_levels: [
        "GET /v2/comboLevels",
        "Combined gamma levels per symbol — a compact level set (call/put walls, zero-gamma, nearby strikes) used by the app's per-symbol views.",
        [
          ["sym", "string", "yes", "Symbol, e.g. `SPX`."],
          ["next_exp", "string|number|boolean", "no", "`nextExp` flag/value."],
          ["params", "object", "no", "Extra query params."],
        ],
        "Verified public (returned data with no token attached).",
      ],
      spotgamma_home_all_data: [
        "GET /home/allData",
        "Aggregate home payload the dashboard loads for its main view — a bundle of the day's key datasets in one response.",
        [],
        "Verified public.",
      ],
    },
  },
  {
    title: "Greeks / Skew / IV",
    blurb: "Option greeks snapshots and history, skew, tilt, risk reversal, and IV statistics.",
    tools: {
      spotgamma_latest_greeks: [
        "GET /v2/latest_greeks (free: /v2/free_latest_greeks)",
        "Latest greeks snapshot for a symbol — the full option-chain greeks grid (per strike/expiry). Very large for SPX (hits the ~200 KB cap); post-filter by strike/expiry client-side.",
        [
          ["sym", "string", "yes", "Symbol."],
          ["use_free", "boolean", "no", "Use the free variant."],
        ],
        "Gated; free variant available.",
      ],
      spotgamma_daily_greeks: [
        "GET /v2/daily_greeks (free: /v2/free_daily_greeks)",
        "Daily greeks history for a symbol on a given date — the per-strike greeks series the app charts.",
        [
          ["sym", "string", "yes", "Symbol."],
          ["date", "YYYY-MM-DD", "yes", "Trade date."],
          ["mkt_close", "string|number|boolean", "no", "`mkt_close` flag/value."],
          ["use_free", "boolean", "no", "Use the free variant."],
        ],
        "Gated; free variant available.",
      ],
      spotgamma_skew: [
        "GET /v2/skew (free: /v2/free_skew)",
        "Skew dataset powering the app's skew chart. Large payload.",
        [
          ["use_free", "boolean", "no", "Use the free variant."],
          ["params", "object", "no", "Extra query params."],
        ],
        "Gated; free variant available.",
      ],
      spotgamma_tilt: [
        "GET /v1/tilt",
        "Tilt metric for a symbol — SpotGamma's call/put skew tilt reading. Large per-strike payload for SPX.",
        [["sym", "string", "yes", "Symbol."]],
        "Verified public (worked with no token attached).",
      ],
      spotgamma_risk_reversal: [
        "GET /v1/optionsRiskReversal",
        "Options risk-reversal data for a symbol (25-delta style call/put IV spread series).",
        [["sym", "string", "yes", "Symbol."]],
        "Verified public.",
      ],
      spotgamma_rr: [
        "GET /v1/rr (free: /v1/free_rr)",
        "Risk-reversal chart series (the RR chart in the dashboard).",
        [
          ["sym", "string", "yes", "Symbol."],
          ["use_free", "boolean", "no", "Use the free variant."],
        ],
        "Gated; free variant available.",
      ],
      spotgamma_iv_stats: [
        "GET /v1/iv_stats (free: /v1/free_iv_stats)",
        "IV statistics for a symbol — IV percentile/rank style aggregates plus term structure stats. Large payload.",
        [
          ["sym", "string", "yes", "Symbol."],
          ["date", "YYYY-MM-DD", "no", "Optional date."],
          ["use_free", "boolean", "no", "Use the free variant."],
        ],
        "Gated; free variant available.",
      ],
    },
  },
  {
    title: "Open Interest (incl. synthetic OI)",
    blurb:
      "Classical open interest, OI concentration, and SpotGamma's synthetic-OI (Equity Hub) datasets.",
    tools: {
      spotgamma_oi_intraday: [
        "GET /v2/open_interest/intraday_{kind}",
        "Intraday OI endpoints from the app bundle: `gamma`, `delta`, `stats`, `strike_bars`, `timestamps`. The exact query schema (from the bundle): gamma/delta → `symbol,date,ts,mkt_actor`; stats → `sym,date`; strike_bars → `symbol,bar_type,date`; timestamps → `symbol,greek,date,mkt_actor`.",
        [
          ["kind", "enum", "yes", "`gamma` | `delta` | `stats` | `strike_bars` | `timestamps`."],
          ["symbol", "string", "yes", "Underlying, e.g. `SPX`."],
          ["date", "YYYY-MM-DD", "no", "Trade date."],
          ["ts", "string", "no", "Timestamp (gamma/delta)."],
          ["mkt_actor", "string", "no", "Market-actor filter."],
          ["greek", "string", "no", "Greek name (timestamps)."],
          ["bar_type", "string", "no", "Bar type (strike_bars)."],
        ],
        "⚠ STALE: all five routes return **404 even with a valid token** (verified " + TODAY + "). Kept for completeness.",
      ],
      spotgamma_oi: [
        "GET /v1/oi · GET /v1/oi/{exp}",
        "Open interest for a symbol — full chain OI by strike/expiry (very large for SPX). Pass `expiration` to use the per-expiry variant.",
        [
          ["sym", "string", "yes", "Symbol."],
          ["expiration", "string", "no", "Expiration for `/v1/oi/{exp}`."],
          ["params", "object", "no", "Extra query params."],
        ],
        "Gated (403 without token).",
      ],
      spotgamma_oi_syms: [
        "GET /v1/oi_syms",
        "List of symbols that have OI data available.",
        [],
        "Gated (403 without token).",
      ],
      spotgamma_concentration: [
        "GET /v1/concentration",
        "OI concentration — where open interest clusters, grouped by `strike` or `expiration`. Large payload for SPX.",
        [
          ["syms", "string", "yes", "Comma-separated symbols."],
          ["group_by", "enum", "yes", "`strike` | `expiration`."],
        ],
        "Verified public (worked with no token attached).",
      ],
      spotgamma_synth_oi_equities: [
        "GET /synth_oi/v1/equities (free: …/free_equities)",
        "Synthetic-OI equity table for a date — the Equity Hub dataset fired on home load. Very large payload.",
        [
          ["date", "YYYY-MM-DD", "yes", "Data date."],
          ["use_free", "boolean", "no", "Use the free variant."],
        ],
        "Gated; free variant available.",
      ],
      spotgamma_synth_oi_chart_data: [
        "GET /synth_oi/v1/chart_data",
        "Synthetic-OI chart series. Query schema is not fully documented — pass params through (`sym` accepted). Large payload.",
        [["params", "object", "no", "Query params passed through as-is."]],
        "Gated (403 without token).",
      ],
      spotgamma_synth_oi_historical: [
        "GET /synth_oi/v1/historical (free: …/free_historical)",
        "Historical synthetic-OI series.",
        [
          ["use_free", "boolean", "no", "Use the free variant."],
          ["params", "object", "no", "Extra query params."],
        ],
        "Gated; free variant available.",
      ],
      spotgamma_synth_oi_last_update: [
        "GET /synth_oi/v1/last_update",
        "Synthetic-OI last-update timestamp (US/Eastern).",
        [],
        "Verified public.",
      ],
      spotgamma_synth_oi_eh_symbols: [
        "GET /synth_oi/v1/eh_symbols",
        "Equity Hub symbol universe — all symbols covered by synthetic OI, with metadata. Large payload.",
        [],
        "Verified public.",
      ],
      spotgamma_synth_oi_equity_scanners: [
        "GET /synth_oi/v1/equityScanners",
        "Synthetic-OI scanner definitions/results (Equity Hub scans).",
        [["params", "object", "no", "Extra query params."]],
        "Gated (403 without token).",
      ],
    },
  },
  {
    title: "HIRO (order flow)",
    blurb: "SpotGamma's HIRO order-flow signals: live running list, per-symbol history, and latest ticks.",
    tools: {
      spotgamma_running_hiro: [
        "GET /v6/running_hiro (free: /v1/free_running_hiro)",
        "Live running HIRO list — every covered symbol with the current day signal, price, and 1/5/20-day signal ranges (`low1/high1/low5/high5/low20/high20`). The paid tier includes the numeric signals; the free variant returns symbol metadata only.",
        [["use_free", "boolean", "no", "Use the free variant (no token needed, fewer fields)."]],
        "Gated; free variant verified without token.",
      ],
      spotgamma_hiro_history: [
        "GET /v11/hiro",
        "HIRO history per symbol with flags for all expiries / next expiry / retail flow.",
        [
          ["syms", "string", "yes", "Symbol(s)."],
          ["start", "string", "no", "Start (API format)."],
          ["all", "boolean", "no", "`all=1` flag."],
          ["next_exp", "boolean", "no", "`nextExp=1` flag."],
          ["retail", "boolean", "no", "`retail=1` flag."],
          ["params", "object", "no", "Extra query params."],
        ],
        "Gated (403 without token). The SPX example returned a small/empty payload — history depth may require a `start` value.",
      ],
      spotgamma_latest_hiro: [
        "GET /v4/latestHiro (free: /v1/free_latest_hiro)",
        "Latest HIRO ticks — the most recent order-flow prints. App uses `limit=720`.",
        [
          ["syms", "string", "no", "Comma-separated symbols."],
          ["all", "boolean", "no", "`all=1` flag."],
          ["limit", "integer", "no", "Row limit."],
          ["use_free", "boolean", "no", "Use the free variant."],
        ],
        "Gated; free variant available.",
      ],
    },
  },
  {
    title: "Market data",
    blurb: "Quotes, bars, futures, rates, and breadth/positioning datasets.",
    tools: {
      spotgamma_prices: [
        "GET /v1/prices",
        "Batch last-price quotes for a watchlist (symbols joined with `-` on the wire).",
        [["syms", "string[]", "yes", "Symbols, e.g. `[\"SPX\",\"SPY\"]`."]],
        "Verified public.",
      ],
      spotgamma_quote: [
        "GET /v1/twelve_quote",
        "Single full quote (Twelve Data proxied): open/high/low/close, change, volume, 52-week range.",
        [["symbol", "string", "yes", "Symbol."]],
        "Verified public.",
      ],
      spotgamma_series: [
        "GET /v1/twelve_series",
        "Time-series bars (Twelve Data proxied). Intraday: `interval=1min&outputsize=390&order=asc(&date=…)`. Daily: `interval=1day&start_date=…(&end_date=…)&order=asc`.",
        [
          ["symbol", "string", "yes", "Symbol."],
          ["interval", "string", "yes", "e.g. `1min`, `5min`, `1day`."],
          ["outputsize", "integer", "no", "Max bars."],
          ["order", "enum", "no", "`asc` | `desc`."],
          ["date", "YYYY-MM-DD", "no", "Single day (intraday)."],
          ["start_date", "YYYY-MM-DD", "no", "Range start (daily)."],
          ["end_date", "YYYY-MM-DD", "no", "Range end (daily)."],
        ],
        "Verified public.",
      ],
      spotgamma_futures: [
        "GET /v1/futures · GET /v1/futures/realtime",
        "Futures snapshot — e.g. `S&P ES=F` for ES (S&P 500 e-mini). Returns the full contract table (large payload). `realtime` switches to the realtime variant.",
        [
          ["sym", "string", "yes", "Futures symbol, e.g. `S&P ES=F`."],
          ["realtime", "boolean", "no", "Use `/v1/futures/realtime`."],
        ],
        "Verified public.",
      ],
      spotgamma_most_recent_market_open: [
        "GET /v1/futures/mostRecentMarketOpen",
        "SPX/SPY prices at the most recent market open. Tiny, fast, public — good connectivity check.",
        [],
        "Verified public (catalog-confirmed).",
      ],
      spotgamma_treasury_rates: [
        "GET /v1/treasury_rates",
        "US Treasury yield curve for a date (1M–30Y).",
        [["date", "YYYY-MM-DD", "yes", "Rates date."]],
        "Verified public.",
      ],
      spotgamma_dividends: [
        "GET /v1/dividends",
        "Dividend data. Note: SPX is an index — the example returned an empty array; use paying symbols (e.g. `SPY`) for dividend rows.",
        [["params", "object", "no", "Query params passed through."]],
        "Verified public.",
      ],
      spotgamma_zero_dte: [
        "GET /v1/zeroDTE",
        "0DTE data for a symbol — same-day expiry positioning/greeks. Very large payload for SPX.",
        [
          ["sym", "string", "yes", "Symbol."],
          ["params", "object", "no", "Extra query params."],
        ],
        "Verified public.",
      ],
      spotgamma_equity_put_call_ratio: [
        "GET /v1/equityPutCallRatio",
        "Equity put/call ratio chart series (market-wide).",
        [],
        "Verified public.",
      ],
      spotgamma_correlation_regime: [
        "GET /v1/correlation_regime",
        "Correlation regime for a symbol.",
        [["sym", "string", "yes", "Symbol."]],
        "⚠ STALE: returns **404** (verified " + TODAY + "). Per the app bundle, `correlation_regime` now arrives as a field inside other payloads.",
      ],
      spotgamma_trending: [
        "GET /v3/trending",
        "Trending symbols ranked by trend score (absolute move vs. expectation).",
        [["interval", "integer", "no", "Interval in minutes (app uses 30)."]],
        "Verified public.",
      ],
    },
  },
  {
    title: "Calendars",
    blurb: "Earnings and macro-economic calendars.",
    tools: {
      spotgamma_earnings: [
        "GET /v1/earnings (free: /v1/free_earnings)",
        "Earnings calendar by date range or symbol list. Rows include `sym`, `day`, `utc`, `period` (BMO/AMC), `confirmed`, `implied_move`, call/put volume, `activity_factor`, `inHiro`. Large payload for wide ranges.",
        [
          ["start", "YYYY-MM-DD", "no", "Range start."],
          ["end", "YYYY-MM-DD", "no", "Range end."],
          ["syms", "string", "no", "Comma-separated symbols."],
          ["use_free", "boolean", "no", "Use the free variant (verified without token)."],
        ],
        "Gated; free variant verified without token.",
      ],
      spotgamma_economic_calendar: [
        "GET /v1/fmp/api/v3/economic_calendar",
        "Macro-economic calendar (FMP proxied): releases with estimate/actual, country, impact.",
        [
          ["from", "YYYY-MM-DD", "yes", "Range start."],
          ["to", "YYYY-MM-DD", "yes", "Range end."],
        ],
        "Verified public.",
      ],
    },
  },
  {
    title: "Scanners / Compass",
    blurb: "Equity scanners and SpotGamma Compass indicators.",
    tools: {
      spotgamma_equity_scanners: [
        "GET /v1/equityScanners (free: /v1/free_equityScanners)",
        "Equity scanner definitions and results (gamma/OI-driven scans).",
        [
          ["use_free", "boolean", "no", "Use the free variant."],
          ["params", "object", "no", "Extra query params."],
        ],
        "Gated; free variant available.",
      ],
      spotgamma_compass: [
        "GET /v1/compass",
        "Compass snapshot per symbol — currently returns `rsi` and `bollingerBand` readings.",
        [["syms", "string", "yes", "Comma-separated symbols."]],
        "Verified public.",
      ],
      spotgamma_compass_hist: [
        "GET /v1/compass_hist",
        "Compass history per symbol — the Compass time series.",
        [["syms", "string", "yes", "Comma-separated symbols."]],
        "Gated (403 without token).",
      ],
    },
  },
  {
    title: "Content / misc + escape hatch",
    blurb: "Dashboard content endpoints and the generic passthrough for anything not wrapped.",
    tools: {
      spotgamma_content_for_category: [
        "GET /home/contentForCategory",
        "CMS content for a dashboard category (e.g. `tooltips` — the UI's explanatory copy).",
        [["category", "string", "yes", "Category key, e.g. `tooltips`."]],
        "Verified public.",
      ],
      spotgamma_founders_notes: [
        "GET /foundersNotes · /foundersNotes/id · /foundersNotes/preview",
        "Founders Notes blog: paged listing (`page/perPage/month/year`), single note (`id`), or preview (`preview_key`). Listing is a large payload.",
        [
          ["page", "integer", "no", "Page number."],
          ["per_page", "integer", "no", "Items per page."],
          ["month", "integer", "no", "Filter month (1–12)."],
          ["year", "integer", "no", "Filter year."],
          ["id", "integer", "no", "Fetch one note by id."],
          ["preview_key", "string", "no", "Preview key."],
        ],
        "Gated (403 without token).",
      ],
      spotgamma_raw_get: [
        "GET {any path}",
        "Escape hatch: GET any catalog path with arbitrary query params — including the account endpoints (`/v1/me/user`, `/v1/me/watchlists`, `/v1/me/alerts`, …) and misc routes (`/v2/occ`, `/v1/allReviews`, `/v1/zendesk_article`, …). Set `auth: true` for gated paths.",
        [
          ["path", "string", "yes", "API path starting with `/`."],
          ["params", "object", "no", "Query params passed through."],
          ["auth", "boolean", "no", "Require/attach Bearer token (default: attach when configured)."],
        ],
        "Example shows `/v1/me/user` (gated) — account profile with memberships.",
      ],
    },
  },
];

// --- render -----------------------------------------------------------------

const GROUP_OF = {};
for (const g of GROUPS) for (const n of Object.keys(g.tools)) GROUP_OF[n] = g.title;

let md = `# spotgamma-mcp — Tool Documentation

MCP server for the **SpotGamma Dashboard API** (\`https://api.spotgamma.com\`), generated from
\`spotgamma-api-endpoints.md\`. **45 tools** across ${GROUPS.length} groups.

Every example below was executed live against the production API on **${TODAY}**
with SPX-oriented arguments (Alpha subscriber token). Outputs are trimmed for
readability; full byte counts are noted.

## Calling a tool

MCP tools are invoked by name with a JSON arguments object:

\`\`\`json
{ "name": "spotgamma_key_levels", "arguments": { "include_gamma_curve": true } }
\`\`\`

## Authentication

| Layer | Value |
|---|---|
| Static app token | Sent automatically on every request (hardcoded in the SpotGamma web bundle) |
| User token | \`SPOTGAMMA_SG_TOKEN\` env var — value of \`localStorage["sgToken"]\` after login; **automatically attached to every request when set** (mirrors the web app) |
| Free tier | Tools with \`use_free\` call the unpaid \`free_\` variant — no token needed |
| Expiry | sgToken JWT lasts ~3 days; re-copy from the browser when gated tools start 403-ing |

**Auth matrix (verified ${TODAY}):**

- **Public, no token needed:** key_levels, home_all_data, combo_levels, tilt, risk_reversal, prices, quote, series, futures, most_recent_market_open, treasury_rates, dividends, zero_dte, equity_put_call_ratio, trending, economic_calendar, compass, content_for_category, synth_oi_last_update, synth_oi_eh_symbols, concentration — plus every \`use_free\` variant.
- **Gated (403 without token):** equities_gex, equities_by_syms, historical_gex, latest_greeks, daily_greeks, skew, rr, iv_stats, oi, oi_syms, synth_oi_equities, synth_oi_chart_data, synth_oi_historical, synth_oi_equity_scanners, running_hiro, hiro_history, latest_hiro, earnings, equity_scanners, compass_hist, founders_notes, \`/v1/me/*\` via raw_get.
- **Stale (404 even with token):** oi_intraday (all kinds), correlation_regime.

**Conventions:** dates are \`YYYY-MM-DD\`; responses are JSON truncated at ~200 KB with a notice;
\`params\` arguments pass straight through to the query string.

---
`;

let toc = "## Contents\n\n";
let body = "";
let idx = 0;
for (const g of GROUPS) {
  idx++;
  toc += `${idx}. [${g.title}](#${idx}-${g.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")})\n`;
  body += `\n## ${idx}. ${g.title}\n\n${g.blurb}\n`;
  for (const [name, [endpoint, explanation, params, notes]] of Object.entries(g.tools)) {
    body += `\n### \`${name}\`\n\n`;
    body += `**Endpoint:** \`${endpoint}\`\n\n`;
    body += `${explanation}\n\n`;
    body += `**Parameters**\n\n${paramsTable(params)}\n`;
    body += `\n**Example call (SPX)**\n\n${argsBlock(name)}\n`;
    body += `\n**Example output (live, ${TODAY})**\n\n${sampleBlock(name)}\n`;
    body += `\n> **Note:** ${notes}\n`;
  }
}

md += toc + "\n---\n" + body;

writeFileSync("DOCUMENTATION.md", md);
console.log(`DOCUMENTATION.md written (${md.length} chars, ${Object.keys(examples).length} tools)`);
