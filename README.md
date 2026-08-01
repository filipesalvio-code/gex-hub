# gex-hub

Local-first hub for options positioning / gamma-exposure (GEX) data.
MCP servers that let AI assistants query MenthorQ & SpotGamma with **your own** session — plus scrapers, a time-series store, and charting.

## Quickstart

Requires Python 3.11+ (Node 18+ for the SpotGamma MCP server).

```bash
pip install -e ".[dev]"
python3 mcp/test_mcp.py        # needs your Chrome session (see docs/ONBOARDING.md)
```

## What you get

- `menthorq` MCP server — 24 tools (positioning, gamma levels, …)
- `spotgamma` MCP server — 45 tools + automatic token refresh
- GEX time series → sqlite/parquet, SPX gamma-curve plots

> Unofficial, personal-use tooling. Requires your own paid MenthorQ/SpotGamma
> accounts. No data is included or redistributed.

## Documentation

- [docs/](docs/README.md) — architecture, API reference, runbook, onboarding, contributing
- [LICENSE](LICENSE) — proprietary, source-available (all rights reserved)
- [SECURITY.md](SECURITY.md) — token policy, data policy, how to report issues

---

## For maintainers

> Everything below is the original operator documentation. Paths marked
> *(local-only)* are gitignored and absent from the public repo; they exist
> only in the owner's full workspace.

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
(`http://127.0.0.1:10086`) or supplied via environment variables.

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

## Setup

Requires Python 3.11+.

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

This installs the importable modules `gex_scraper`, `positioning_artifact` and
`plot_spx_gamma` plus runtime deps (`requests`, `pandas`, `duckdb`,
`matplotlib`, `msgpack`). The `mcp/menthorq_mcp.py` server is stdlib-only; the
SpotGamma MCP server is Node (`spotgamma-mcp/`, see its README). Copy
`.env.example` to `.env` for optional token overrides.

## Directory map

### Core systems
| Path | What it is |
|---|---|
| `mcp/` | **MenthorQ MCP server** (`menthorq_mcp.py`), tests, doc generator, `mcp_guard.py` (registration self-healer). Docs: `mcp/README.md`, full tool reference `mcp/MCP_DOCS.md` |
| `spotgamma-mcp/` | **SpotGamma MCP server** (`server.js`, 45 tools) + `token_refresh.py` (unattended sgToken capture). Docs: `spotgamma-mcp/README.md`, `spotgamma-mcp/DOCUMENTATION.md` |
| `scraper/` | MenthorQ scraping campaign tooling (`mq_api.py`, `mq_db.py`, `mq_work_units.json`, `mq_agent_brief.md`) — see `scraper/README.md` |
| `gex_scraper.py` | SpotGamma GEX scraper → `gex_data.db` (key levels + ~10k-symbol GEX); token from `SG_TOKEN` env or live WebBridge capture (never written to disk) |
| `positioning_artifact.py` | Builds positioning-dashboard artifact from `gex_data.db` + `data/oi/*.parquet` (duckdb, offline) |
| `plot_spx_gamma.py` | SPX gamma-curve plotting → `spx_gamma_curve.png` |
| `attic/` | Historical one-off campaign scripts (`probe_api.py`, `rescrape_eh_hiro.py`, `scrape_daily.py`, `gex_binary.py`, `update_deck.py`); kept for provenance, not maintained — see `attic/README.md` |
| `tests/` | Offline pytest suite (mocked token, in-memory DB); runs in CI |
| `docs/` | Long-form documentation index — see `docs/README.md` |

### Databases *(local-only — gitignored by design, see SECURITY.md)*
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

**Single-machine components.** `mcp/mcp_guard.py`, `spotgamma-mcp/token_refresh.py`
and the LaunchAgents above are macOS/user-specific automation for the owner's
machine (they manage the owner's `mcp.json` and browser session). They are not
part of the portable tooling and are not needed to use the MCP servers or
scrapers on another machine.

### Presentations *(local-only — not in the public repo)*
| Path | Deck |
|---|---|
| `presentation/menthorq_trader/` | 12-page MenthorQ×Kimi deck for options traders (dark terminal style, real SPX data 2026-07-24) |
| `presentation/spotgamma_trader_deck.pptd` + `presentation/pages/` | 12-page SpotGamma market-record deck |
| `SpotGamma-for-Traders/` | 10-page SpotGamma intro deck |

### Reference & research
`API_ENDPOINTS.md` (MenthorQ API catalog — unofficial, personal use) · `spotgamma-api-endpoints.md` /
`spotgamma-api-docs.md` (SpotGamma catalogs — unofficial, personal use) · *(local-only)* `QUIN_dossier.md`,
`QUIN_AI_Distillation.md`, `dossier/`, `quin_research/` (QUIN AI research) ·
`menthorq-legal-corporate-report.md`, `terms-of-use.*`, `cookie-policy.*`
(legal) · `*.html` (archived platform pages) · `probes.json`
(endpoint probe results)

## Runbook

**Test the MCP servers**
```bash
python3 mcp/test_mcp.py      # MenthorQ smoke (5 calls) — needs your Chrome session
python3 mcp/test_all.py      # MenthorQ exhaustive (all 24 tools, via mcp.json config)
```
SpotGamma: boot check = run `server.js` and speak JSON-RPC (see `spotgamma-mcp/README.md`).

**Run the offline tests**
```bash
python3 -m pytest tests/     # no network, no token, no Chrome needed
```

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
4. **Tokens never in the repo or on disk.** Token resolution is `$SG_TOKEN` /
   `$MENTHORQ_TOKEN` env vars or live WebBridge capture only — nothing is
   written to a token file.
5. Everything is local-first: databases, logs, decks and docs live in this
   workspace; nothing is uploaded.

## Status snapshot — 2026-07-25

- MenthorQ: scrape archived (20-unit campaign), MCP registered + guard-protected,
  docs generated, trader deck delivered. All 24 tools pass (25/25).
- SpotGamma: MCP registered (public tier until next token capture), token
  refresh fully automated daily, registration guard-protected.
- Project memory: vault entities `menthorq-mcp.md` and `spotgamma-mcp.md`
  (Kimi agent memory) are kept current after each work session.
