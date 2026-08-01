# SpotGamma Scraping Agent — Standard Brief

You are one of 20 scraping agents (`sg-agent-NN`). Your assignment is exactly
ONE work unit given in your prompt (section + URL). Do not touch other units.

## Environment

- Workspace: `/Users/filipesalvio/gex-hub`
- DB helper: `scraper/db_writer.py` (import it; do NOT write SQL yourself)
- Database: `spotgamma.db` (tables `scrape_runs`, `raw_snapshots` already exist)
- Browser control: Kimi WebBridge daemon at `http://127.0.0.1:10086/command`
- The user IS logged into SpotGamma in this browser. Do not log out, do not
  navigate to /preferences or /admin, never close tabs.

## WebBridge rules (critical)

- Your prompt gives you a personal session name `spotgamma-scrape-NN`.
  Use it as the top-level `"session"` field of EVERY request. Never use
  another agent's session, never use the bare `spotgamma-scrape` session.
- On your FIRST `navigate`, also pass
  `"group_title":"SpotGamma agent NN"` (your number).
- Request format:
  ```bash
  curl -s -X POST http://127.0.0.1:10086/command -H 'Content-Type: application/json' \
    -d '{"action":"navigate","args":{"url":"<YOUR URL>","newTab":true,"group_title":"SpotGamma agent NN"},"session":"spotgamma-scrape-NN"}' --max-time 60
  ```
- Useful actions: `navigate`, `evaluate` (JS, async allowed), `snapshot`.
- `evaluate` shares the page JS realm: wrap code in an IIFE
  `(() => { ... })()` and return compact `JSON.stringify(data)` only.

## Procedure

1. Register the run FIRST (from the workspace dir):
   ```python
   python3 -c "
   import sys; sys.path.insert(0, 'scraper')
   from db_writer import start_run
   print(start_run('sg-agent-NN', '<YOUR URL>'))"
   ```
   → this prints your run_id. Keep it.
2. `navigate` (newTab:true) to your URL with your session + group title.
3. Wait for the React app: `evaluate`
   `new Promise(r=>setTimeout(()=>r({url:location.href,title:document.title}),8000))`
   If the title/url suggests a login wall, `finish_run(run_id,'blocked','login wall')` and stop.
4. Extract the section's data with one or more `evaluate` calls:
   - Metric cards, stat boxes, level lists: label + value pairs.
   - Tables (`<table>` or div-grids): headers + rows as arrays.
   - Chart-only widgets (canvas/SVG): grab legend/axis/tooltip DOM text;
     if numbers live only in the chart, include `"chart_only": true`.
   - Also capture `document.title` and `location.href` in every payload.
   - If a response looks truncated, split extraction per-widget into several
     calls and store each as its own snapshot under the same run_id.
5. Persist each chunk (write a small temp python script if easier):
   ```python
   import sys; sys.path.insert(0, 'scraper')
   from db_writer import save_snapshot, finish_run
   save_snapshot(run_id, '<final URL>', '<section>', payload_dict)
   finish_run(run_id, 'ok', 'items=<n>')
   ```
6. Verify: query `raw_snapshots` for your run_id and confirm ≥1 row with
   non-trivial JSON (>200 chars).
7. Final report: run_id, snapshot row ids, what you captured, item counts,
   anything chart-only/missing. Keep it under 15 lines.

## Rules

- ONE unit per agent. No navigation to other sections.
- Only INSERT via the helpers; never modify other agents' rows.
- Do not close your tab when done; leave it for the user to inspect.
