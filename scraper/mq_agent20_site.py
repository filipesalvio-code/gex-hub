"""mq-agent-20 section B: account-site HTML scrape via WebBridge.

Scrapes 4 menthorq.com account pages in the user's own session, saves
body text + tables via save_response under the same run_id as section A.
"""
import json
import sys
import time
import urllib.request

sys.path.insert(0, 'scraper')
from mq_db import save_response, finish_run

RUN_ID = 23
SESSION = "menthorq-scrape"
DAEMON = "http://127.0.0.1:10086/command"

URLS = [
    "https://menthorq.com/account/?action=data&type=dashboard&commands=cta",
    "https://menthorq.com/account/?action=data&type=dashboard&commands=vol",
    "https://menthorq.com/account/?action=data&type=summary&category=cryptos",
    "https://menthorq.com/account/?action=data&type=integrations&slug=tradingview",
]

EXTRACT = r"""
(()=>{
  const text = document.body ? document.body.innerText : '';
  const tables = [...document.querySelectorAll('table')].map(t =>
    [...t.querySelectorAll('tr')].map(tr =>
      [...tr.querySelectorAll('th,td')].map(c => c.innerText.trim())));
  return JSON.stringify({url: location.href, title: document.title,
    ready: document.readyState, len: text.length,
    text: text.slice(0, 80000), tables: tables.slice(0, 60)});
})()
"""


def cmd(action, args, timeout=90):
    body = json.dumps({"action": action, "args": args, "session": SESSION}).encode()
    req = urllib.request.Request(DAEMON, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def evaluate(code, timeout=90):
    out = cmd("evaluate", {"code": code}, timeout)
    if not out.get("ok"):
        return None
    val = (out.get("data") or {}).get("value")
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return val
    return val


summary = []
for url in URLS:
    # 1. navigate (page-load timeout is normal for this SPA)
    try:
        nav = cmd("navigate", {"url": url, "newTab": True}, timeout=45)
        print('nav:', json.dumps(nav)[:160])
    except Exception as e:
        print('nav timeout/err (expected):', repr(e)[:120])
    # 2. wait, then poll evaluate until content appears (max ~40s)
    time.sleep(8)
    data = None
    for i in range(8):
        try:
            data = evaluate(EXTRACT)
        except Exception as e:
            print('eval err:', repr(e)[:120])
            data = None
        if isinstance(data, dict) and data.get('len', 0) > 120:
            break
        time.sleep(4)
    if not isinstance(data, dict):
        data = {"url": url, "error": "no content extracted", "text": "", "tables": []}
        status = 0
    else:
        status = 200
    payload = {"text": data.get("text", ""), "tables": data.get("tables", []),
               "title": data.get("title", ""), "final_url": data.get("url", url)}
    save_response(RUN_ID, 'account-site', url, status, payload)
    ntab = len(payload["tables"])
    summary.append((url, status, len(payload["text"]), ntab, payload["title"]))
    print(f'[{status}] {url}  text={len(payload["text"])} chars, tables={ntab}, title={payload["title"]!r}')
    time.sleep(1)

# refresh run notes (our own run row only)
ok = sum(1 for s in summary if s[1] == 200)
finish_run(RUN_ID, 'ok' if ok == len(URLS) else 'partial',
           f'sectionA calls=13 ok=13; sectionB pages={ok}/{len(URLS)}')
print('SUMMARY')
for s in summary:
    print(s)
