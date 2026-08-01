# Security Policy

## Token & credential policy

- **No tokens in the repo or on disk.** All live access uses session tokens
  resolved at runtime from environment variables (`SG_TOKEN`,
  `MENTHORQ_TOKEN`, `SPOTGAMMA_SG_TOKEN`) or captured live from the owner's
  own logged-in browser via the local WebBridge daemon. Tokens are held in
  memory only and are never written to a token file.
- The legacy `sg_token.txt` file fallback was removed; it must never return.
- `.env` is gitignored; `.env.example` documents the available variables and
  contains no values.
- No passwords are stored or used anywhere in this project.
- If you ever find a committed token, JWT, cookie, or session value in this
  repository's history, please report it immediately (see below).

## Data policy

- Databases (`*.db`), parquet extracts (`data/`), logs, and browser-captured
  artifacts are **gitignored by design**. They contain data pulled from the
  owner's paid MenthorQ/SpotGamma accounts and are not redistributed.
- This repository publishes code and documentation only.

## Scope notes

- `mcp/mcp_guard.py`, `spotgamma-mcp/token_refresh.py`, and the macOS
  LaunchAgents are single-machine automation for the owner's environment;
  they manage the owner's local `mcp.json` and browser session and are not
  part of the portable tooling.
- The MCP servers and scrapers make outbound requests only to the MenthorQ
  and SpotGamma platforms using the operator's own session.

## Reporting a vulnerability

This is a personal, source-available project (see LICENSE). To report a
security issue — especially any leaked credential — please open an issue on
the repository or contact the owner through the hosting platform. Do not
include real tokens or account data in public reports; redact values and
describe where the secret appears (file, commit) so it can be purged.
