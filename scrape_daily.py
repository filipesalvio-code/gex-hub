import json
import requests
import time
import sys
import sqlite3
from pathlib import Path

SESSION = "spotgamma-daily"
BASE = "https://dashboard.spotgamma.com"
DB_PATH = Path("spotgamma.db").resolve()

def wb(action, args):
    r = requests.post(
        "http://127.0.0.1:10086/command",
        headers={"Content-Type": "application/json"},
        json={"action": action, "args": args, "session": SESSION},
        timeout=60
    )
    return r.json()

def wait(ms=7000):
    time.sleep(ms / 1000)

def eval_js(code):
    resp = wb("evaluate", {"code": code})
    if resp.get("ok"):
        val = resp.get("data", {}).get("value", "null")
        try:
            return json.loads(val)
        except Exception:
            return val
    return {"_error": resp.get("error", {})}

# Start DB run
sys.path.insert(0, "scraper")
from db_writer import start_run, save_snapshot, finish_run
run_id = start_run("sg-daily", BASE)
print(f"Run ID: {run_id}")

# --- PAGE 1: HOME ---
print("Navigating to home...")
nav = wb("navigate", {"url": f"{BASE}/home", "newTab": True, "group_title": "SpotGamma daily"})
print("Home nav:", nav)
wait(8000)

# Extract home data
home_js = """
(() => {
  const data = {url: location.href, title: document.title, asOfDate: null, indices: {}, events: []};
  const allText = document.body.innerText;
  const dm = allText.match(/as of ([A-Za-z]+ \\d{1,2},? \\d{4})/i) || allText.match(/(\\d{4}-\\d{2}-\\d{2})/);
  if (dm) data.asOfDate = dm[0];
  // Find all tables
  document.querySelectorAll('table').forEach(t => {
    const caption = t.closest('section, div[class*="card"], div[class*="panel"]')?.querySelector('h2, h3, h4, h5, .title, [class*="header"]')?.textContent?.trim() || '';
    const headers = Array.from(t.querySelectorAll('thead th, tr:first-child th, tr:first-child td')).map(th => th.textContent.trim());
    const rows = Array.from(t.querySelectorAll('tbody tr, tr')).slice(1).map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim()));
    const idxMatch = caption.match(/(SPX|SPY|NDX|QQQ|RUT|IWM)/);
    if (idxMatch || headers.some(h => /Level|Strike|Gamma|Wall|Trigger|Combo/i.test(h))) {
      const sym = idxMatch ? idxMatch[1] : (headers[0] || 'unknown');
      if (!data.indices[sym]) data.indices[sym] = [];
      data.indices[sym].push({caption, headers, rows});
    } else if (headers.some(h => /Event|Time|Calendar/i.test(h)) || rows.some(r => r.some(c => /Fed|PCE|GDP|PMI|NFP|Consumer|Durable|Goods|Conference|Press/i.test(c)))) {
      data.events.push({caption, headers, rows});
    }
  });
  // Fallback: scan all rows for level-like data
  if (Object.keys(data.indices).length === 0) {
    const allRows = [];
    document.querySelectorAll('tr, [class*="row"]').forEach(r => {
      const cells = Array.from(r.querySelectorAll('td, [class*="cell"]')).map(c => c.textContent.trim()).filter(Boolean);
      if (cells.length >= 2 && cells.some(c => /\\d{4,}/.test(c))) allRows.push(cells);
    });
    data._allRows = allRows;
  }
  // Events fallback
  if (data.events.length === 0) {
    const evs = [];
    document.querySelectorAll('p, div, li').forEach(el => {
      const txt = el.textContent.trim();
      const m = txt.match(/^([A-Za-z]+ \\d{1,2}-\\d{2})\\s+(\\d{1,2}:\\d{2}\\s*(?:am|pm)?\\s*(?:EDT|EST)?)\\s*(.+)$/i);
      if (m && /Fed|PCE|GDP|PMI|NFP|Consumer|Durable|Goods|Conference|Press/i.test(txt)) {
        evs.push({date: m[1], time: m[2], title: m[3]});
      }
    });
    data.events = evs;
  }
  return JSON.stringify(data);
})()
"""
home_data = eval_js(home_js)
print("Home data keys:", list(home_data.keys()) if isinstance(home_data, dict) else type(home_data))
save_snapshot(run_id, home_data.get("url", f"{BASE}/home"), "market-overview", home_data)

# --- PAGE 2: EQUITY HUB SPX ---
print("Navigating to equity hub SPX...")
wb("navigate", {"url": f"{BASE}/equityhub?sym=SPX"})
wait(8000)

eh_js = """
(() => {
  const data = {url: location.href, title: document.title, metrics: {}, history: []};
  document.querySelectorAll('[class*="metric"], [class*="stat"], [class*="card"]').forEach(el => {
    const label = el.querySelector('[class*="label"], [class*="title"], h3, h4, h5, h6')?.textContent?.trim();
    const value = el.querySelector('[class*="value"], [class*="number"], [class*="big"], span, p')?.textContent?.trim();
    if (label && value) data.metrics[label] = value;
  });
  const allText = document.body.innerText;
  const dm = allText.match(/as of ([A-Za-z]+ \\d{1,2},? \\d{4})/i) || allText.match(/(\\d{4}-\\d{2}-\\d{2})/);
  if (dm) data.asOfDate = dm[0];
  // History table
  document.querySelectorAll('table').forEach(t => {
    const headers = Array.from(t.querySelectorAll('thead th, tr:first-child th, tr:first-child td')).map(th => th.textContent.trim());
    const rows = Array.from(t.querySelectorAll('tbody tr, tr')).slice(1).map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim()));
    if (headers.length > 1) data.history.push({headers, rows});
  });
  return JSON.stringify(data);
})()
"""
eh_data = eval_js(eh_js)
save_snapshot(run_id, eh_data.get("url", f"{BASE}/equityhub?sym=SPX"), "equityhub-spx", eh_data)

# --- PAGE 3: HIRO SPX ---
print("Navigating to HIRO SPX...")
wb("navigate", {"url": f"{BASE}/hiro?sym=SPX"})
wait(8000)

hiro_js = """
(() => {
  const data = {url: location.href, title: document.title, metrics: {}, levels: {}, flow: []};
  const allText = document.body.innerText;
  const dm = allText.match(/as of ([A-Za-z]+ \\d{1,2},? \\d{4})/i) || allText.match(/(\\d{4}-\\d{2}-\\d{2})/);
  if (dm) data.asOfDate = dm[0];
  // Metric panels
  document.querySelectorAll('[class*="metric"], [class*="stat"], [class*="panel"]').forEach(el => {
    const label = el.querySelector('[class*="label"], [class*="title"], h3, h4, h5, h6')?.textContent?.trim();
    const value = el.querySelector('[class*="value"], [class*="number"], [class*="big"], span, p')?.textContent?.trim();
    if (label && value) data.metrics[label] = value;
  });
  // Levels
  document.querySelectorAll('table').forEach(t => {
    const headers = Array.from(t.querySelectorAll('thead th, tr:first-child th, tr:first-child td')).map(th => th.textContent.trim());
    const rows = Array.from(t.querySelectorAll('tbody tr, tr')).slice(1).map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim()));
    if (rows.some(r => r.some(c => /Wall|Hedge|Gamma|Delta/i.test(c)))) {
      data.levels = {headers, rows};
    } else if (rows.some(r => r.some(c => /\\$|K|M|B|Call|Put|Strike|Expiry/i.test(c)))) {
      data.flow.push({headers, rows});
    }
  });
  return JSON.stringify(data);
})()
"""
hiro_data = eval_js(hiro_js)
save_snapshot(run_id, hiro_data.get("url", f"{BASE}/hiro?sym=SPX"), "hiro-spx", hiro_data)

# --- PAGE 4: IVOL ---
print("Navigating to Volatility Dashboard...")
wb("navigate", {"url": f"{BASE}/ivol"})
wait(8000)

ivol_js = """
(() => {
  const data = {url: location.href, title: document.title, overview: {}, termStructure: [], skew: {}};
  const allText = document.body.innerText;
  const dm = allText.match(/as of ([A-Za-z]+ \\d{1,2},? \\d{4})/i) || allText.match(/(\\d{4}-\\d{2}-\\d{2})/);
  if (dm) data.asOfDate = dm[0];
  // Look for Z-score and key metrics
  const zMatch = allText.match(/Z-Score[\\s:]*([\\d.]+)/i);
  if (zMatch) data.overview.zScore = zMatch[1];
  const ivMatch = allText.match(/ATM IV[\\s:]*([\\d.]+%?)/i);
  if (ivMatch) data.skew.atmIV = ivMatch[1];
  const priceMatch = allText.match(/SPX[\\s:]*([\\d,]+)/i);
  if (priceMatch) data.overview.spxPrice = priceMatch[1];
  // Term structure from text or tables
  document.querySelectorAll('table').forEach(t => {
    const headers = Array.from(t.querySelectorAll('thead th, tr:first-child th, tr:first-child td')).map(th => th.textContent.trim());
    const rows = Array.from(t.querySelectorAll('tbody tr, tr')).slice(1).map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim()));
    if (headers.some(h => /Date|Expiry|IV|Vol/i.test(h))) {
      data.termStructure.push({headers, rows});
    }
  });
  data._allText = allText.slice(0, 5000);
  return JSON.stringify(data);
})()
"""
ivol_data = eval_js(ivol_js)
save_snapshot(run_id, ivol_data.get("url", f"{BASE}/ivol"), "volatility-dashboard", ivol_data)

# --- PAGE 5: TAPE ---
print("Navigating to Tape...")
wb("navigate", {"url": f"{BASE}/tape"})
wait(8000)

tape_js = """
(() => {
  const data = {url: location.href, title: document.title, summary: {}, tables: [], prints: []};
  const allText = document.body.innerText;
  const dm = allText.match(/as of ([A-Za-z]+ \\d{1,2},? \\d{4})/i) || allText.match(/(\\d{4}-\\d{2}-\\d{2})/);
  if (dm) data.asOfDate = dm[0];
  document.querySelectorAll('table').forEach(t => {
    const headers = Array.from(t.querySelectorAll('thead th, tr:first-child th, tr:first-child td')).map(th => th.textContent.trim());
    const rows = Array.from(t.querySelectorAll('tbody tr, tr')).slice(1).map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim()));
    if (rows.some(r => r.some(c => /\\$|K|M|B|Call|Put|Strike|Expiry|Premium/i.test(c)))) {
      data.tables.push({headers, rows});
    }
  });
  data._allText = allText.slice(0, 5000);
  return JSON.stringify(data);
})()
"""
tape_data = eval_js(tape_js)
save_snapshot(run_id, tape_data.get("url", f"{BASE}/tape"), "tape", tape_data)

# --- PAGE 6: SCANNERS ---
print("Navigating to Scanners...")
wb("navigate", {"url": f"{BASE}/scanners"})
wait(8000)

scan_js = """
(() => {
  const data = {url: location.href, title: document.title, scanners: []};
  const allText = document.body.innerText;
  const dm = allText.match(/as of ([A-Za-z]+ \\d{1,2},? \\d{4})/i) || allText.match(/(\\d{4}-\\d{2}-\\d{2})/);
  if (dm) data.asOfDate = dm[0];
  document.querySelectorAll('table').forEach(t => {
    const headers = Array.from(t.querySelectorAll('thead th, tr:first-child th, tr:first-child td')).map(th => th.textContent.trim());
    const rows = Array.from(t.querySelectorAll('tbody tr, tr')).slice(1).map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim())).filter(r => r.some(Boolean));
    if (rows.length > 0) data.scanners.push({headers, rows: rows.slice(0, 5)});
  });
  data._allText = allText.slice(0, 5000);
  return JSON.stringify(data);
})()
"""
scan_data = eval_js(scan_js)
save_snapshot(run_id, scan_data.get("url", f"{BASE}/scanners"), "scanners", scan_data)

# --- PAGE 7: FOUNDERS NOTES ---
print("Navigating to Founders Notes...")
wb("navigate", {"url": f"{BASE}/foundersNotes"})
wait(8000)

fn_js = """
(() => {
  const data = {url: location.href, title: document.title, notes: []};
  const allText = document.body.innerText;
  const dm = allText.match(/as of ([A-Za-z]+ \\d{1,2},? \\d{4})/i) || allText.match(/(\\d{4}-\\d{2}-\\d{2})/);
  if (dm) data.asOfDate = dm[0];
  // Look for note titles and key levels
  document.querySelectorAll('h1, h2, h3, h4, h5, h6, [class*="title"]').forEach(el => {
    const txt = el.textContent.trim();
    if (/Founder|Note|Report|Morning|Evening|PM|AM/i.test(txt)) {
      data.notes.push({type: 'title', text: txt});
    }
  });
  // Look for resistance/pivot/support
  const rpMatch = allText.match(/Resistance[\\s:]*([\\d.,\s]+)/i);
  if (rpMatch) data.resistance = rpMatch[1];
  const pvMatch = allText.match(/Pivot[\\s:]*([\\d.,\s]+)/i);
  if (pvMatch) data.pivot = pvMatch[1];
  const suMatch = allText.match(/Support[\\s:]*([\\d.,\s]+)/i);
  if (suMatch) data.support = suMatch[1];
  data._allText = allText.slice(0, 5000);
  return JSON.stringify(data);
})()
"""
fn_data = eval_js(fn_js)
save_snapshot(run_id, fn_data.get("url", f"{BASE}/foundersNotes"), "founders-notes", fn_data)

# Finish run
finish_run(run_id, "ok", f"pages=7,run_id={run_id}")
print(f"Run {run_id} finished.")
