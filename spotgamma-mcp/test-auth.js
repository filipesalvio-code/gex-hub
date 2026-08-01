// Gated-endpoint test: reads SPOTGAMMA_SG_TOKEN from Kimi's mcp.json env
// (single source of truth for the token) and calls auth-gated tools.
import { readFileSync } from "node:fs";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const MCP_JSON =
  "/Users/filipesalvio/Library/Application Support/kimi-desktop/daimon-share/daimon/runtime/kimi-code/home/mcp.json";
const cfg = JSON.parse(readFileSync(MCP_JSON, "utf8"));
const token = cfg.mcpServers?.spotgamma?.env?.SPOTGAMMA_SG_TOKEN;
if (!token) throw new Error("SPOTGAMMA_SG_TOKEN not found in mcp.json env");

const transport = new StdioClientTransport({
  command: process.execPath,
  args: ["server.js"],
  env: { ...process.env, SPOTGAMMA_SG_TOKEN: token },
});
const client = new Client({ name: "spotgamma-auth-test", version: "0.1.0" });
await client.connect(transport);

async function call(name, args) {
  const res = await client.callTool({ name, arguments: args });
  const text = res.content?.[0]?.text ?? "";
  console.log(`=== ${name} ===`);
  console.log(res.isError ? `ERROR: ${text.slice(0, 500)}` : text.slice(0, 700));
  console.log();
}

await call("spotgamma_equities_gex", { syms_filter: ["SPX", "SPY", "QQQ", "NVDA"] });
await call("spotgamma_running_hiro", {});
await call("spotgamma_equities_by_syms", { syms: "SPX", date: "2026-07-24" });

await client.close();
console.log("AUTH TEST DONE");
