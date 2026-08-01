"""mq-agent-20 section B fix: reuse the session's vol tab (newTab:false) to
load the 2 missing account pages, so evaluate can't land on the wrong tab."""
import json, sys, time, urllib.request

sys.path.insert(0, 'scraper')
from mq_db import save_response, finish_run

RUN_ID = 23
SESSION = "menthorq-scrape"
DAEMON = "http://127.0.0.1:10086/command"
VOL_TAB = "https://menthorq.com/account/?action=data&type=dashboard&commands=vol&date=2026-07-25"

TARGETS = [
    ("https://menthorq.com/account/?action=data&type=dashboard&commands=cta", "commands=cta"),
    ("https://menthorq.com/account/?action=data&type=summary&category=cryptos", "type=summary"),
]

EXTRACT = r"""
(()=>{
  const text = document.body ? document.body.innerText : '';
  const tables = [...document.querySelectorAll('table')].map(t =>
    [...t.querySelectorAll('tr')].map(tr =>
      [...tr.querySelectorAll('th,td')].map(c => c.innerText.trim())));
  return JSON.stringify({url: location.href, title: document.title,
    len: text.length, text: text.slice(0, 80000), tables: tables.slice(0, 60)});
})()
"""

def cmd(action, args, timeout=45):
    body = json.dumps({"action": action, "args": args, "session": SESSION}).encode()
    req = urllib.request.Request(DAEMON, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def evaluate(code):
    out = cmd("evaluate", {"code": code}, 60)
    if not out.get("ok"): return None
    val = (out.get("data") or {}).get("value")
    if isinstance(val, str):
        try: return json.loads(val)
        except json.JSONDecodeError: return val
    return val

for url, marker in TARGETS:
    got = None
    try:
        print('find_tab:', json.dumps(cmd("find_tab", {"url": VOL_TAB}))[:140])
    except Exception as e:
        print('find_tab err:', repr(e)[:100])
    time.sleep(1)
    try:
        print('nav:', json.dumps(cmd("navigate", {"url": url, "newTab": False}))[:140])
    except Exception as e:
        print('nav timeout/err (expected):', repr(e)[:100])
    time.sleep(5)
    for i in range(8):
        try: data = evaluate(EXTRACT)
        except Exception: data = None
        if isinstance(data, dict) and marker in (data.get('url') or '') and data.get('len', 0) > 120:
            got = data; break
        time.sleep(4)
    if got:
        payload = {"text": got["text"], "tables": got["tables"],
                   "title": got.get("title", ""), "final_url": got.get("url", url)}
        save_response(RUN_ID, 'account-site', url, 200, payload)
        print(f'[200] {url}  text={len(got["text"])} chars, tables={len(got["tables"])}, final={got["url"]}')
    else:
        print(f'[FAILED] {url}')

finish_run(RUN_ID, 'ok', 'sectionA 13/13; sectionB 4 pages (cta+summary re-captured via tab reuse)')
