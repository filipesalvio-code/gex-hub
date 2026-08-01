# Design: gex-poller — automatic MCP extraction → timeseries.db

Date: 2026-08-01
Status: approved (design)

## Goal

Automatically poll the core MenthorQ + SpotGamma MCP tools on a schedule and
store normalized time series in a new unified sqlite database, with minimal
observability.

## Architecture

A single Python package `poller/` that:

1. Spawns both MCP servers over stdio JSON-RPC (client pattern reused from
   `mcp/test_mcp.py`).
2. Calls the core tool set for SPX/SPY/QQQ + NVDA/TSLA/AAPL.
3. Normalizes responses into typed sqlite tables in `timeseries.db`.
4. Writes audit rows, logs, exits. Stateless between runs — all state in DB.

## Capture set

- MenthorQ: `gamma_levels`, `dealer_positioning`, `put_call_ratio`,
  `metrics_intraday`, `market_status`
- SpotGamma: `key_levels`, `compass`, `equity_put_call_ratio`, `zero_dte`,
  `most_recent_market_open`

## Schema (timeseries.db)

- Typed table per data family: `gamma_levels`, `dealer_positioning`,
  `key_levels`, `put_call_ratio`, `compass` — known fields as columns plus
  `payload TEXT` (raw JSON), `captured_at`, `source`, `ticker`.
- `scrape_runs` audit table: run id, started/finished, tool, http_status,
  rows written, error.
- `INSERT OR IGNORE` + unique constraint on `(tool, ticker, source_timestamp)`
  for idempotent re-runs.

## Scheduling

`~/Library/LaunchAgents/com.gexhub.poller.plist` with `StartInterval` 900s.
The script self-gates: exits immediately outside 13:30–20:00 UTC Mon–Fri or
when `menthorq_market_status` reports closed (holiday-aware for free).

## Error handling

Fail-closed: bridge daemon unreachable or token expired → log to
`scrape_runs`, exit non-zero; LaunchAgent retries next interval. One
transaction per tool call — no partial-run commits.

## Observability (minimal)

- Structured JSON-lines log per run in `logs/poller.jsonl` (timestamp, tools,
  rows, duration, errors); size-based rotation at 10 MB.
- Status CLI `python3 poller/status.py`: last run, 24h success rate,
  per-tool freshness, last 5 errors (reads `scrape_runs`).
- macOS notification (`osascript`) after 3 consecutive failed runs. No
  external services.

## Quality & review

- Coverage: 100% unit (normalization, schema, idempotency, market-hours
  gate, observability) · 80% integration (poller ↔ fake stdio MCP, real
  sqlite, plist validation) · 40% e2e (live `--once` cycle against real
  servers).
- CodeRabbit review after every 3 completed tasks; fixes applied before
  continuing.

## Testing

- Offline pytest: fake stdio MCP server with canned payloads → assert schema
  writes and idempotency.
- Live smoke: `python3 poller/poll.py --once` runs a single cycle on demand.
