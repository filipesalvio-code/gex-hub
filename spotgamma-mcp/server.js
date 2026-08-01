#!/usr/bin/env node
/**
 * spotgamma-mcp — MCP server for the SpotGamma Dashboard API.
 *
 * Built from spotgamma-api-endpoints.md (endpoint catalog discovered
 * 2026-07-25 from https://dashboard.spotgamma.com/home).
 *
 * Transport: stdio. Auth: static app token (hardcoded in the SpotGamma web
 * bundle) for public endpoints + optional Bearer token from env for
 * gated endpoints:
 *   SPOTGAMMA_SG_TOKEN        — value of localStorage["sgToken"] after login
 *   SPOTGAMMA_OPEN_HOUSE_TOKEN— optional x-open-house-token header
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const BASE_URL = "https://api.spotgamma.com";
const STATIC_APP_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE2NjgxMjgyNDJ9.0VtbQW99MELrgb4JW56xtbRdh1LAbDBlB1T78dJlILA";
const API_VERSION = "5613";
const MAX_CHARS = 200_000; // truncate oversized payloads

const SG_TOKEN = process.env.SPOTGAMMA_SG_TOKEN || process.env.SG_TOKEN || "";
const OPEN_HOUSE_TOKEN = process.env.SPOTGAMMA_OPEN_HOUSE_TOKEN || "";

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

function buildHeaders({ auth = false } = {}) {
  const headers = {
    "x-json-web-token": STATIC_APP_TOKEN,
    "Content-Type": "application/json",
    Version: API_VERSION,
    "App-Type": "web",
  };
  // Mirror the web app: once logged in it sends the Bearer token on EVERY
  // request. Many catalog endpoints turn out to be gated (403 "Invalid
  // authorization: <empty>"), so attach the token whenever we have one.
  if (SG_TOKEN) {
    headers["Authorization"] = `Bearer ${SG_TOKEN}`;
  } else if (auth) {
    throw new Error(
      "This endpoint requires a Bearer token. Set SPOTGAMMA_SG_TOKEN " +
        "(the value of localStorage['sgToken'] after logging in to " +
        "dashboard.spotgamma.com), or use the free variant if the tool offers one."
    );
  }
  if (OPEN_HOUSE_TOKEN) headers["x-open-house-token"] = OPEN_HOUSE_TOKEN;
  return headers;
}

async function sgGet(path, params = {}, { auth = false } = {}) {
  const url = new URL(path.startsWith("http") ? path : `${BASE_URL}${path}`);
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    url.searchParams.set(k, String(v));
  }
  const res = await fetch(url, { headers: buildHeaders({ auth }) });
  const text = await res.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = text;
  }
  if (!res.ok) {
    const msg =
      typeof body === "object" && body !== null
        ? JSON.stringify(body)
        : String(body).slice(0, 2000);
    throw new Error(`SpotGamma API ${res.status} ${res.statusText}: ${msg}`);
  }
  return body;
}

function jsonResult(data) {
  let text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  if (text.length > MAX_CHARS) {
    text =
      text.slice(0, MAX_CHARS) +
      `\n\n… [truncated at ${MAX_CHARS} chars — narrow the query or use spotgamma_raw_get with tighter params]`;
  }
  return { content: [{ type: "text", text }] };
}

function errResult(err) {
  return {
    isError: true,
    content: [{ type: "text", text: `Error: ${err.message}` }],
  };
}

/** Wrap a handler with error capture. */
function run(fn) {
  return async (args) => {
    try {
      return jsonResult(await fn(args));
    } catch (err) {
      return errResult(err);
    }
  };
}

// ---------------------------------------------------------------------------
// Server
// ---------------------------------------------------------------------------

const server = new McpServer(
  { name: "spotgamma-mcp", version: "1.0.0" },
  {
    instructions:
      "SpotGamma Dashboard API: GEX/gamma levels, greeks, skew/IV, open interest " +
      "(incl. synthetic OI), HIRO order flow, market data, calendars, scanners and " +
      "Compass. Public endpoints work out of the box; gated endpoints need " +
      "SPOTGAMMA_SG_TOKEN. Many gated endpoints have unpaid-tier free_ variants " +
      "exposed via each tool's use_free flag.",
  }
);

const t = (name, description, schema, handler) =>
  server.registerTool(name, { description, inputSchema: schema }, run(handler));

// Shared schema fragments -------------------------------------------------

const useFree = z
  .boolean()
  .optional()
  .describe("Use the unpaid-tier free_ variant of this endpoint.");
const dateStr = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .describe("Date in YYYY-MM-DD format.");
const extraParams = z
  .record(z.union([z.string(), z.number(), z.boolean()]))
  .optional()
  .describe("Extra query-string params to pass through as-is.");

// =========================================================================
// GEX / Gamma (core)
// =========================================================================

t(
  "spotgamma_key_levels",
  "SPX key gamma levels: call wall, put wall, zero-gamma strike, max gamma " +
    "strike, gamma notional, UPX, levels_with_pct, strike list and (optionally) " +
    "the full gamma curve plus greeks (theta/vega/delta). Verified live/public.",
  {
    include_gamma_curve: z
      .boolean()
      .optional()
      .describe("Include the gamma curve (current_list). Default false."),
  },
  async ({ include_gamma_curve }) =>
    sgGet("/home/keyLevels", {
      includeGammaCurve: include_gamma_curve ? 1 : 0,
    })
);

t(
  "spotgamma_equities_gex",
  "Full equity GEX table (v4/equities): sym, name, upx, callsum, putsum, " +
    "minfs, earnings_utc, etc. Auth required (SPOTGAMMA_SG_TOKEN); set use_free " +
    "for the unpaid variant (v1/free_equities).",
  {
    use_free: useFree,
    syms_filter: z
      .array(z.string())
      .optional()
      .describe(
        "Client-side filter: only return rows whose sym is in this list."
      ),
  },
  async ({ use_free, syms_filter }) => {
    const data = await sgGet(use_free ? "/v1/free_equities" : "/v4/equities", {}, { auth: !use_free });
    if (!syms_filter || syms_filter.length === 0) return data;
    const wanted = new Set(syms_filter.map((s) => s.toUpperCase()));
    const rows = Array.isArray(data) ? data : data?.data;
    if (!Array.isArray(rows)) return data;
    const filtered = rows.filter(
      (r) => r && typeof r === "object" && wanted.has(String(r.sym ?? "").toUpperCase())
    );
    return Array.isArray(data) ? filtered : { ...data, data: filtered };
  }
);

t(
  "spotgamma_equities_by_syms",
  "Per-symbol GEX profile for a given date (the app requests the previous " +
    "trading day). AUTH REQUIRED (verified 403 without SPOTGAMMA_SG_TOKEN; no " +
    "free variant exists).",
  {
    syms: z.string().describe("Symbol, e.g. SPX."),
    date: dateStr.optional().describe("Profile date; defaults to API default."),
  },
  async ({ syms, date }) => sgGet("/v3/equitiesBySyms", { syms, date }, { auth: true })
);

t(
  "spotgamma_historical_gex",
  "Historical GEX series. Auth: gated (use_free for v1/free_historical).",
  { use_free: useFree, params: extraParams },
  async ({ use_free, params }) =>
    sgGet(use_free ? "/v1/free_historical" : "/v4/historical", params ?? {}, { auth: !use_free })
);

t(
  "spotgamma_combo_levels",
  "Combined gamma levels per symbol (v2/comboLevels).",
  {
    sym: z.string().describe("Symbol, e.g. SPX."),
    next_exp: z
      .union([z.string(), z.number(), z.boolean()])
      .optional()
      .describe("nextExp flag/value."),
    params: extraParams,
  },
  async ({ sym, next_exp, params }) =>
    sgGet("/v2/comboLevels", { sym, nextExp: next_exp, ...(params ?? {}) })
);

t(
  "spotgamma_home_all_data",
  "Aggregate home payload (home/allData).",
  {},
  async () => sgGet("/home/allData")
);

// =========================================================================
// Greeks / Skew / IV
// =========================================================================

t(
  "spotgamma_latest_greeks",
  "Latest greeks snapshot for a symbol (free variant: v2/free_latest_greeks).",
  { sym: z.string(), use_free: useFree },
  async ({ sym, use_free }) =>
    sgGet(use_free ? "/v2/free_latest_greeks" : "/v2/latest_greeks", { sym }, { auth: !use_free })
);

t(
  "spotgamma_daily_greeks",
  "Daily greeks history for a symbol and date.",
  {
    sym: z.string(),
    date: dateStr,
    mkt_close: z
      .union([z.string(), z.number(), z.boolean()])
      .optional()
      .describe("mkt_close flag/value."),
    use_free: useFree,
  },
  async ({ sym, date, mkt_close, use_free }) =>
    sgGet(
      use_free ? "/v2/free_daily_greeks" : "/v2/daily_greeks",
      { sym, date, mkt_close },
      { auth: !use_free }
    )
);

t(
  "spotgamma_skew",
  "Skew data (free variant: v2/free_skew).",
  { use_free: useFree, params: extraParams },
  async ({ use_free, params }) =>
    sgGet(use_free ? "/v2/free_skew" : "/v2/skew", params ?? {}, { auth: !use_free })
);

t(
  "spotgamma_tilt",
  "Tilt metric for a symbol.",
  { sym: z.string() },
  async ({ sym }) => sgGet("/v1/tilt", { sym })
);

t(
  "spotgamma_risk_reversal",
  "Options risk reversal for a symbol.",
  { sym: z.string() },
  async ({ sym }) => sgGet("/v1/optionsRiskReversal", { sym })
);

t(
  "spotgamma_rr",
  "RR chart series (free variant: v1/free_rr).",
  { sym: z.string(), use_free: useFree },
  async ({ sym, use_free }) =>
    sgGet(use_free ? "/v1/free_rr" : "/v1/rr", { sym }, { auth: !use_free })
);

t(
  "spotgamma_iv_stats",
  "IV statistics for a symbol, optionally for a date (free variant: " +
    "v1/free_iv_stats).",
  { sym: z.string(), date: dateStr.optional(), use_free: useFree },
  async ({ sym, date, use_free }) =>
    sgGet(use_free ? "/v1/free_iv_stats" : "/v1/iv_stats", { sym, date }, { auth: !use_free })
);

// =========================================================================
// Open Interest (incl. synthetic OI)
// =========================================================================

t(
  "spotgamma_oi_intraday",
  "Intraday open-interest endpoints: gamma, delta, stats, per-strike bars, or " +
    "available timestamps. NOTE 2026-07-25: these routes currently return 404 " +
    "even with a Bearer token — kept for completeness from the app bundle. " +
    "Query params per kind (from the app bundle): " +
    "gamma/delta → symbol, date, ts, mkt_actor; stats → symbol, date; " +
    "strike_bars → symbol, bar_type, date; timestamps → symbol, greek, date, mkt_actor.",
  {
    kind: z
      .enum(["gamma", "delta", "stats", "strike_bars", "timestamps"])
      .describe("Which intraday OI dataset."),
    symbol: z.string().describe("Underlying symbol, e.g. SPX."),
    date: dateStr.optional(),
    ts: z.string().optional().describe("Timestamp (gamma/delta kinds)."),
    mkt_actor: z.string().optional().describe("Market actor filter (gamma/delta/timestamps)."),
    greek: z.string().optional().describe("Greek name, e.g. gamma (timestamps kind)."),
    bar_type: z.string().optional().describe("Bar type (strike_bars kind)."),
    params: extraParams,
  },
  async ({ kind, symbol, date, ts, mkt_actor, greek, bar_type, params }) => {
    const base = { ...(params ?? {}) };
    if (kind === "stats") Object.assign(base, { sym: symbol, date });
    else if (kind === "strike_bars") Object.assign(base, { symbol, bar_type, date });
    else if (kind === "timestamps") Object.assign(base, { symbol, greek, date, mkt_actor });
    else Object.assign(base, { symbol, date, ts, mkt_actor });
    return sgGet(`/v2/open_interest/intraday_${kind}`, base);
  }
);

t(
  "spotgamma_oi",
  "Open interest for a symbol (v1/oi), or for a specific expiration " +
    "(v1/oi/{exp}).",
  {
    sym: z.string(),
    expiration: z.string().optional().describe("Expiration for v1/oi/{exp}."),
    params: extraParams,
  },
  async ({ sym, expiration, params }) => {
    if (expiration) return sgGet(`/v1/oi/${encodeURIComponent(expiration)}`, { sym, ...(params ?? {}) });
    return sgGet("/v1/oi", { sym, ...(params ?? {}) });
  }
);

t(
  "spotgamma_oi_syms",
  "List of symbols with OI data (v1/oi_syms).",
  {},
  async () => sgGet("/v1/oi_syms")
);

t(
  "spotgamma_concentration",
  "OI concentration for symbols, grouped by strike or expiration.",
  {
    syms: z.string().describe("Comma-separated symbol list."),
    group_by: z.enum(["strike", "expiration"]),
  },
  async ({ syms, group_by }) =>
    sgGet("/v1/concentration", { syms, groupBy: group_by })
);

t(
  "spotgamma_synth_oi_equities",
  "Synthetic OI equities for a date (fired on home load; free variant: " +
    "synth_oi/v1/free_equities).",
  { date: dateStr, use_free: useFree },
  async ({ date, use_free }) =>
    sgGet(`/synth_oi/v1/${use_free ? "free_equities" : "equities"}`, { date }, { auth: !use_free })
);

t(
  "spotgamma_synth_oi_chart_data",
  "Synthetic OI chart data.",
  { params: extraParams },
  async ({ params }) => sgGet("/synth_oi/v1/chart_data", params ?? {})
);

t(
  "spotgamma_synth_oi_historical",
  "Historical synthetic OI (free variant: synth_oi/v1/free_historical).",
  { use_free: useFree, params: extraParams },
  async ({ use_free, params }) =>
    sgGet(`/synth_oi/v1/${use_free ? "free_historical" : "historical"}`, params ?? {}, { auth: !use_free })
);

t(
  "spotgamma_synth_oi_last_update",
  "Synthetic OI last-update timestamp.",
  {},
  async () => sgGet("/synth_oi/v1/last_update")
);

t(
  "spotgamma_synth_oi_eh_symbols",
  "Equity Hub symbol list.",
  {},
  async () => sgGet("/synth_oi/v1/eh_symbols")
);

t(
  "spotgamma_synth_oi_equity_scanners",
  "Synthetic-OI scanner definitions/results.",
  { params: extraParams },
  async ({ params }) => sgGet("/synth_oi/v1/equityScanners", params ?? {})
);

// =========================================================================
// HIRO (order flow)
// =========================================================================

t(
  "spotgamma_running_hiro",
  "Live running HIRO list (polled by the app). Auth required; use_free for " +
    "the unpaid variant (v1/free_running_hiro).",
  { use_free: useFree },
  async ({ use_free }) =>
    sgGet(use_free ? "/v1/free_running_hiro" : "/v6/running_hiro", {}, { auth: !use_free })
);

t(
  "spotgamma_hiro_history",
  "HIRO history per symbol (v11/hiro).",
  {
    syms: z.string().describe("Symbol(s)."),
    start: z.string().optional().describe("Start (as accepted by the API)."),
    all: z.boolean().optional().describe("all=1 flag."),
    next_exp: z.boolean().optional().describe("nextExp=1 flag."),
    retail: z.boolean().optional().describe("retail=1 flag."),
    params: extraParams,
  },
  async ({ syms, start, all, next_exp, retail, params }) =>
    sgGet("/v11/hiro", {
      syms,
      start,
      all: all === undefined ? undefined : all ? 1 : 0,
      nextExp: next_exp === undefined ? undefined : next_exp ? 1 : 0,
      retail: retail === undefined ? undefined : retail ? 1 : 0,
      ...(params ?? {}),
    })
);

t(
  "spotgamma_latest_hiro",
  "Latest HIRO ticks (v4/latestHiro), optionally filtered to symbols. " +
    "use_free → v1/free_latest_hiro.",
  {
    syms: z.string().optional().describe("Comma-separated symbol list."),
    all: z.boolean().optional(),
    limit: z.number().int().positive().optional().describe("Row limit (app uses 720)."),
    use_free: useFree,
  },
  async ({ syms, all, limit, use_free }) =>
    sgGet(
      use_free ? "/v1/free_latest_hiro" : "/v4/latestHiro",
      { syms, all: all === undefined ? undefined : all ? 1 : 0, limit },
      { auth: !use_free }
    )
);

// =========================================================================
// Market data
// =========================================================================

t(
  "spotgamma_prices",
  "Batch quotes for a watchlist (dash-separated symbols).",
  { syms: z.array(z.string()).min(1).describe("Symbols, e.g. [\"SPY\",\"QQQ\"].") },
  async ({ syms }) => sgGet("/v1/prices", { syms: syms.join("-") })
);

t(
  "spotgamma_quote",
  "Single quote (Twelve Data proxied).",
  { symbol: z.string() },
  async ({ symbol }) => sgGet("/v1/twelve_quote", { symbol })
);

t(
  "spotgamma_series",
  "Time series bars (Twelve Data proxied). Intraday: interval=1min with " +
    "outputsize/order/date. Daily: interval=1day with start_date/end_date.",
  {
    symbol: z.string(),
    interval: z.string().describe("e.g. 1min, 5min, 1day."),
    outputsize: z.number().int().positive().optional(),
    order: z.enum(["asc", "desc"]).optional(),
    date: dateStr.optional(),
    start_date: dateStr.optional(),
    end_date: dateStr.optional(),
  },
  async ({ symbol, interval, outputsize, order, date, start_date, end_date }) =>
    sgGet("/v1/twelve_series", {
      symbol,
      interval,
      outputsize,
      order,
      date,
      start_date,
      end_date,
    })
);

t(
  "spotgamma_futures",
  "Futures snapshot (e.g. sym='S&P ES=F' — app sends it URL-encoded) or the " +
    "realtime variant.",
  {
    sym: z.string().describe("Futures symbol, e.g. 'S&P ES=F'."),
    realtime: z.boolean().optional().describe("Use /v1/futures/realtime."),
  },
  async ({ sym, realtime }) =>
    sgGet(realtime ? "/v1/futures/realtime" : "/v1/futures", { sym })
);

t(
  "spotgamma_most_recent_market_open",
  "SPX/SPY last market open. Public — no auth needed.",
  {},
  async () => sgGet("/v1/futures/mostRecentMarketOpen")
);

t(
  "spotgamma_treasury_rates",
  "Treasury rates for a date.",
  { date: dateStr },
  async ({ date }) => sgGet("/v1/treasury_rates", { date })
);

t(
  "spotgamma_dividends",
  "Dividends data.",
  { params: extraParams },
  async ({ params }) => sgGet("/v1/dividends", params ?? {})
);

t(
  "spotgamma_zero_dte",
  "0DTE data for a symbol.",
  { sym: z.string(), params: extraParams },
  async ({ sym, params }) => sgGet("/v1/zeroDTE", { sym, ...(params ?? {}) })
);

t(
  "spotgamma_equity_put_call_ratio",
  "Equity put/call ratio chart.",
  {},
  async () => sgGet("/v1/equityPutCallRatio")
);

t(
  "spotgamma_correlation_regime",
  "Correlation regime for a symbol. NOTE 2026-07-25: /v1/correlation_regime " +
    "currently returns 404 — the correlation_regime data now arrives as a " +
    "field inside other payloads per the app bundle. Kept for completeness.",
  { sym: z.string() },
  async ({ sym }) => sgGet("/v1/correlation_regime", { sym })
);

t(
  "spotgamma_trending",
  "Trending symbols.",
  { interval: z.number().int().optional().describe("Interval in minutes (app uses 30).") },
  async ({ interval }) => sgGet("/v3/trending", { interval })
);

// =========================================================================
// Calendars
// =========================================================================

t(
  "spotgamma_earnings",
  "Earnings calendar, by date range or by symbols (free variant: " +
    "v1/free_earnings).",
  {
    start: dateStr.optional(),
    end: dateStr.optional(),
    syms: z.string().optional().describe("Comma-separated symbol list."),
    use_free: useFree,
  },
  async ({ start, end, syms, use_free }) =>
    sgGet(use_free ? "/v1/free_earnings" : "/v1/earnings", { start, end, syms }, { auth: !use_free })
);

t(
  "spotgamma_economic_calendar",
  "Macro/economic calendar (FMP proxied).",
  { from: dateStr, to: dateStr },
  async ({ from, to }) =>
    sgGet("/v1/fmp/api/v3/economic_calendar", { from, to })
);

// =========================================================================
// Scanners / Compass
// =========================================================================

t(
  "spotgamma_equity_scanners",
  "Equity scanners (free variant: v1/free_equityScanners).",
  { use_free: useFree, params: extraParams },
  async ({ use_free, params }) =>
    sgGet(use_free ? "/v1/free_equityScanners" : "/v1/equityScanners", params ?? {}, { auth: !use_free })
);

t(
  "spotgamma_compass",
  "Compass data for symbols.",
  { syms: z.string().describe("Comma-separated symbol list.") },
  async ({ syms }) => sgGet("/v1/compass", { syms })
);

t(
  "spotgamma_compass_hist",
  "Compass history for symbols.",
  { syms: z.string().describe("Comma-separated symbol list.") },
  async ({ syms }) => sgGet("/v1/compass_hist", { syms })
);

// =========================================================================
// Content / misc + escape hatch
// =========================================================================

t(
  "spotgamma_content_for_category",
  "Home content for a category (e.g. tooltips).",
  { category: z.string() },
  async ({ category }) => sgGet("/home/contentForCategory", { category })
);

t(
  "spotgamma_founders_notes",
  "Founders Notes listing, single note, or preview.",
  {
    page: z.number().int().positive().optional(),
    per_page: z.number().int().positive().optional(),
    month: z.number().int().min(1).max(12).optional(),
    year: z.number().int().optional(),
    id: z.number().int().optional().describe("Fetch a single note by id."),
    preview_key: z.string().optional().describe("Preview key."),
  },
  async ({ page, per_page, month, year, id, preview_key }) => {
    if (preview_key) return sgGet("/foundersNotes/preview", { previewKey: preview_key });
    if (id !== undefined) return sgGet("/foundersNotes/id", { id });
    return sgGet("/foundersNotes", { page, perPage: per_page, month, year });
  }
);

t(
  "spotgamma_raw_get",
  "Escape hatch: GET any SpotGamma API path from the endpoint catalog with " +
    "arbitrary query params — including account endpoints (v1/me/*, gated) and " +
    "misc endpoints (v2/occ, v1/allReviews, zendesk_article, ...).",
  {
    path: z
      .string()
      .describe("API path, e.g. /v1/me/user or /v2/occ. Must start with '/'."),
    params: extraParams,
    auth: z
      .boolean()
      .optional()
      .describe("Attach Bearer SPOTGAMMA_SG_TOKEN (required for v1/me/* and v4/*)."),
  },
  async ({ path, params, auth }) => {
    if (!path.startsWith("/")) throw new Error("path must start with '/'");
    return sgGet(path, params ?? {}, { auth: !!auth });
  }
);

// ---------------------------------------------------------------------------

const transport = new StdioServerTransport();
await server.connect(transport);
console.error(
  `spotgamma-mcp running on stdio. Bearer token: ${SG_TOKEN ? "set" : "NOT set (gated endpoints unavailable; use_free variants still work)"}.`
);
