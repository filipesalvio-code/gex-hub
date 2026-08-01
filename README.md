# GEX Scrapping — Options-Positioning Data Hub

📖 Full documentation: [docs/](docs/README.md) — architecture, API reference, runbook, onboarding, contributing.

A local-first workspace for capturing, archiving and querying **options
positioning data** from the owner's own premium accounts, and for serving that
data to AI assistants through MCP servers.

Two data platforms are integrated:

| Platform | Account | Integration | Status (2026-07-25) |
|---|---|---|---|
| **MenthorQ** (`dashboard.menthorq.io`) | Premium | MCP server, 24 tools · live API via browser-session token | ✅ active, self-healing |
| **SpotGamma** (`dashboard.spotgamma.com`) | Alpha | MCP server, 45 tools · REST scrapers · token auto-refresh | ✅ active (public tier until next daily token capture) |

No passwords are stored anywhere. All access runs on live-session tokens
captured from the owner's own Chrome via the Kimi WebBridge daemon
(`http://127.0.0.1:10086`).

## Big picture

```
                    ┌──────────────────────────────────────────────┐
                    │                 Chrome (owner)                │
                    │  dashboard.menthorq.io · dashboard.spotgamma  │
                    └───────────────┬──────────────────────────────┘
                                    │  WebBridge (token capture, page control)
        ┌───────────────────────────┼───────────────────────────────┐
        ▼                           ▼                               ▼
┌───────────────┐         ┌─────────────────┐             ┌──────────────────┐
│ menthorq_mcp  │         │ spotgamma-mcp   │             │ scrapers         │
│ 24 tools      │         │ 45 tools        │             │ mq_* · gex_*     │
│ (python,stdio)│         │ (node, stdio)   │             │                  │
└───────┬───────┘         └────────┬────────┘             └────────┬─────────┘
        │                          │                               │
        ▼                          ▼                               ▼
 gateway.menthorq.io      dashboard.spotgamma.com          menthorq.db · spotgamma.db
        │                          │                               gex_data.db · data/
        └──────────────┬───────────┘
                       ▼
              Kimi MCP registry
        `kimi-code/home/mcp.json`
        protected by LaunchAgent watcher + guard
```

## Directory map

### Core systems
| Path | What it is |
|---|---|
| `mcp/` | **MenthorQ MCP server** (`menthorq_mcp.py`), tests, doc generator, `mcp_guard.py` (registration self-healer). Docs: `mcp/README.md`, full tool reference `mcp/MCP_DOCS.md` |
| `spotgamma-mcp/` | **SpotGamma MCP server** (`server.js`, 45 tools) + `token_refresh.py` (unattended sgToken capture). Docs: `spotgamma-mcp/README.md`, `spotgamma-mcp/DOCUMENTATION.md` |
| `scraper/` | MenthorQ scraping campaign tooling (`mq_api.py`, `mq_db.py`, `mq_work_units.json`, `mq_agent_brief.md`) + legacy one-off extraction scripts — see `scraper/README.md` |
| `gex_scraper.py` | SpotGamma GEX scraper → `gex_data.db` (key levels + ~10k-symbol GEX); auto-refreshes `sg_token.txt` via WebBridge |
| `positioning_artifact.py` | Builds positioning-dashboard artifact from `gex_data.db` + `data/oi/*.parquet` (duckdb, offline) |
| `plot_spx_gamma.py` | SPX gamma-curve plotting → `spx_gamma_curve.png` |

### Databases
| File | Contents |
|---|---|
| `menthorq.db` (3.1 MB) | MenthorQ archive: 230 verbatim API responses, 1,256-instrument `tickers`, 34-endpoint `api_endpoints` catalog, `scrape_runs` |
| `spotgamma.db` (768 KB) | SpotGamma raw snapshots + scrape runs (table `raw_snapshots`, `scrape_runs`) — see `SPOTGAMMA_DB_DOCUMENTATION.md` |
| `gex_data.db` (80 MB) | SpotGamma time series: `key_levels` (SPX walls/zero-gamma/gamma curve), `equities_gex` (~10k symbols), `scrape_runs` |
| `data/` | Parquet/arrow extracts (OI matrices, greeks, strike bars), sitemap inventories |

### Automation (macOS LaunchAgents — user-level, reversible)
| Agent | Job |
|---|---|
| `com.menthorq.mcpguard` | Watches `mcp.json`; re-runs `mcp/mcp_guard.py` on any change → re-adds `menthorq` **and** `spotgamma` entries in seconds (preserves tokens). Verified live |
| `com.spotgamma.tokenrefresh` | Daily 09:17 → `spotgamma-mcp/token_refresh.py`: captures `sgToken` from Chrome, merges into `mcp.json`. Logs to `logs/spotgamma_token_refresh.log` |

Remove: `launchctl unload ~/Library/LaunchAgents/<name>.plist` + delete the plist.

### Presentations (kimi-slides `.pptd`; export PPTX only via the editor)
| Path | Deck |
|---|---|
| `presentation/menthorq_trader/` | 12-page MenthorQ×Kimi deck for options traders (dark terminal style, real SPX data 2026-07-24) |
| `presentation/spotgamma_trader_deck.pptd` + `presentation/pages/` | 12-page SpotGamma market-record deck |
| `SpotGamma-for-Traders/` | 10-page SpotGamma intro deck |

### Reference & research
`API_ENDPOINTS.md` (MenthorQ API catalog) · `spotgamma-api-endpoints.md` /
`spotgamma-api-docs.md` (SpotGamma catalogs) · `QUIN_dossier.md`,
`QUIN_AI_Distillation.md`, `dossier/`, `quin_research/` (QUIN AI research) ·
`menthorq-legal-corporate-report.md`, `terms-of-use.*`, `cookie-policy.*`
(legal) · `*.html` (archived platform pages) · `probes.json`, `probe_api.py`
(endpoint probes)

> Many root-level `*.py`/`*.js` and most `scraper/run_*`/`extract_*` files are
> **historical one-off campaign scripts** — kept for provenance, not maintained.

## Runbook

**Test the MCP servers**
```bash
python3 mcp/test_mcp.py      # MenthorQ smoke (5 calls)
python3 mcp/test_all.py      # MenthorQ exhaustive (all 24 tools, via mcp.json config)
```
SpotGamma: boot check = run `server.js` and speak JSON-RPC (see `spotgamma-mcp/README.md`).

**Check registration health**
```bash
python3 mcp/mcp_guard.py --status
```

**Refresh the SpotGamma token manually** (normally automatic, daily 09:17)
```bash
python3 spotgamma-mcp/token_refresh.py   # needs Chrome open + SpotGamma login
```

**Regenerate the MenthorQ MCP docs** (after editing the server)
```bash
python3 mcp/gen_docs.py
```

**Re-run the MenthorQ scrape** — see `scraper/README.md` (campaign model:
20 work units × `mq_api.py`/`mq_db.py`).

**Edit a presentation** — open the `.pptd` in the Kimi slides editor; export
PPTX **only** via the editor's export button (never CLI). Validate after edits:
`kimi-slides check <deck-dir>` (each deck must be alone in its directory).

## Hard-won conventions (read before automating here)

1. **`mcp.json` is shared — MERGE, never replace.** Multiple sessions write it;
   it has been wiped twice. The watcher+guard heal our entries, but other tools
   count on the same courtesy from us.
2. **WebBridge `evaluate` targets the last `navigate`d tab**, not `find_tab`
   selections. All tooling here origin-guards probes and falls back to opening
   a fresh tab (see `mcp/menthorq_mcp.py::_fetch_token_via_bridge`).
3. **kimi-slides YAML**: quote any text containing `:` or `,` inside flow maps
   (a bare comma silently truncates text); dark decks need explicit chart
   `fill`; one `.pptd` per directory.
4. **Tokens never in the repo as a rule.** `sg_token.txt` is a legacy exception
   used by `gex_scraper.py`; new code uses env vars or live capture only.
5. Everything is local-first: databases, logs, decks and docs live in this
   workspace; nothing is uploaded.

## Status snapshot — 2026-07-25

- MenthorQ: scrape archived (20-unit campaign), MCP registered + guard-protected,
  docs generated, trader deck delivered. All 24 tools pass (25/25).
- SpotGamma: MCP registered (public tier until next token capture), token
  refresh fully automated daily, registration guard-protected.
- Project memory: vault entities `menthorq-mcp.md` and `spotgamma-mcp.md`
  (Kimi agent memory) are kept current after each work session.
