# gex-hub — Documentation Index

> This index reflects the full local workspace; entries marked local-only are
> gitignored and absent from the public repo.

Start with the root [README.md](../README.md) (what this is, quick start,
directory map). This `docs/` folder holds the long-form documentation.

## Documents

| Doc | Audience | Purpose |
|---|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Anyone changing or extending the system | Context, goals, high-level design, key decisions and trade-offs, data flow |
| [API.md](API.md) | Developers / AI agents calling the tools | MCP tool surface, scraper CLIs, authentication, errors, conventions |
| [RUNBOOK.md](RUNBOOK.md) | Operator (usually the owner + agent) | Procedures: health checks, token refresh, re-scrapes, doc regeneration, rollback, escalation |
| [ONBOARDING.md](ONBOARDING.md) | New contributor or a fresh agent session | Environment setup, how the systems connect, common tasks with walkthroughs |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Anyone editing this workspace | Conventions, safety rules, where things live, how to add code |
| [COMPLIANCE.md](COMPLIANCE.md) | Anyone touching the public repo | Publish scope (tooling, no data), ToS basis, contributor rules, excluded paths |

## Detailed references that live next to the code (linked, not duplicated)

- [API_ENDPOINTS.md](../API_ENDPOINTS.md) — MenthorQ gateway endpoint catalog
- [spotgamma-api-endpoints.md](../spotgamma-api-endpoints.md) — SpotGamma endpoint catalog
- [spotgamma-api-docs.md](../spotgamma-api-docs.md) — SpotGamma full API reference with live SPX samples
- [SPOTGAMMA_DB_DOCUMENTATION.md](../SPOTGAMMA_DB_DOCUMENTATION.md) — `spotgamma.db` schema + query cookbook
- [mcp/README.md](../mcp/README.md), [mcp/MCP_DOCS.md](../mcp/MCP_DOCS.md) — MenthorQ MCP server + generated tool reference
- [spotgamma-mcp/README.md](../spotgamma-mcp/README.md), [spotgamma-mcp/DOCUMENTATION.md](../spotgamma-mcp/DOCUMENTATION.md) — SpotGamma MCP server + generated tool reference
- [scraper/README.md](../scraper/README.md) — scraping-campaign tooling
- [attic/README.md](../attic/README.md) — historical one-off scripts (provenance only)
- `presentation/README.md` (local-only) — slide-deck rules

## Research corpus (background, not operational)

QUIN AI research (all local-only): `QUIN_dossier.md`,
`QUIN_AI_Distillation.md`, `quin_menthorq_research.md`, `dossier/`,
`quin_research/`. Legal (local-only): `menthorq-legal-corporate-report.md`,
`terms-of-use.*`, `cookie-policy.*`.

> Keep it current: when you change a system, update the doc that lives
> closest to that system first, then this index if the map changed.
