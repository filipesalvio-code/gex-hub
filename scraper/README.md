# scraper/ — MenthorQ scraping campaign tooling

Support code for the 2026-07-25 full-platform MenthorQ scrape (20 work units,
results in `../menthorq.db`). For the big picture see `../README.md`.

## The maintained four

| File | Role |
|---|---|
| `mq_api.py` | API client: pulls a fresh bearer token from the open `dashboard.menthorq.io` tab via WebBridge (5-min in-memory cache, never persisted), GET with 429/5xx backoff. `get(service, path) -> (status, json)` |
| `mq_db.py` | SQLite helpers for `../menthorq.db`: `init_db`, `start_run`/`finish_run`, `save_response`, `save_endpoint`, `upsert_ticker`. Agents must use these, never raw SQL |
| `mq_work_units.json` | The 20-unit campaign definition (endpoint lists per unit) |
| `mq_agent_brief.md` | The standard brief every scraping agent followed (procedure, rules, section B for the WordPress account pages) |

## Quick start

```python
import sys; sys.path.insert(0, 'scraper')
from mq_api import get
from mq_db import start_run, save_response, finish_run

run_id = start_run('my-agent', 'ad-hoc')
status, data = get('clickhouse-api', '/api/web/v1/gamma-levels/SPX/eod')
save_response(run_id, 'clickhouse-api',
              'https://gateway.menthorq.io/clickhouse-api/api/web/v1/gamma-levels/SPX/eod',
              status, data)
finish_run(run_id, 'ok' if status == 200 else 'partial', f'http={status}')
```

Services: `clickhouse-api` (market data), `qbot-service` (news/assets),
`user-service`, `chat-service` (QUIN). Endpoint rules (intraday metric field
names, candle params, required `frequency`, dead endpoints) are documented in
`../API_ENDPOINTS.md` and the `api_endpoints` table.

## Re-running a full campaign

1. Ensure Chrome is open with a logged-in `dashboard.menthorq.io` tab
   (WebBridge session `menthorq-scrape`).
2. Assign each unit in `mq_work_units.json` to an agent with the brief in
   `mq_agent_brief.md` (one unit per agent, ≤5 concurrent to stay polite).
3. Verify: `SELECT agent_name, unit_key, status FROM scrape_runs ORDER BY id DESC LIMIT 20;`

## Everything else in this folder

`run_*.py`, `tmp_*.py`, `extract_*.js`, `probe_*.js`, `sg18_*`, `agent16_*`,
`*.json` payloads, and the old `db_writer.py` / `work_units.json` /
`agent_brief.md` trio are **historical one-off scripts** from various scraping
campaigns (MenthorQ and SpotGamma). Kept for provenance — treat as read-only
reference, not maintained code. The SpotGamma trio pairs with `../spotgamma.db`
(schema in `../SPOTGAMMA_DB_DOCUMENTATION.md`).
