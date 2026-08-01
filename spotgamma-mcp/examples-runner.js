// Calls every spotgamma tool with SPX-oriented args and captures the result
// (status + truncated sample) into examples-output.json for doc generation.
import { readFileSync, writeFileSync } from "node:fs";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const MCP_JSON =
  "/Users/filipesalvio/Library/Application Support/kimi-desktop/daimon-share/daimon/runtime/kimi-code/home/mcp.json";
const token = JSON.parse(readFileSync(MCP_JSON, "utf8")).mcpServers.spotgamma.env.SPOTGAMMA_SG_TOKEN;

const CALLS = [
  ["spotgamma_key_levels", { include_gamma_curve: true }],
  ["spotgamma_equities_gex", { syms_filter: ["SPX"] }],
  ["spotgamma_equities_by_syms", { syms: "SPX", date: "2026-07-24" }],
  ["spotgamma_historical_gex", { params: { sym: "SPX" } }],
  ["spotgamma_combo_levels", { sym: "SPX" }],
  ["spotgamma_home_all_data", {}],
  ["spotgamma_latest_greeks", { sym: "SPX" }],
  ["spotgamma_daily_greeks", { sym: "SPX", date: "2026-07-24" }],
  ["spotgamma_skew", {}],
  ["spotgamma_tilt", { sym: "SPX" }],
  ["spotgamma_risk_reversal", { sym: "SPX" }],
  ["spotgamma_rr", { sym: "SPX" }],
  ["spotgamma_iv_stats", { sym: "SPX" }],
  ["spotgamma_oi_intraday", { kind: "gamma", symbol: "SPX", date: "2026-07-24" }],
  ["spotgamma_oi", { sym: "SPX" }],
  ["spotgamma_oi_syms", {}],
  ["spotgamma_concentration", { syms: "SPX", group_by: "strike" }],
  ["spotgamma_synth_oi_equities", { date: "2026-07-24" }],
  ["spotgamma_synth_oi_chart_data", { params: { sym: "SPX" } }],
  ["spotgamma_synth_oi_historical", { params: { sym: "SPX" } }],
  ["spotgamma_synth_oi_last_update", {}],
  ["spotgamma_synth_oi_eh_symbols", {}],
  ["spotgamma_synth_oi_equity_scanners", {}],
  ["spotgamma_running_hiro", {}],
  ["spotgamma_hiro_history", { syms: "SPX", all: true, next_exp: true, retail: true }],
  ["spotgamma_latest_hiro", { syms: "SPX", all: true, limit: 10 }],
  ["spotgamma_prices", { syms: ["SPX", "SPY"] }],
  ["spotgamma_quote", { symbol: "SPX" }],
  ["spotgamma_series", { symbol: "SPX", interval: "1day", start_date: "2026-07-01", end_date: "2026-07-24", order: "asc" }],
  ["spotgamma_futures", { sym: "S&P ES=F" }],
  ["spotgamma_most_recent_market_open", {}],
  ["spotgamma_treasury_rates", { date: "2026-07-24" }],
  ["spotgamma_dividends", { params: { sym: "SPX" } }],
  ["spotgamma_zero_dte", { sym: "SPX" }],
  ["spotgamma_equity_put_call_ratio", {}],
  ["spotgamma_correlation_regime", { sym: "SPX" }],
  ["spotgamma_trending", { interval: 30 }],
  ["spotgamma_earnings", { start: "2026-07-24", end: "2026-07-31" }],
  ["spotgamma_economic_calendar", { from: "2026-07-20", to: "2026-07-26" }],
  ["spotgamma_equity_scanners", {}],
  ["spotgamma_compass", { syms: "SPX" }],
  ["spotgamma_compass_hist", { syms: "SPX" }],
  ["spotgamma_content_for_category", { category: "tooltips" }],
  ["spotgamma_founders_notes", { page: 1, per_page: 2 }],
  ["spotgamma_raw_get", { path: "/v1/me/user", auth: true }],
];

const transport = new StdioClientTransport({
  command: process.execPath,
  args: ["server.js"],
  env: { ...process.env, SPOTGAMMA_SG_TOKEN: token },
});
const client = new Client({ name: "doc-examples", version: "0.1.0" });
await client.connect(transport);

const out = {};
for (const [name, args] of CALLS) {
  try {
    const res = await client.callTool({ name, arguments: args });
    const text = res.content?.[0]?.text ?? "";
    out[name] = { args, error: !!res.isError, bytes: text.length, sample: text.slice(0, 1500) };
    console.log(`${res.isError ? "ERR " : "ok  "} ${name} (${text.length} chars)`);
  } catch (e) {
    out[name] = { args, error: true, bytes: 0, sample: `Error: ${e.message}` };
    console.log(`FAIL ${name}: ${e.message}`);
  }
}
await client.close();
writeFileSync("examples-output.json", JSON.stringify(out, null, 2));
console.log("\nSaved examples-output.json");
