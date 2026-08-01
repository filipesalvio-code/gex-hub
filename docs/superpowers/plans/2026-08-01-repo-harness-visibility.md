# Repo Harness & Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn this local-only workspace into a clean, secure, public-ready open-source repository (GEX/options-positioning MCP servers + scrapers) that others can clone, install, and run — without leaking tokens or redistributing premium data.

**Architecture:** Publish **code only** (MCP servers, scrapers, analysis scripts, docs). Databases, scraped data, archived HTML, logs, tokens, and presentation decks stay local and are gitignored. One git repo at root, Python deps via `pyproject.toml`, Node deps via `spotgamma-mcp/package.json`, tests via pytest + node smoke, CI via GitHub Actions.

**Tech Stack:** Python 3.11+ (requests, pandas, duckdb, matplotlib, mcp), Node 18+ (@modelcontextprotocol/sdk, hono), pytest, ruff, GitHub Actions.

## Global Constraints

- **Never commit secrets.** `sg_token.txt`, `probes.json`, anything matching token/bearer/cookie patterns is excluded before the first commit.
- **Never commit scraped data or DBs.** `*.db`, `data/`, `*.html` archives, `logs/`, parquet — all local-only. Publishing MenthorQ/SpotGamma data violates their ToS (see `terms-of-use.txt`).
- **Merge, never replace `mcp.json`** (existing hard-won convention #1).
- Root folder rename `GEX Scrap` → `gex-hub` happens in Task 4, after secrets are removed (so no path confusion mid-cleanup).
- macOS LaunchAgents (`com.menthorq.mcpguard`, `com.spotgamma.tokenrefresh`) must keep working — absolute paths in their plists need updating after the rename.

---

### Task 1: Secrets audit and neutralization (BLOCKER — nothing else ships before this)

**Files:**
- Delete: `sg_token.txt`
- Modify: `gex_scraper.py` (token loading)
- Modify: `probes.json` (verify/strip)
- Create: `.env.example`

**Interfaces:**
- Consumes: nothing
- Produces: `gex_scraper.py` reads token from the **existing** `SG_TOKEN` env var or the **existing** `refresh_token_via_webbridge(token_file)` live capture only; `.env.example` documenting `SG_TOKEN=` (empty)

NOTE: `gex_scraper.py` already supports `$SG_TOKEN` and already has `refresh_token_via_webbridge(token_file)` — this task REMOVES the `sg_token.txt` file fallback; do not invent new loader functions. Also note: `STATIC_HEADERS` in `gex_scraper.py` contains a JWT that is SpotGamma's static app key shipped in their public JS bundle — it is NOT a user secret; flag it for the Task 2 compliance doc, take no action on it.

- [ ] **Step 1: Rotate the exposed token.** CONTROLLER-OWNED, NOT PART OF THIS TASK — handled outside the implementer flow (Chrome WebBridge clear; pending if the browser extension is disconnected).

- [ ] **Step 2: Scan the whole tree for secrets before any commit**

```bash
cd "/Users/filipesalvio/GEX Scrap"
grep -rInE '(eyJ[A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9._-]{20,}|sgToken|session[_-]?id|api[_-]?key["\x27]?\s*[:=])' \
  --exclude-dir=node_modules --exclude-dir=__pycache__ . > /tmp/secret-scan.txt
wc -l /tmp/secret-scan.txt   # review every hit by hand
```

Expected: hits in `sg_token.txt`, `probes.json`, possibly `mcp/*.py` (code referencing tokens is fine; literal token values are not). Verify each hit is either (a) code that *handles* tokens or (b) a literal secret to remove.

- [ ] **Step 3: Remove the `sg_token.txt` file fallback in `gex_scraper.py`**

The file currently has a `read_token_file`-style helper (around `gex_scraper.py:170-178`) that opens `sg_token.txt`. Delete that helper and every call site, so token resolution is exactly:

1. `SG_TOKEN` env var (already supported — keep)
2. `refresh_token_via_webbridge(token_file)` live capture (already exists — keep, but change it to never *write* a token file: it should return the token string only; update its callers to use the return value instead of re-reading the file)

Keep `DEFAULT_TOKEN_FILE` only if still referenced for backwards-compat messaging; otherwise remove it. Update the module docstring auth paragraph and the CLI error hint (around `gex_scraper.py:319`) to say: set `$SG_TOKEN` or keep Chrome logged in for WebBridge capture.

- [ ] **Step 4: Verify scraper still imports and resolves tokens**

```bash
cd "/Users/filipesalvio/GEX Scrap"
SG_TOKEN="test.jwt.token" python3 -c "
import gex_scraper as gs
assert not hasattr(gs, 'read_token_file'), 'file fallback still present'
print('import ok, no file fallback')
"
```

Expected: `import ok, no file fallback`. (No live WebBridge needed for this check.)

- [ ] **Step 5: Delete the token file and create `.env.example`**

```bash
rm "/Users/filipesalvio/GEX Scrap/sg_token.txt"
```

`.env.example` content:

```
# SpotGamma session token — captured automatically via WebBridge when Chrome is logged in.
# Manual override only:
SG_TOKEN=
```

- [ ] **Step 6: Inspect `probes.json`** — if it contains captured headers/cookies/tokens, move it to `docs/` redacted or delete it. It is listed in the secret-scan hits.

---

### Task 2: Compliance documentation (DECISION ALREADY MADE — document it)

**Files:**
- Read: `terms-of-use.txt`, `cookie-policy.txt`, `menthorq-legal-corporate-report.md`
- Create: `docs/COMPLIANCE.md`

**Interfaces:**
- Consumes: Task 1 done
- Produces: `docs/COMPLIANCE.md` recording the publish scope; Task 10 (README disclaimer) and Task 11 (launch) rely on it

USER RULING (2026-08-01, supersedes the original decision-gate wording): **Publish tooling, no data.** MCP servers, scrapers, and analysis code go public; endpoint catalogs stay in-repo marked "unofficial, personal use"; data, DBs, decks with real scraped numbers, and QUIN research never publish. LICENSE ruling: **proprietary** (source-available, all rights reserved) — see Task 10.

- [ ] **Step 1: Skim `terms-of-use.txt` and `menthorq-legal-corporate-report.md`** for clauses on scraping, redistribution, and API access. Quote 1–3 relevant lines (with section names if present) in the compliance doc.
- [ ] **Step 2: Write `docs/COMPLIANCE.md`** covering, one short section each:
  1. Decision: public repo contains code only; no data, no databases, no scraped content, no decks, no QUIN research.
  2. ToS basis: the quotes from Step 1, with one sentence on why personal-use client tooling is being published anyway (owner's own account, own session token, no redistribution of platform data).
  3. `STATIC_HEADERS` note: `gex_scraper.py` embeds SpotGamma's static app key that ships in their public dashboard JS bundle; it is not a user credential. Record that this was reviewed and accepted.
  4. Contributor rules: never commit tokens, DBs, `data/`, logs, or anything under the gitignored paths; PRs adding scraped data will be rejected.
- [ ] **Step 3: Cross-check `.gitignore` covers every exclusion the doc names** (it is written in Task 3 — if Task 3 already ran, verify; if not, leave a note in the doc that Task 3 implements it).

---

### Task 3: Root `.gitignore` and hygiene files

**Files:**
- Create: `.gitignore`, `.gitattributes`

**Interfaces:**
- Consumes: Task 1 (secrets deleted), Task 2 (exclusion list confirmed)
- Produces: gitignore rules every later task relies on

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# Secrets
.env
sg_token.txt
probes.json

# Agent/planning workspace
.superpowers/
.venv/

# Data & databases (never publish scraped premium data)
*.db
*.db-journal
data/
*.parquet
*.arrow

# Logs & runtime
logs/
__pycache__/
*.pyc
.DS_Store

# Node
node_modules/

# Archived platform pages & research (kept local, ToS-sensitive)
/home_*.html
/quin_*.html
/feature_*.html
/landing_*.html
/sunbiz-*.html
/terms-of-use.*
/cookie-policy.*
/dossier/
/quin_research/
*-screenshots/
/presentation-screenshots/

# Presentations are personal decks — keep local for now
/presentation/
/SpotGamma-for-Traders/
/spotgamma_trader_deck/

# Generated artifacts
spx_gamma_curve.png
guide_*_body.txt
home_2022_body.txt
```

- [ ] **Step 2: Create `.gitattributes`**

```gitattributes
* text=auto eol=lf
*.png binary
*.pptd binary
```

- [ ] **Step 3: Dry-run verification (no git yet)**

```bash
cd "/Users/filipesalvio/GEX Scrap"
python3 - <<'EOF'
import fnmatch, os
rules = [l.strip() for l in open('.gitignore') if l.strip() and not l.startswith('#')]
bad = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('node_modules','__pycache__')]
    for f in files:
        p = os.path.join(root, f).lstrip('./')
        if f.endswith('.db') or f == 'sg_token.txt':
            if not any(fnmatch.fnmatch(f, r) or fnmatch.fnmatch(p, r.lstrip('/')) for r in rules):
                bad.append(p)
print("UNIGNORED SENSITIVE:", bad or "none")
EOF
```

Expected: `UNIGNORED SENSITIVE: none`

---

### Task 4: Git init, rename, first commit

**Files:**
- Rename: `/Users/filipesalvio/GEX Scrap` → `/Users/filipesalvio/gex-hub`
- Modify: `~/Library/LaunchAgents/com.spotgamma.tokenrefresh.plist` (path update)
- Modify: `~/Library/LaunchAgents/com.menthorq.mcpguard.plist` (path update)

**Interfaces:**
- Consumes: Tasks 1–3
- Produces: a git repo at `~/gex-hub` with a clean initial commit; LaunchAgents pointing at the new path

- [ ] **Step 1: Update LaunchAgent paths first** (they reference the old absolute path; do it while you remember)

```bash
for p in com.menthorq.mcpguard com.spotgamma.tokenrefresh; do
  launchctl unload ~/Library/LaunchAgents/$p.plist
  sed -i '' 's|/Users/filipesalvio/GEX Scrap|/Users/filipesalvio/gex-hub|g' ~/Library/LaunchAgents/$p.plist
done
```

- [ ] **Step 2: Rename and init**

```bash
mv "/Users/filipesalvio/GEX Scrap" "/Users/filipesalvio/gex-hub"
cd "/Users/filipesalvio/gex-hub"
git init -b main
```

- [ ] **Step 3: Verify nothing sensitive is staged**

```bash
git add -A
git status --short | grep -iE '(\.db$|token|probes\.json|\.env|parquet|logs/)' && echo "ABORT: sensitive file staged" || echo "clean"
```

Expected: `clean`

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: initial public-ready import of gex-hub"
```

- [ ] **Step 5: Reload agents and smoke-test the guard**

```bash
launchctl load ~/Library/LaunchAgents/com.menthorq.mcpguard.plist
launchctl load ~/Library/LaunchAgents/com.spotgamma.tokenrefresh.plist
python3 mcp/mcp_guard.py --status
```

Expected: guard reports both MCP entries healthy from the new path.

---

### Task 5: Python dependency harness (`pyproject.toml`)

**Files:**
- Create: `pyproject.toml`
- Modify: `README.md` (install section)

**Interfaces:**
- Consumes: Task 4
- Produces: `pip install -e .` works; CI (Task 10) installs from this file

- [ ] **Step 1: Inventory imports** — already done during planning: third-party = `requests`, `pandas`, `matplotlib`, `duckdb`, `mcp`. NOTE: `daimon_runtime` and `db_writer` are imported by `plot_spx_gamma.py` / scraper scripts but are **not in this repo** — they live in your personal harness. Decide per file: inline the needed function, or guard the import.

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "gex-hub"
version = "0.1.0"
description = "Local-first options-positioning (GEX) data hub: MenthorQ & SpotGamma MCP servers, scrapers, and analysis tools"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
dependencies = [
  "requests>=2.31",
  "pandas>=2.0",
  "duckdb>=0.10",
  "matplotlib>=3.8",
  "mcp>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.5"]

[tool.setuptools]
py-modules = ["gex_scraper", "positioning_artifact", "plot_spx_gamma"]

[tool.ruff]
line-length = 110
```

- [ ] **Step 3: Fix external-module imports.** For `plot_spx_gamma.py`, replace `from daimon_runtime import setup_plot` with a local 5-line matplotlib style function. For scraper scripts importing `db_writer`, either copy the function into `scraper/db_writer.py` or delete dead one-off scripts (Task 7 will remove most).

- [ ] **Step 4: Verify clean install**

```bash
cd /Users/filipesalvio/gex-hub
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python3 -c "import gex_scraper, positioning_artifact, plot_spx_gamma; print('imports ok')"
```

Expected: `imports ok`

(Add `.venv/` to `.gitignore` and commit both changes.)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore README.md plot_spx_gamma.py
git commit -m "build: add pyproject.toml, remove external harness deps"
```

---

### Task 6: Repo structure cleanup

**Files:**
- Move: root one-off scripts → `attic/`
- Modify: `README.md` directory map

**Interfaces:**
- Consumes: Task 4 (git repo, so moves are tracked)
- Produces: root with only maintained entry points; `attic/` clearly marked unmaintained

- [ ] **Step 1: Classify root files.** Maintained (stay): `gex_scraper.py`, `positioning_artifact.py`, `plot_spx_gamma.py`, `mcp/`, `spotgamma-mcp/`, `scraper/mq_*.py`, `docs/`, `README.md`, `*.md` API catalogs (pending Task 2 decision). Attic: `probe_api.py`, `rescrape_eh_hiro.py`, `scrape_daily.py`, `gex_binary.py`, `update_deck.py`, `spotgamma-index.js`, `spotgamma-polling-worker.js`.

- [ ] **Step 2: Move and label**

```bash
cd /Users/filipesalvio/gex-hub
mkdir -p attic
git mv probe_api.py rescrape_eh_hiro.py scrape_daily.py gex_binary.py update_deck.py \
       spotgamma-index.js spotgamma-polling-worker.js attic/
printf '# Attic\n\nHistorical one-off campaign scripts. Kept for provenance, not maintained, not supported.\n' > attic/README.md
git add attic/README.md
```

- [ ] **Step 3: Fix any surviving import of moved files** — grep for their names outside `attic/`:

```bash
grep -rn -E '(probe_api|rescrape_eh_hiro|scrape_daily|gex_binary|update_deck|spotgamma-index|spotgamma-polling-worker)' \
  --include='*.py' --include='*.js' --include='*.md' . | grep -v attic/ | grep -v node_modules
```

Expected: only doc references; update README directory map to point at `attic/`.

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor: move one-off campaign scripts to attic/"
```

---

### Task 7: Project `AGENTS.md`

**Files:**
- Create: `AGENTS.md`

**Interfaces:**
- Produces: agent-facing rules file (the repo's portable SoT, per your harness convention)

- [ ] **Step 1: Create `AGENTS.md`** — short, rules only:

```markdown
# gex-hub agent rules

- Secrets: never commit tokens. Tokens come from `GEX_SG_TOKEN` env or live WebBridge capture (127.0.0.1:10086).
- Data: `*.db`, `data/`, `logs/` are local-only and gitignored. Never commit scraped data (ToS).
- `mcp.json` (Kimi registry) is shared — MERGE, never replace.
- Tests: `pytest` (offline, mocked). Live smoke: `python3 mcp/test_mcp.py` (needs Chrome session).
- Lint: `ruff check .`. Node syntax: `node --check spotgamma-mcp/server.js`.
- Docs: after editing `mcp/menthorq_mcp.py` run `python3 mcp/gen_docs.py`.
- `attic/` is unmaintained; do not "fix" files there.
```

- [ ] **Step 2: Commit** — `git add AGENTS.md && git commit -m "docs: add AGENTS.md agent rules"`

---

### Task 8: Offline test harness (pytest, mocked)

**Files:**
- Create: `tests/test_gex_scraper.py`, `tests/test_positioning_artifact.py`, `tests/conftest.py`
- Modify: `pyproject.toml` (pytest config)

**Interfaces:**
- Consumes: Task 5 (dev extras include pytest)
- Produces: `pytest` passes with **no network, no Chrome, no tokens**; CI (Task 10) runs exactly this

- [ ] **Step 1: Write `tests/conftest.py`** — fixture building a tiny in-memory sqlite with the `key_levels` schema (copy `CREATE TABLE` from `gex_scraper.py`) and a fake WebBridge transport:

```python
import sqlite3, pytest

@pytest.fixture
def mem_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE key_levels (
        symbol TEXT, date TEXT, level_type TEXT, price REAL)""")
    conn.execute("INSERT INTO key_levels VALUES ('SPX','2026-07-31','call_wall',6800.0)")
    yield conn
    conn.close()
```

(Adjust columns to the real schema — read it via `sqlite3 gex_data.db '.schema key_levels'` locally when implementing.)

- [ ] **Step 2: Write failing tests** — e.g. `test_load_token_prefers_env` (monkeypatch `GEX_SG_TOKEN`, assert returned), `test_load_token_falls_back_to_webbridge` (monkeypatch capture fn, assert called), `test_artifact_aggregates_levels` (use `mem_db`).

- [ ] **Step 3: Run, see failures**

```bash
pytest tests/ -v   # Expected: FAIL — token loader/artifact fns not yet importable/pure
```

- [ ] **Step 4: Minimal refactors to pass** — make `load_token` and the artifact builder accept an injected DB path/connection (dependency injection, no behavior change). Re-run: PASS.

- [ ] **Step 5: Add pytest config to `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 6: Commit**

```bash
git add tests/ pyproject.toml gex_scraper.py positioning_artifact.py
git commit -m "test: offline pytest harness with mocked token + in-memory db"
```

---

### Task 9: CI (GitHub Actions) + lint

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: Tasks 5, 8
- Produces: green CI on every push; the file works even before the repo is public

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: ci
on: [push, pull_request]
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest -q
  node:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: 20}
      - run: npm ci
        working-directory: spotgamma-mcp
      - run: node --check server.js
        working-directory: spotgamma-mcp
```

- [ ] **Step 2: Ensure `spotgamma-mcp/package-lock.json` exists** (`npm ci` needs it): `cd spotgamma-mcp && npm install --package-lock-only && git add package-lock.json`

- [ ] **Step 3: Run locally what CI runs**

```bash
ruff check . && pytest -q && node --check spotgamma-mcp/server.js
```

Expected: all pass.

- [ ] **Step 4: Commit** — `git add .github spotgamma-mcp/package-lock.json && git commit -m "ci: lint + offline tests + node syntax check"`

---

### Task 10: Public-facing README, LICENSE, SECURITY

**Files:**
- Modify: `README.md`
- Create: `LICENSE`, `SECURITY.md`

**Interfaces:**
- Consumes: Task 2 (license decision + compliance scope)
- Produces: landing page for the public repo

- [ ] **Step 1: Rewrite the top of `README.md`** for strangers — keep the existing deep content below a `## For maintainers` fold:

```markdown
# gex-hub

Local-first hub for options positioning / gamma-exposure (GEX) data.
MCP servers that let AI assistants query MenthorQ & SpotGamma with **your own** session — plus scrapers, a time-series store, and charting.

## Quickstart
pip install -e ".[dev]"
python3 mcp/test_mcp.py        # needs your Chrome session (see docs/ONBOARDING.md)

## What you get
- `menthorq` MCP server — 24 tools (positioning, gamma levels, …)
- `spotgamma` MCP server — 45 tools + automatic token refresh
- GEX time series → sqlite/parquet, SPX gamma-curve plots

> Unofficial, personal-use tooling. Requires your own paid MenthorQ/SpotGamma accounts. No data is included or redistributed.
```

- [ ] **Step 2: `LICENSE`** — PROPRIETARY (user ruling 2026-08-01, supersedes the MIT default). Source-available, all-rights-reserved text:

```
Copyright (c) 2026 Filipe Salvio. All rights reserved.

This repository is made publicly visible for demonstration and evaluation
purposes only. No license is granted to use, copy, modify, merge, publish,
distribute, sublicense, or sell the software or its documentation, in whole
or in part, without prior written permission from the copyright holder.

Viewing and forking this repository through the hosting platform's UI is
permitted to the extent required by the platform's terms of service.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
```

Also update `pyproject.toml` in Task 5: `license = {text = "Proprietary"}` (plan text there says MIT — proprietary governs).

- [ ] **Step 3: `SECURITY.md`** — token policy (env/WebBridge only), how to report, note that DBs are gitignored by design.

- [ ] **Step 4: Commit** — `git add README.md LICENSE SECURITY.md && git commit -m "docs: public README, MIT license, security policy"`

---

### Task 11: Launch

**Files:** none (GitHub UI + git remote)

- [ ] **Step 1: Final pre-flight**

```bash
cd /Users/filipesalvio/gex-hub
git log --stat | grep -iE '(\.db|sg_token|\.env)' && echo ABORT || echo "history clean"
ruff check . && pytest -q && python3 mcp/mcp_guard.py --status
```

Plus, before pushing: **confirm the SpotGamma token rotation happened** (controller item from Task 1: WebBridge clear of `sgToken` in Chrome, or a manual logout/login by the owner). If the WebBridge extension was disconnected during Task 1, retry it now — the rotation must be verified, not assumed.

- [ ] **Step 2: Create and push**

```bash
gh repo create gex-hub --public --source . --push \
  --description "Local-first options positioning (GEX) hub — MenthorQ & SpotGamma MCP servers for AI assistants"
gh repo edit --add-topic mcp,options-trading,gamma-exposure,gex,spotgamma,menthorq,ai-agents
```

- [ ] **Step 3: Post-launch** — verify LaunchAgents still healthy on new path, update vault entities `menthorq-mcp.md`/`spotgamma-mcp.md` (your project memory) with the public URL, flip the README status line "not a git repo / local-only" to the repo URL.

---

## Risk notes

- **ToS (highest risk):** Task 2 can veto launch. Everything before it is still valuable privately.
- **Token leakage:** mitigated by Task 1 rotation + gitignore + pre-commit scan; no git history exists yet, so no scrubbing needed.
- **`daimon_runtime`/`db_writer`:** external personal-harness imports will break clones — fixed in Task 5 Step 3.
- **LaunchAgent path breakage** after rename — handled in Task 4 Step 1/5.
