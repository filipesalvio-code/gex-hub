# gex-hub agent rules

- Secrets: never commit tokens. Tokens come from `SG_TOKEN` env var or live WebBridge capture (127.0.0.1:10086).
- Data/secrets exclusions are enforced by .gitignore per docs/COMPLIANCE.md §5 — never commit anything it lists.
- Data: `*.db`, `data/`, `logs/` are local-only and gitignored. Never commit scraped data (ToS).
- `mcp.json` (Kimi registry) is shared — MERGE, never replace.
- Tests: `pytest` (offline, mocked; see tests/). Live smoke: `python3 mcp/test_mcp.py` (needs Chrome session).
- Lint: `ruff check .`. Node syntax: `node --check spotgamma-mcp/server.js`.
- Docs: after editing `mcp/menthorq_mcp.py` run `python3 mcp/gen_docs.py`.
- `attic/` is unmaintained; do not "fix" files there.
