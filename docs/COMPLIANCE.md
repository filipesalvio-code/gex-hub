# Compliance — what publishes, what doesn't, and why

This document records the publish-scope decision for this repository and the
rules that keep it true. It is the reference Task 10 (README disclaimer) and
Task 11 (launch) point at, and the checklist Task 3's `.gitignore` is verified
against.

## 1. Decision

**Publish tooling, no data.** (Owner ruling, 2026-08-01.)

The public repository contains **code only**: the MCP servers (`mcp/`,
`spotgamma-mcp/`), the scrapers and analysis code (`gex_scraper.py`,
`gex_binary.py` (in `attic/`), `positioning_artifact.py`, `plot_spx_gamma.py`, `scraper/`),
and the documentation. The endpoint catalogs (`API_ENDPOINTS.md`,
`spotgamma-api-endpoints.md`, `spotgamma-api-docs.md`) stay in-repo, marked
**unofficial, personal use**.

The following never publish:

- Scraped data and datasets (`data/`, `probes.json`, root `*.html` / `*.txt`
  page archives).
- Databases (`gex_data.db`, `menthorq.db`, `spotgamma.db`, any `*.db`).
- Decks and artifacts containing real scraped numbers (`presentation/`,
  `presentation-screenshots/`, `spotgamma_trader_deck/`,
  `spotgamma_trader_deck_screenshot/`, exported charts such as
  `spx_gamma_curve.png`).
- QUIN research (`QUIN_dossier.md`, `QUIN_AI_Distillation.md`,
  `quin_menthorq_research.md`, `dossier/`, `quin_research/`).
- Credentials and machine-local config: `sg_token.txt`, `mcp/mcp.json`,
  `logs/`.

License ruling: **proprietary, source-available, all rights reserved** (see
Task 10). Source-available does not grant redistribution rights.

## 2. ToS basis

The platform Terms of Use restrict what may be done with MenthorQ content and
data. Relevant clauses (verbatim, from `terms-of-use.txt`):

> "All content on the Website, including text, visuals, software, and
> trademarks, is owned by Menthor Q LLC or its licensors and protected by U.S.
> and international law. You are granted a limited, non-transferable license
> for personal or internal business use. You may not: Copy, reproduce, or
> redistribute content / Create derivative works / Use trademarks or brand
> elements without permission / Reverse-engineer, rent, or sublicense our
> content or software"
> — Terms of Use, §5 "Intellectual Property & License Grant"
> (`terms-of-use.txt:176-182`)

> "You may not redistribute, resell, sublicense, publish, broadcast, transfer,
> display, scrape, download in bulk, or otherwise make real-time data
> available to any third party except as expressly permitted by MenthorQ and
> the applicable third-party provider, exchange, licensor, or vendor."
> — Terms of Use, §18 "Third Party Providers and Real Time Market Data"
> (`terms-of-use.txt:240`)

> "A 'Non-Professional Subscriber' generally means an individual who accesses
> real-time data solely for personal, non-commercial use..."
> — Terms of Use, §18 (`terms-of-use.txt:235`)

Why the tooling is published anyway: this repo is **personal-use client
tooling** — it talks to the platforms with the owner's own account and the
owner's own session token, and it publishes **no platform data**. The clauses
above prohibit redistributing MenthorQ's *content and data*; that is exactly
what Section 1 excludes. The code itself (request shapes, parsers, MCP tool
definitions) is the owner's work product. The endpoint catalogs are marked
unofficial and carry no scraped payloads. This is the owner's ruling; this
document records it, it does not re-adjudicate it.

## 3. `STATIC_HEADERS` in `gex_scraper.py` — reviewed and accepted

`gex_scraper.py:44-53` embeds a static `x-json-web-token` (also present in
`spotgamma-mcp/server.js` and documented in `spotgamma-api-docs.md`). This is
**SpotGamma's static application key, hardcoded in their public dashboard JS
bundle** — it ships to every browser that loads dashboard.spotgamma.com and is
identical for all users. It is **not a user credential**: it identifies the
web app, not a person, and grants no account access by itself (gated
endpoints additionally require the user's own `sgToken` Bearer token).

Reviewed during the 2026-08-01 publish-prep secret scan
(`.superpowers/sdd/2026-08-01-repo-harness-visibility/secret-scan.txt`) and
**accepted as not-a-user-credential**. It stays in the published code.

By contrast, `sg_token.txt` (the owner's real session JWT) was deleted in
Task 1, and `mcp/mcp.json.backup` had its token redacted in Task 1.

## 4. Contributor rules

These rules are not negotiable. PRs that violate them will be rejected.

1. **Never commit tokens, session IDs, or credentials of any kind.** Tokens
   come from env vars (`MENTHORQ_TOKEN`, `SG_TOKEN`, `SPOTGAMMA_SG_TOKEN`) or
   live browser capture — never from files in the repo.
2. **Never commit data.** No `data/`, no `*.db`, no `probes.json`, no scraped
   HTML/JSON payloads, no logs.
3. **Never commit decks or documents containing real scraped numbers.**
4. **Never commit QUIN research** or any platform content beyond the endpoint
   catalogs already in scope.
5. **Never commit anything under the gitignored paths** listed in Section 5.
   If you need a new local-only path, add it to `.gitignore` first.
6. Endpoint catalogs you add or update must be marked **unofficial, personal
   use** and must contain request/response *shapes*, not real data payloads.

## 5. Paths that must stay out of the public repo

Task 3 implements `.gitignore`; this list is what it is checked against.

| Path | Reason |
|---|---|
| `sg_token.txt` | Owner's session token (deleted in Task 1; must never return) |
| `.env`, `.env.*` (except `.env.example`) | Local env-var files may contain tokens; `.env.example` is publishable |
| `mcp/mcp.json` | Live MCP config with token env vars |
| `mcp/mcp.json.backup` | Machine-specific backup; still embeds an absolute local path — **decision: exclude the whole file** rather than redact further |
| `data/` | Scraped datasets |
| `*.db` (`gex_data.db`, `menthorq.db`, `spotgamma.db`) | Databases of scraped data |
| `probes.json` | Scraped probe output |
| `logs/` | Runtime logs (may contain tokens/account data) |
| Root `*.html`, `*.txt` page archives (`home_*`, `quin_*`, `guide_*`, `feature_quin_*`, `sunbiz-*`, etc.) | Raw scraped platform content |
| `presentation/`, `presentation-screenshots/`, `spotgamma_trader_deck/`, `spotgamma_trader_deck_screenshot/`, `SpotGamma-for-Traders/`, `SpotGamma-for-Traders-screenshots/`, `spx_gamma_curve.png` | Decks/artifacts with real scraped numbers |
| `QUIN_dossier.md`, `QUIN_AI_Distillation.md`, `quin_menthorq_research.md`, `dossier/`, `quin_research/` | QUIN research (owner ruling: never publishes) |
| `terms-of-use.*`, `cookie-policy.*`, `menthorq-legal-corporate-report.md` | Platform legal documents / legal research — kept local, quoted here by reference |
| `spotgamma-index.js`, `spotgamma-polling-worker.js` | Verbatim copies of SpotGamma's proprietary JS bundle — third-party code, not ours to publish |
| `scraper/` raw payload JSONs (`a16_b*`, `*_payload_*`, `skew_*`, `ts_chart_raw`, `vix_*`, `fsm_data`) and `scraper/tmp_*` scratch files/dirs | Scraped platform data from campaigns; `mq_work_units.json`/`work_units.json` are tooling and stay publishable |
| `__pycache__/`, `*.pyc` | Build artifacts |

Notes:

- The `mcp/mcp.json.backup` decision is **exclusion** (recommended over
  redaction): it is a machine-specific backup whose token was already
  redacted in Task 1 but whose embedded absolute path
  (`/Users/filipesalvio/Documents/Kimi/Workspaces/...`) is local-only
  information. Task 3 must add it to `.gitignore`.
- `.superpowers/` (planning/working files) also stays local.
