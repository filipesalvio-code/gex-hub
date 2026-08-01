import json, requests, time, sys
sys.path.insert(0, "scraper")
from db_writer import save_snapshot

SESSION = "spotgamma-daily"
BASE = "https://dashboard.spotgamma.com"
RUN_ID = 24

def wb(action, args):
    r = requests.post(
        "http://127.0.0.1:10086/command",
        headers={"Content-Type": "application/json"},
        json={"action": action, "args": args, "session": SESSION},
        timeout=60
    )
    return r.json()

def eval_js(code):
    resp = wb("evaluate", {"code": code})
    if resp.get("ok"):
        val = resp.get("data", {}).get("value", "null")
        try:
            return json.loads(val)
        except Exception:
            return val
    return {"_error": resp.get("error", {})}

# --- Re-scrape Equity Hub SPX ---
print("Re-navigating to equity hub SPX...")
wb("navigate", {"url": f"{BASE}/equityhub?sym=SPX"})
time.sleep(10)

# Try clicking on History tab first
wb("evaluate", {"code": "(() => { const tabs = Array.from(document.querySelectorAll('button, [role=tab]')); const histTab = tabs.find(t => /History/i.test(t.textContent)); if (histTab) { histTab.click(); return 'clicked history'; } return 'no history tab'; })()"})
time.sleep(3)

eh_js = """
(() => {
  const data = {url: location.href, title: document.title, metrics: {}, history: [], gamma: [], allText: document.body.innerText.slice(0, 8000)};
  const allText = document.body.innerText;
  const dm = allText.match(/as of ([A-Za-z]+ \\d{1,2},? \\d{4})/i) || allText.match(/(\\d{4}-\\d{2}-\\d{2})/);
  if (dm) data.asOfDate = dm[0];
  // Extract all visible text blocks that look like metrics
  document.querySelectorAll('div, span, p').forEach(el => {
    const txt = el.textContent.trim();
    const m = txt.match(/^([A-Za-z\\s/]+)[\\s:]*([\\d.,\-]+[%$BKM]?)$/);
    if (m && m[1].length > 2 && m[1].length < 40) {
      data.metrics[m[1].trim()] = m[2].trim();
    }
  });
  // Tables
  document.querySelectorAll('table').forEach(t => {
    const headers = Array.from(t.querySelectorAll('thead th, tr:first-child th, tr:first-child td')).map(th => th.textContent.trim());
    const rows = Array.from(t.querySelectorAll('tbody tr, tr')).slice(1).map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim()));
    if (rows.some(r => r.some(c => /Gamma|Call|Put|gamma/i.test(c)))) {
      data.gamma.push({headers, rows});
    } else {
      data.history.push({headers, rows});
    }
  });
  return JSON.stringify(data);
})()
"""
eh_data = eval_js(eh_js)
print("Equity hub keys:", list(eh_data.keys()) if isinstance(eh_data, dict) else type(eh_data))
save_snapshot(RUN_ID, eh_data.get("url", f"{BASE}/equityhub?sym=SPX"), "equityhub-spx-v2", eh_data)

# --- Re-scrape HIRO SPX ---
print("Re-navigating to HIRO SPX...")
wb("navigate", {"url": f"{BASE}/hiro?sym=SPX"})
time.sleep(10)

hiro_js = """
(() => {
  const data = {url: location.href, title: document.title, metrics: {}, levels: {}, flow: [], allText: document.body.innerText.slice(0, 8000)};
  const allText = document.body.innerText;
  const dm = allText.match(/as of ([A-Za-z]+ \\d{1,2},? \\d{4})/i) || allText.match(/(\\d{4}-\\d{2}-\\d{2})/);
  if (dm) data.asOfDate = dm[0];
  // Look for big numbers and metrics
  document.querySelectorAll('div, span, p, h1, h2, h3, h4, h5, h6').forEach(el => {
    const txt = el.textContent.trim();
    const m = txt.match(/^([A-Za-z\\s/]+)[\\s:]*([\\d.,\-]+[%$BKM]?)$/);
    if (m && m[1].length > 2 && m[1].length < 40) {
      data.metrics[m[1].trim()] = m[2].trim();
    }
  });
  // HIRO specific patterns
  const hiroMatch = allText.match(/HIRO[\\s:]*([\\d.]+[BKM]?)/i);
  if (hiroMatch) data.metrics["HIRO"] = hiroMatch[1];
  const rangeMatch = allText.match(/([\-\\d.]+[BKM]?)\\s*to\\s*([\\d.]+[BKM]?)/i);
  if (rangeMatch) { data.metrics["rangeMin"] = rangeMatch[1]; data.metrics["rangeMax"] = rangeMatch[2]; }
  // Tables
  document.querySelectorAll('table').forEach(t => {
    const headers = Array.from(t.querySelectorAll('thead th, tr:first-child th, tr:first-child td')).map(th => th.textContent.trim());
    const rows = Array.from(t.querySelectorAll('tbody tr, tr')).slice(1).map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim()));
    if (rows.some(r => r.some(c => /Wall|Hedge|Gamma|Delta|Key/i.test(c)))) {
      data.levels = {headers, rows};
    } else if (rows.some(r => r.some(c => /\\$|K|M|B|Call|Put|Strike|Expiry|Side/i.test(c)))) {
      data.flow.push({headers, rows});
    }
  });
  return JSON.stringify(data);
})()
"""
hiro_data = eval_js(hiro_js)
print("HIRO keys:", list(hiro_data.keys()) if isinstance(hiro_data, dict) else type(hiro_data))
save_snapshot(RUN_ID, hiro_data.get("url", f"{BASE}/hiro?sym=SPX"), "hiro-spx-v2", hiro_data)

print("Done rescraping equityhub and hiro.")
