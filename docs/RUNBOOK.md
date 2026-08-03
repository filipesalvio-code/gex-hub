# Runbook

Operational procedures for this workspace. Everything is local-first and
user-level; nothing here requires sudo.

## When to use this runbook

- An MCP tool fails or returns auth errors.
- `mcp.json` lost the `menthorq`/`spotgamma` entries.
- You want to re-run a scrape campaign, refresh a token, or regenerate docs.
- Something in this workspace misbehaves and you need to roll back.

## Prerequisites and access needed

- macOS user session with **Chrome open** and logged in to
  `dashboard.menthorq.io` and/or `dashboard.spotgamma.com` (only needed for
  the platform you're operating on).
- **Kimi WebBridge** daemon running (`http://127.0.0.1:10086`) with the
  browser extension connected.
- Kimi managed Python (`python3` in a Kimi shell) or any Python 3.8+ for the
  stdlib-only tools; Node 18+ for the SpotGamma MCP.
- Workspace root: `/Users/filipesalvio/gex-hub`.

---

## Procedure 1 — Health check (start here)

```bash
cd "/Users/filipesalvio/gex-hub"

# 1. Registration state (prints registered/missing per server, no changes)
python3 mcp/mcp_guard.py --status

# 2. MenthorQ MCP smoke test (5 live calls; needs Chrome + MenthorQ login)
python3 mcp/test_mcp.py

# 3. SpotGamma MCP boot test (public endpoints; no token needed)
cd spotgamma-mcp && node test-client.js && cd ..

# 4. Scraper dry check — key levels only
python3 gex_scraper.py --skip-equities
```

Expected: guard prints `registered` for both servers; MenthorQ smoke 5/5;
SpotGamma client lists 45 tools; scraper prints `"status": "ok"`.

If the guard shows `missing`, just run `python3 mcp/mcp_guard.py` — or wait a
few seconds; the LaunchAgent watcher usually heals it first. New tool
registrations require a **new Kimi session** to take effect.

## Procedure 2 — MenthorQ auth failures ("session expired" errors)

1. Open `https://dashboard.menthorq.io` in Chrome and log in again.
2. Retry the call — the server re-reads the session automatically.
3. If Chrome/WebBridge is unavailable, paste a token:
   DevTools → Network → any gateway call → copy the `Bearer` value, then set
   `MENTHORQ_TOKEN` in the server env (or the shell for CLI use).
4. Verify with `python3 mcp/test_mcp.py`.

Rollback: unset `MENTHORQ_TOKEN` to return to WebBridge mode.

## Procedure 3 — SpotGamma auth failures (403 on gated endpoints)

The `sgToken` JWT lives ~3 days. Normally `com.spotgamma.tokenrefresh`
(daily 09:17) renews it. To refresh manually:

```bash
python3 spotgamma-mcp/token_refresh.py   # needs Chrome open + SpotGamma login
```

Exit codes: `0` refreshed (or already current), `2` could not capture (Chrome
closed / logged out — harmless, the next scheduled run retries).
Verify: `python3 mcp/mcp_guard.py --status` shows `spotgamma: registered (with user token)`.
`gex_scraper.py` self-refreshes its token via WebBridge on 401/403 — no action
needed for the scraper.

Rollback: remove `SPOTGAMMA_SG_TOKEN` from the `spotgamma` env block in
`mcp.json` — public/`use_free` tools keep working.

## Procedure 4 — Re-run the MenthorQ scrape campaign

See [../scraper/README.md](../scraper/README.md). Summary:

1. Chrome open, logged in to MenthorQ (WebBridge session `menthorq-scrape`).
2. Assign each unit in `scraper/mq_work_units.json` to one agent with
   `scraper/mq_agent_brief.md`; ≤5 concurrent.
3. Agents use `scraper/mq_api.py` / `scraper/mq_db.py` only — never raw SQL,
   never store the token.
4. Verify:
   ```sql
   SELECT agent_name, unit_key, status FROM scrape_runs ORDER BY id DESC LIMIT 20;
   ```

Rollback: archive data is insert-only; delete rows by `run_id` from
`raw_responses` and the run from `scrape_runs` to undo a bad run.

## Procedure 5 — Re-run the SpotGamma DOM scrape

Legacy campaign (results in `spotgamma.db`): one agent per unit in
`scraper/work_units.json` following `scraper/agent_brief.md`, writing via
`scraper/db_writer.py`. For a single-page refresh, adapt `scrape_daily.py`
(now in `attic/`)
(page list + extraction JS per page). Full schema and query cookbook:
[../SPOTGAMMA_DB_DOCUMENTATION.md](../SPOTGAMMA_DB_DOCUMENTATION.md).

## Procedure 6 — Regenerate documentation

```bash
python3 mcp/gen_docs.py                                # mcp/MCP_DOCS.md (from menthorq.db archive)
cd spotgamma-mcp && node examples-runner.js && node generate-docs.js && cd ..
                                                       # spotgamma-mcp/DOCUMENTATION.md (live calls)
```

`gen_docs.py` redacts personal data; `examples-runner.js` reads the token
from `mcp.json` and needs a valid SpotGamma session for gated examples.

## Procedure 7 — Edit a presentation deck

1. Open the `.pptd` in the Kimi slides editor; export PPTX **only** via the
   editor's export button (never CLI).
2. Validate after edits: `kimi-slides check <deck-dir>` — exactly one `.pptd`
   per directory.
3. YAML pitfalls: quote text containing `:` or `,` inside flow maps; dark
   decks need explicit chart `fill`. See [../presentation/README.md](../presentation/README.md).

## Procedure 8 — Remove the automation (full rollback)

```bash
launchctl unload ~/Library/LaunchAgents/com.menthorq.mcpguard.plist
launchctl unload ~/Library/LaunchAgents/com.spotgamma.tokenrefresh.plist
rm ~/Library/LaunchAgents/com.menthorq.mcpguard.plist \
   ~/Library/LaunchAgents/com.spotgamma.tokenrefresh.plist
```

Then remove the `menthorq` and `spotgamma` keys from Kimi's `mcp.json`
(MERGE-style: leave every other key untouched). Databases, logs and decks are
plain files in this workspace — delete or keep.

## Escalation path

1. **This runbook** → 2. the subsystem README closest to the failure
   (`mcp/README.md`, `spotgamma-mcp/README.md`, `scraper/README.md`) →
   3. project memory vault entities `menthorq-mcp.md` / `spotgamma-mcp.md`
   (Kimi agent memory — kept current after each work session) →
   4. the owner. There is no external on-call: these are personal
   integrations against the owner's own accounts; platform-side outages
   (MenthorQ/SpotGamma down) can only be waited out.

## Known gotchas (hard-won)

1. **`mcp.json` is shared — MERGE, never replace.** It has been wiped twice
   by other tools. The watcher + guard heal our entries; extend the same
   courtesy to theirs.
2. **WebBridge `evaluate` targets the last `navigate`d tab**, not `find_tab`
   selections. All token probes origin-check `location.href` and fall back to
   opening a fresh tab.
3. **No tokens on disk.** `gex_scraper.py` and the MCP servers resolve tokens
   from env vars (`SG_TOKEN`, `MENTHORQ_TOKEN`) or live WebBridge capture
   only; nothing is written to a token file.
4. **Display strings in `spotgamma.db`** carry units (`"3.15B"`, `"15.47%"`) —
   parse before math (helper in `SPOTGAMMA_DB_DOCUMENTATION.md` §4).
5. **Weekend captures freeze at Friday's close** — recorded honestly in
   payloads (`market_state`, `chart_only`, `scanner_empty`); don't mistake
   them for live data.

## gex-poller

Install:  `cp poller/com.gexhub.poller.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.gexhub.poller.plist`
Remove:   `launchctl unload ~/Library/LaunchAgents/com.gexhub.poller.plist`
One shot: `.venv/bin/python3 -m poller.poll --once`
Status:   `.venv/bin/python3 -m poller.status`
Logs:     `logs/poller.jsonl` (cycles), `logs/launchagent.log` (stdout/stderr)

The plist runs the repo venv python (`/Users/filipesalvio/gex-hub/.venv/bin/python3`)
directly, not `/usr/bin/env python3` — system python3 is 3.9 and the poller
requires 3.11+.

The LaunchAgent sets no `EnvironmentVariables` and launchd does not source
shell profiles, so SpotGamma gated endpoints (e.g. v1/me/*, v4/*) need
the token injected separately. After installing the plist, run:

```
launchctl setenv SG_TOKEN <token>
```

(`SPOTGAMMA_SG_TOKEN` is also honored by the server.) The token must never go
into the plist or any committed file — this is a public repo.
