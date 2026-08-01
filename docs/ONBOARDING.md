# Onboarding Guide

Welcome to the GEX Scrapping workspace — a local-first options-positioning
data hub covering two platforms (MenthorQ, SpotGamma), two MCP servers,
three databases, and a pile of research. This guide gets you productive.

## 1. Environment setup (≈10 minutes)

1. **Get the workspace**: `/Users/filipesalvio/gex-hub`.
   Everything lives here; nothing is uploaded anywhere.
2. **Python**: use the Kimi managed runtime (`python3` inside Kimi Work). All
   scheduled/critical scripts are stdlib-only; the analysis tools additionally
   use the runtime's bundled `pandas`/`matplotlib`/`duckdb`. For
   `gex_binary.py` you also need `msgpack` (`pip install msgpack` into a user
   env if missing).
3. **Node**: 18+ (developed on Node 24). One-time:
   ```bash
   cd spotgamma-mcp && npm install
   ```
4. **Browser access**: Chrome with the Kimi WebBridge extension, logged in to
   `dashboard.menthorq.io` and `dashboard.spotgamma.com` (owner's accounts).
   The WebBridge daemon must be listening on `http://127.0.0.1:10086`.
5. **Smoke test** (details in [RUNBOOK.md](RUNBOOK.md) §1):
   ```bash
   python3 mcp/mcp_guard.py --status
   python3 mcp/test_mcp.py
   cd spotgamma-mcp && node test-client.js
   ```

You do **not** need any password: auth is live-session tokens captured from
the browser. The only token file is `sg_token.txt` (legacy; auto-refreshed).

## 2. Key systems and how they connect

Read [ARCHITECTURE.md](ARCHITECTURE.md) for the full picture. The 60-second
version:

- **MenthorQ** data comes two ways: *live* through the `menthorq` MCP server
  (24 tools → `gateway.menthorq.io`, token read from your browser tab per
  call), and *archived* in `menthorq.db` (one full-platform campaign,
  insert-only `raw_responses` + `tickers` + `api_endpoints` catalog).
- **SpotGamma** data comes three ways: *live* through the `spotgamma` MCP
  server (45 tools → `api.spotgamma.com`), *time series* from
  `gex_scraper.py` into `gex_data.db` (+ `gex_binary.py` → `data/*.parquet`),
  and a one-shot DOM scrape of the dashboard in `spotgamma.db`.
- **Kimi registration** of both servers lives in the shared `mcp.json`,
  watched by a LaunchAgent that re-heals our entries (`mcp/mcp_guard.py`).
  The SpotGamma token is refreshed daily 09:17 by another LaunchAgent
  (`spotgamma-mcp/token_refresh.py`).
- **Presentations** (`presentation/`, `SpotGamma-for-Traders/`,
  `spotgamma_trader_deck/`) are kimi-slides `.pptd` decks built from the
  archived data.

Directory map with one-line descriptions: root [README.md](../README.md).

## 3. Common tasks with walkthroughs

### "Where is the SPX call wall right now?"

In a Kimi session (tools already registered):

```
spotgamma_key_levels { include_gamma_curve: false }     # SpotGamma
menthorq_gamma_levels { ticker: "SPX", frequency: "eod" } # MenthorQ
```

From the shell: `python3 gex_scraper.py --skip-equities` then query
`gex_data.db`:

```sql
SELECT trade_date, upx, callwallstrike, putwallstrike, zero_g_strike
FROM key_levels WHERE sym='SPX' ORDER BY trade_date DESC LIMIT 1;
```

### "Plot the gamma curve"

```bash
python3 plot_spx_gamma.py            # → spx_gamma_curve.png (offline, from gex_data.db)
python3 plot_spx_gamma.py --sym QQQ --window 800
```

### "Pull the full per-actor OI matrix"

```bash
python3 gex_binary.py oi SPX         # → data/oi_spx.parquet
# or the deduped daily archive:
python3 -c "import gex_binary; print(gex_binary.archive_oi('SPX'))"
```

### "Query the SpotGamma dashboard archive"

`spotgamma.db` holds 86 widget snapshots across 20 sections (Equity Hub,
HIRO, Tape, iVol, Scanners, …) with SQLite JSON1 queries. Start from the
cookbook in [../SPOTGAMMA_DB_DOCUMENTATION.md](../SPOTGAMMA_DB_DOCUMENTATION.md):

```sql
SELECT json_extract(payload_json, '$.spotgamma_levels.call_wall')
FROM raw_snapshots WHERE section='hiro-spx';
```

### "Add a new MenthorQ/SpotGamma tool"

MenthorQ: add a `_t(...)` entry in `mcp/menthorq_mcp.py` `TOOLS` + a branch
in `call_tool`, then `python3 mcp/test_all.py` and
`python3 mcp/gen_docs.py`. SpotGamma: add a `t(...)` registration in
`spotgamma-mcp/server.js`, then `node examples-runner.js &&
node generate-docs.js`. Endpoint paths come from the catalogs
([../API_ENDPOINTS.md](../API_ENDPOINTS.md),
[../spotgamma-api-endpoints.md](../spotgamma-api-endpoints.md)).

### "Re-run a scrape campaign"

Follow [RUNBOOK.md](RUNBOOK.md) §4–§5. Campaigns are multi-agent by design:
one work unit per agent, helpers-only DB writes, ≤5 concurrent.

## 4. Who to ask for what

| Area | Source of truth |
|---|---|
| MenthorQ MCP tools | [../mcp/MCP_DOCS.md](../mcp/MCP_DOCS.md) |
| SpotGamma MCP tools | [../spotgamma-mcp/DOCUMENTATION.md](../spotgamma-mcp/DOCUMENTATION.md) |
| MenthorQ endpoints | [../API_ENDPOINTS.md](../API_ENDPOINTS.md) + `menthorq.db.api_endpoints` |
| SpotGamma endpoints | [../spotgamma-api-docs.md](../spotgamma-api-docs.md) + `probes.json` |
| spotgamma.db contents | [../SPOTGAMMA_DB_DOCUMENTATION.md](../SPOTGAMMA_DB_DOCUMENTATION.md) |
| Scrape campaigns | [../scraper/README.md](../scraper/README.md) |
| Decks | [../presentation/README.md](../presentation/README.md) |
| Session-to-session state | Kimi memory vault entities `menthorq-mcp.md`, `spotgamma-mcp.md` |
| Operations / incidents | [RUNBOOK.md](RUNBOOK.md) — escalation path in §8 |
| QUIN AI background research | [../QUIN_AI_Distillation.md](../QUIN_AI_Distillation.md), [../dossier/](../dossier/) |

This is a single-owner project: the "team" is the owner plus Kimi agent
sessions. When in doubt, leave a note in the relevant README and in the
memory vault so the next session inherits it.
