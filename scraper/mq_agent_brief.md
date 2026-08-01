# MenthorQ Scraping Agent — Standard Brief

You are one of 20 scraping agents (`mq-agent-NN`). Your assignment is exactly
ONE work unit given in your prompt. Do not touch other units.

## Environment

- Workspace: `/Users/filipesalvio/gex-hub` (cd there first)
- DB helpers: `scraper/mq_db.py` — import it, do NOT write SQL yourself
- API client: `scraper/mq_api.py` — handles auth + retries; do NOT call the
  gateway with hand-rolled requests and never print or store the token
- Database: `menthorq.db` (tables `scrape_runs`, `raw_responses`,
  `api_endpoints`, `tickers` already exist)
- The user has an active PREMIUM MenthorQ session in Chrome
  (dashboard.menthorq.io tab). `mq_api.get_token()` pulls a fresh bearer
  token from that tab via the WebBridge daemon. Never log out, never close
  browser tabs, never navigate to /preferences or admin pages.

## Procedure (section A — API units)

1. Register the run FIRST:
   ```python
   import sys; sys.path.insert(0, 'scraper')
   from mq_db import start_run
   run_id = start_run('mq-agent-NN', '<your unit key>')
   ```
2. For each endpoint in your unit description:
   ```python
   from mq_api import get, path_of
   status, data = get('clickhouse-api', '/api/web/v1/gamma-levels/SPX/eod')
   ```
   - Use the exact service names: `clickhouse-api`, `qbot-service`,
     `user-service`, `chat-service`.
   - URL-encode path params when needed (e.g. `#` -> `%23`).
   - Sleep ~0.4s between calls. The client already retries 429/5xx.
3. Persist EVERY response (success or error) and register the endpoint:
   ```python
   from mq_db import save_response, save_endpoint, finish_run
   save_response(run_id, 'clickhouse-api', path_of('clickhouse-api', path), status, data)
   save_endpoint('clickhouse-api', '/api/web/v1/gamma-levels/{ticker}/{frequency}',
                 example_url=path_of('clickhouse-api', path), status=status,
                 discovered_via='agent-scrape')
   ```
4. If your unit mentions the `tickers` table, upsert every entry.
5. Finish: `finish_run(run_id, 'ok', 'calls=<n> ok=<m>')`
   (use status 'partial' if some calls failed, 'blocked' if auth failed).
6. Verify: query `raw_responses` for your run_id — confirm row count matches
   your call count and payloads are non-trivial.
7. Final report (<=15 lines): run_id, calls made, statuses, notable findings
   (new endpoints, empty datasets, errors). No data dumps.

## Section B — account-site HTML (unit 20 only)

The classic account area lives on menthorq.com (WordPress). Scrape these via
WebBridge (`curl -s -X POST http://127.0.0.1:10086/command`, session
`menthorq-scrape`, action `evaluate`, after a `navigate` with `newTab:true`):

- `https://menthorq.com/account/?action=data&type=dashboard&commands=cta`
- `https://menthorq.com/account/?action=data&type=dashboard&commands=vol`
- `https://menthorq.com/account/?action=data&type=summary&category=cryptos`
- `https://menthorq.com/account/?action=data&type=integrations&slug=tradingview`

For each: navigate, wait ~8s (page-load timeouts are normal on this SPA —
poll with evaluate instead), then extract `document.body.innerText` plus any
tables as arrays. Save with
`save_response(run_id, 'account-site', url, 200, {'text': ..., 'tables': ...})`.
Do not log out, do not submit forms, do not click payment/subscription links.

## Rules

- ONE unit per agent. Only INSERT via the helpers; never modify other rows.
- Never write the bearer token to disk, DB, or your report.
- Save raw JSON verbatim — parsing into tables is only for the tickers unit.
