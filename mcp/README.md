# MenthorQ MCP Server

Zero-dependency MCP server (stdio, Python 3.8+) exposing the MenthorQ data
platform APIs discovered from `dashboard.menthorq.io` (see `../API_ENDPOINTS.md`).

- Server: `menthorq_mcp.py` — newline-delimited JSON-RPC 2.0 on stdio,
  MCP protocol version `2024-11-05`, 24 tools.
- Test:   `test_mcp.py` — spawns the server and smoke-tests it
  (`python3 mcp/test_mcp.py`).

## Authentication

The gateway (`gateway.menthorq.io`) needs a Cognito `accessToken`. Resolved per
call, in this order:

1. **`MENTHORQ_TOKEN` env var** — paste a token manually (highest priority).
2. **Kimi WebBridge** (default) — the server pulls a fresh token from your
   open, logged-in `dashboard.menthorq.io` Chrome tab via the local WebBridge
   daemon. It auto-opens a dashboard tab if none is usable. If your MenthorQ
   session expires, calls fail with a clear "log in again" message — just
   revisit `https://dashboard.menthorq.io` in Chrome.

Optional env overrides: `MENTHORQ_BRIDGE_URL` (default
`http://127.0.0.1:10086/command`), `MENTHORQ_BRIDGE_SESSION` (default
`menthorq-scrape`). Tokens are cached in-memory for 5 minutes and never
written to disk.

## Client configuration

**Already registered in Kimi** (2026-07-25) at
`…/daimon/runtime/kimi-code/home/mcp.json` (backup of the original in
`mcp.json.backup`). New Kimi sessions pick the tools up automatically as
`mcp__…menthorq…` tools; a running session must be restarted to see them.

Standard `mcpServers` entry (what was registered):

```json
{
  "mcpServers": {
    "menthorq": {
      "command": "/Users/filipesalvio/Library/Application Support/kimi-desktop/daimon-share/daimon/runtime/python/.venv/bin/python3",
      "args": ["/Users/filipesalvio/gex-hub/mcp/menthorq_mcp.py"],
      "env": {
        "MENTHORQ_BRIDGE_SESSION": "menthorq-scrape"
      }
    }
  }
}
```

## Testing

- `python3 mcp/test_mcp.py` — quick smoke test (5 representative calls).
- `python3 mcp/test_all.py` — launches the server via the exact command
  registered in Kimi's `mcp.json` and calls **every tool**: last run 25/25
  passed (all HTTP 200).

## Tools (24)

| Group | Tools |
|---|---|
| Universe & prices | `menthorq_tickers`, `menthorq_prices`, `menthorq_market_status` |
| Gamma | `menthorq_gamma_levels`, `menthorq_gamma_insights`, `menthorq_gamma_insights_expirations` |
| Metrics | `menthorq_metrics_eod` (option/momentum/volatility/seasonality), `menthorq_metrics_intraday` (IV & skew fields only) |
| Options | `menthorq_options_matrix`, `menthorq_put_call_ratio`, `menthorq_dealer_positioning` |
| Volatility | `menthorq_volatility_insights` (skew, IV vs 50d, VRP) |
| Charts | `menthorq_candles` (intervals `1m..45m, 1h..4h, 1D, 1W, 1M`; ms-epoch `from_ms`/`to_ms`), `menthorq_tradingview` |
| Screeners | `menthorq_screener`, `menthorq_screener_columns`, `menthorq_screener_templates` |
| News/events | `menthorq_qbot_assets`, `menthorq_events`, `menthorq_company_news` |
| Account | `menthorq_user_me`, `menthorq_watchlists`, `menthorq_chats`, `menthorq_chat_templates` |

Every tool returns `{"http_status": <int>, "data": <json>}` as text content;
non-2xx statuses set `isError: true`.

## Notes

- `market-status` supports NYSE/NASDAQ only (upstream limitation).
- `put-call-ratio` returns the latest snapshot, not a series.
- Futures tickers use provider format (`DATABENTO#ES`); browse
  `menthorq_tickers` for exact symbols.
- The historical scrape archive (~1.5 MB from 2026-07-25) lives in
  `../menthorq.db` — this server talks to the live API, not the archive.
