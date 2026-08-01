// Smoke test: spawn the server over stdio, list tools, call public endpoints.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const transport = new StdioClientTransport({
  command: process.execPath,
  args: ["server.js"],
});

const client = new Client({ name: "spotgamma-mcp-test", version: "0.1.0" });
await client.connect(transport);

const { tools } = await client.listTools();
console.log(`TOOLS (${tools.length}):`);
for (const tool of tools) console.log(`  - ${tool.name}`);

async function call(name, args) {
  const res = await client.callTool({ name, arguments: args });
  const text = res.content?.[0]?.text ?? "";
  console.log(`\n=== ${name} ${JSON.stringify(args)} ===`);
  console.log(res.isError ? `ERROR: ${text}` : text.slice(0, 900));
}

// Public endpoints (verified live in the catalog).
await call("spotgamma_most_recent_market_open", {});
await call("spotgamma_key_levels", { include_gamma_curve: false });

await client.close();
console.log("\nSMOKE TEST DONE");
