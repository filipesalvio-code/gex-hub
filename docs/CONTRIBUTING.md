# Contributing Guide

Rules for changing anything in this workspace. They exist because specific
things already went wrong at least once.

## The five hard rules

1. **`mcp.json` is shared — MERGE, never replace.** Read the file, change
   your keys, write back atomically (`tmp` + `os.replace`), keep mode 600.
   Other tools count on the same courtesy. Use `mcp/mcp_guard.py`'s pattern.
2. **No passwords, no tokens in code or new files.** The only token on disk
   is `sg_token.txt` (legacy, used by `gex_scraper.py`; auto-refreshed). New
   code takes tokens from env vars (`MENTHORQ_TOKEN`, `SG_TOKEN`,
   `SPOTGAMMA_SG_TOKEN`) or captures them live via WebBridge — and never
   writes them to the DB, logs, or reports.
3. **Archive raw, parse late.** Scrape code stores verbatim payloads via the
   helper modules (`scraper/mq_db.py`, `scraper/db_writer.py`) — never raw
   SQL, never UPDATE/DELETE other runs' rows. Curated tables are rebuilt
   from raw, not patched.
4. **Stdlib-only for anything scheduled or registration-critical.**
   `gex_scraper.py`, `mcp_guard.py`, `token_refresh.py`, `menthorq_mcp.py`
   must keep running under any Python 3.8+. Heavier deps belong in
   interactive tools only.
5. **Local-first.** Databases, logs, decks, and docs live in this workspace.
   Don't upload account data anywhere.

## Where things live (and what not to touch)

- `mcp/`, `spotgamma-mcp/`, `gex_scraper.py`, `gex_binary.py`,
  `positioning_artifact.py`, `plot_spx_gamma.py`, `scraper/mq_*.py` —
  **maintained code**. Changes welcome; follow the patterns above.
- `scraper/run_*.py`, `scraper/extract_*.js`, `scraper/probe_*.js`,
  `scraper/sg1*_*.py`, `scraper/agent16_*`, `update_deck.py`,
  `scrape_daily.py`, `rescrape_eh_hiro.py`, root `*.html`/`*.txt` archives —
  **historical one-off artifacts, kept for provenance.** Treat as read-only
  reference; write new scripts instead of editing them.
- `probes.json`, `data/`, `*.db` — **data**. Regenerate via the tools; don't
  hand-edit.
- Presentations: edit `.pptd` pages only through the kimi-slides editor;
  export PPTX only via the editor's export button; one `.pptd` per directory;
  `kimi-slides check <deck-dir>` after edits.

## Testing your change

```bash
python3 mcp/test_mcp.py                      # MenthorQ MCP smoke
python3 mcp/test_all.py                      # MenthorQ MCP, all 24 tools
cd spotgamma-mcp && node test-client.js      # SpotGamma MCP boot + 2 calls
python3 gex_scraper.py --skip-equities       # scraper end-to-end
python3 mcp/mcp_guard.py --status            # registration health
```

## Documentation duties

- Changed a tool or endpoint? Regenerate the matching reference:
  `python3 mcp/gen_docs.py` or `node examples-runner.js && node generate-docs.js`.
- Changed how something works? Update the README nearest to it
  (`mcp/README.md`, `spotgamma-mcp/README.md`, `scraper/README.md`) and, if
  the map changed, [../README.md](../README.md) and [README.md](README.md).
- Link, don't duplicate: reference the subsystem docs instead of copying
  tables between files.
- After each work session, refresh the Kimi memory vault entities
  `menthorq-mcp.md` / `spotgamma-mcp.md`.

## Style

- Python: type hints where cheap, module docstring at the top explaining
  purpose + auth + CLI, `log = logging.getLogger(<name>)` for CLIs.
- Docstrings and READMEs in English; tables for inventories; show commands
  and expected output rather than describing them.
- Dates in docs are UTC ISO (`YYYY-MM-DD`); data timestamps are ISO-8601 UTC
  seconds (`datetime.now(timezone.utc).isoformat(timespec="seconds")`).
