# Architecture

## Context and goals

The owner holds paid accounts on two options-positioning analytics platforms —
**MenthorQ** (Premium) and **SpotGamma** (Alpha). Both are web dashboards with
undocumented internal APIs. This workspace exists to:

1. **Capture** the data from those accounts (reverse-engineered REST APIs,
   browser-DOM scraping, binary payload decoding).
2. **Archive** it locally (SQLite databases + parquet extracts) so history
   accumulates beyond what the platforms expose.
3. **Serve** it to AI assistants (Kimi Work, any MCP client) as first-class
   tools, so questions like "where is today's SPX call wall" are one call away.

Non-goals: redistribution of data, unattended trading, bypassing paywalls.
All access uses the owner's own live sessions; no passwords are stored.

## High-level design

```
                    ┌──────────────────────────────────────────────┐
                    │                 Chrome (owner)                │
                    │  dashboard.menthorq.io · dashboard.spotgamma  │
                    └───────────────┬──────────────────────────────┘
                                    │  Kimi WebBridge daemon
                                    │  (http://127.0.0.1:10086) — tab control,
                                    │  JS evaluate, token capture
        ┌───────────────────────────┼───────────────────────────────┐
        ▼                           ▼                               ▼
┌───────────────┐         ┌──────────────────┐            ┌────────────────────┐
│ mcp/          │         │ spotgamma-mcp/   │            │ scrapers           │
│ menthorq_mcp  │         │ server.js        │            │ gex_scraper.py     │
│ 24 tools,     │         │ 45 tools,        │            │ gex_binary.py      │
│ Python, stdio │         │ Node, stdio      │            │ scrape_daily.py    │
└───────┬───────┘         └────────┬─────────┘            │ scraper/mq_* (20u) │
        │                          │                      └─────────┬──────────┘
        ▼                          ▼                                ▼
 gateway.menthorq.io      api.spotgamma.com                menthorq.db (2.2 MB)
 (Cognito bearer)         (+ api.stream.spotgamma.com)     spotgamma.db (768 KB)
 (static app JWT + sgToken)                                gex_data.db (80 MB)
        │                          │                        data/*.parquet
        └──────────────┬───────────┘
                       ▼
        Kimi MCP registry — mcp.json
        protected by LaunchAgent watcher + mcp/mcp_guard.py
        SpotGamma token refreshed daily 09:17 by
        com.spotgamma.tokenrefresh → spotgamma-mcp/token_refresh.py
```

## Components

| Component | Path | Role |
|---|---|---|
| MenthorQ MCP server | `mcp/menthorq_mcp.py` | Zero-dependency Python stdio MCP server; 24 tools over `gateway.menthorq.io`; token pulled live from the browser per call (5-min in-memory cache) |
| Registration guard | `mcp/mcp_guard.py` + LaunchAgent `com.menthorq.mcpguard` | Re-adds the `menthorq` and `spotgamma` entries to Kimi's `mcp.json` whenever the file changes (MERGE-only, atomic write, mode 600) |
| SpotGamma MCP server | `spotgamma-mcp/server.js` | Node stdio MCP server (MCP SDK + zod); 45 tools over `api.spotgamma.com`; static app token + optional `SPOTGAMMA_SG_TOKEN` bearer |
| SpotGamma token refresh | `spotgamma-mcp/token_refresh.py` + LaunchAgent `com.spotgamma.tokenrefresh` | Daily 09:17: captures `localStorage["sgToken"]` from Chrome via WebBridge, merges into `mcp.json` env |
| GEX scraper | `gex_scraper.py` | Stdlib-only scheduled scraper: `home/keyLevels` → `gex_data.db.key_levels`, `v4/equities` → `equities_gex` (~10k symbols); self-refreshes its token via WebBridge on 401/403 |
| Binary decoders | `gex_binary.py` (now in `attic/`) | Decodes SpotGamma's MessagePack/Parquet payloads (OI matrix, greeks, IV stats, intraday strike bars) → `data/*.parquet` |
| MenthorQ scrape campaign | `scraper/mq_api.py`, `mq_db.py`, `mq_work_units.json`, `mq_agent_brief.md` | 20-unit parallel-agent full-platform archive → `menthorq.db` |
| SpotGamma scrape campaign | `scraper/db_writer.py`, `work_units.json`, `agent_brief.md`, `scrape_daily.py` (now in `attic/`) | 20-unit DOM-scrape of the dashboard → `spotgamma.db` |
| Analysis outputs | `plot_spx_gamma.py`, `positioning_artifact.py` | Gamma-curve charts and the positioning-dashboard artifact, built offline from the local archive |

## Key decisions and trade-offs

1. **Live-session tokens instead of stored credentials.**
   No passwords anywhere. MenthorQ tokens are read per call from the open
   browser tab; the SpotGamma JWT (~3-day life) is captured daily into
   `mcp.json` env; `gex_scraper.py` resolves it from `$SG_TOKEN` or live
   WebBridge capture (never written to disk).
   *Trade-off:* everything depends on the owner being logged in somewhere —
   accepted deliberately, since the account is the owner's.

2. **MCP servers over custom integrations.**
   Both platforms are exposed as stdio MCP servers, so any MCP-capable
   assistant gets the tools without bespoke glue. *Trade-off:* Kimi reads
   `mcp.json` at session start, so registration needs a guard (below) and new
   sessions to pick up changes.

3. **Self-healing registration (`mcp_guard.py` + watcher).**
   `mcp.json` is shared state and has been wiped twice by other tools. Rather
   than defending it, a LaunchAgent watches the file and the guard merges our
   entries back in seconds (preserving the SpotGamma env token). MERGE-only,
   idempotent, atomic — the same courtesy is expected from every writer.

4. **Archive raw, parse late.**
   Scrape campaigns store verbatim JSON (`raw_responses`, `raw_snapshots`)
   with run bookkeeping; curated columns are layered on top (`tickers`,
   `key_levels`, `equities_gex`). *Trade-off:* larger DBs and display-string
   parsing (`"3.15B"`), but nothing is ever lost and re-derivation is free.

5. **Stdlib-only for anything scheduled.**
   `gex_scraper.py`, `mcp_guard.py`, `token_refresh.py`, `menthorq_mcp.py` use
   only the Python standard library so they run under the Kimi managed runtime
   and survive environment churn. Heavier deps (msgpack, duckdb, pandas,
   matplotlib) are confined to interactive tools (`attic/gex_binary.py`,
   `plot_spx_gamma.py`, `positioning_artifact.py`).

6. **WebBridge as the browser bridge — with origin guards.**
   All browser automation goes through the local WebBridge daemon. Because its
   `evaluate` targets the last `navigate`d tab (not `find_tab` selections),
   every token probe checks `location.href` first and falls back to opening a
   fresh tab (`wrong_tab` state), never evaluating blindly on a random tab.

7. **Generated docs from live data.**
   `mcp/MCP_DOCS.md` and `spotgamma-mcp/DOCUMENTATION.md` are generated
   (`mcp/gen_docs.py`, `examples-runner.js` + `generate-docs.js`) from real
   archived/live responses, with personal data redacted. Docs drift is fixed
   by regenerating, not hand-editing.

## Data flow

**MenthorQ (live query path):** assistant → `menthorq_*` tool → `get_token()`
(env `MENTHORQ_TOKEN`, else WebBridge `/api/auth/session` from the dashboard
tab, cached 5 min) → `gateway.menthorq.io/<service>/api/web/v1/...` →
`{"http_status", "data"}` back to the assistant. Nothing is persisted.

**MenthorQ (archive path):** 20 agents, one work unit each → `mq_api.get()`
(0.4 s spacing, 429/5xx backoff) → `mq_db.save_response()` → `menthorq.db`
(`scrape_runs`, `raw_responses`, `api_endpoints`, `tickers`).

**SpotGamma (live query path):** assistant → `spotgamma_*` tool → static app
headers (+ `Authorization: Bearer $SPOTGAMMA_SG_TOKEN` when set; `use_free`
variants otherwise) → `api.spotgamma.com` → JSON (truncated at 200 KB).

**SpotGamma (archive path):** `gex_scraper.py` (key levels + equities GEX,
upserted by `(sym, trade_date)`) and `attic/gex_binary.py archive_oi` (per-actor OI
matrix, one parquet per US-Eastern calendar day in `data/oi/`). A separate
20-agent DOM campaign (`spotgamma.db`) captured the dashboard widgets,
including SVG-digitized chart series.

**Analysis:** `plot_spx_gamma.py` and `positioning_artifact.py` read only the
local archive — no network.

## Integration points

| External system | How we connect | Failure mode |
|---|---|---|
| Kimi WebBridge (`127.0.0.1:10086`) | HTTP `POST /command` (`navigate`, `evaluate`, `list_tabs`, `find_tab`) | daemon down / Chrome closed → token capture fails; calls return a clear "log in again" error |
| `gateway.menthorq.io` | HTTPS GET, Cognito `accessToken` bearer | session expiry → 4xx; retry after re-login |
| `api.spotgamma.com` / `api.stream.spotgamma.com` | HTTPS GET, static JWT + `sgToken` bearer | token expiry → 403; daily refresh or `gex_scraper.py` self-heal |
| Kimi `mcp.json` | MERGE-only writes, atomic rename, mode 600 | other writers wipe it → watcher + guard re-add our entries |
| macOS LaunchAgents (user-level) | `com.menthorq.mcpguard` (watch), `com.spotgamma.tokenrefresh` (daily 09:17) | both are reversible: `launchctl unload` + delete plist |
