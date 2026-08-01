#!/usr/bin/env python3
"""sg-agent-16: iterate SpotGamma scanners, capture equity lists."""
import json, time, urllib.request

DAEMON = "http://127.0.0.1:10086/command"
SESSION = "spotgamma-scrape-16"

SCANNERS = [
    "Volatility Risk Premium", "Squeeze", "Reverse Volatility Risk Premium",
    "Highest Options Impact", "Earnings IV Crush", "Call Wall Increase",
    "Call Wall Decrease", "Put Wall Increase", "Put Wall Decrease",
    "Hedge Wall Increase", "Hedge Wall Decrease", "1% Margin of Hedge Wall",
    "IV Percent Change", "Sector ETFs", "Top Gamma % Expiring this Friday",
    "Top Delta % Expiring this Friday", "Cross Asset Summary",
]

JS = r"""
(async () => {
  const SCANNER = %s;
  const sleep = ms => new Promise(r=>setTimeout(r,ms));
  const sels=[...document.querySelectorAll(".MuiSelect-select")];
  sels[0].dispatchEvent(new MouseEvent("mousedown",{bubbles:true}));
  await sleep(700);
  const items=[...document.querySelectorAll(".MuiMenuItem-root")];
  for(const o of items){
    const cb=o.querySelector("input[type=checkbox]");
    const t=(o.innerText||"").trim();
    if(cb && cb.checked && !/History/.test(t)){ o.click(); await sleep(150); }
  }
  const target=[...document.querySelectorAll(".MuiMenuItem-root")].find(o=>(o.innerText||"").trim()===SCANNER);
  if(!target){ document.body.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true})); return JSON.stringify({err:"not in menu",scanner:SCANNER}); }
  target.click();
  await sleep(300);
  document.body.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));
  await sleep(4500);
  const noEq=/No Equities Found/.test(document.body.innerText);
  const dots=document.querySelectorAll(".recharts-scatter path.recharts-symbols").length;
  const paper=[...document.querySelectorAll(".MuiPaper-root")].find(p=>(p.innerText||"").includes("Actions"));
  const seen=new Map();
  const grab=()=>{ if(!paper) return; [...paper.querySelectorAll(".MuiTableRow-root")].forEach(tr=>{
    const tds=[...tr.querySelectorAll("td")].map(td=>(td.innerText||"").replace(/\s+/g," ").trim());
    if(tds.length>=4 && tds[0] && tds[0]!=="Symbol") seen.set(tds[0],tds.slice(0,4));
  });};
  if(paper){
    for(let i=0;i<9;i++){ grab(); paper.scrollTop=i*320; paper.dispatchEvent(new Event("scroll",{bubbles:true})); await sleep(260); }
    grab();
  }
  return JSON.stringify({scanner:SCANNER,noEq,dots,n:seen.size,rows:[...seen.values()]});
})()
"""

def ev(code, timeout=110):
    payload = {"action": "evaluate", "args": {"code": code}, "session": SESSION}
    req = urllib.request.Request(DAEMON, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        outer = json.loads(r.read().decode())
    return json.loads(outer["data"]["value"])

results = {}
for name in SCANNERS:
    code = JS % json.dumps(name)
    try:
        res = ev(code)
    except Exception as e:
        res = {"scanner": name, "err": str(e)}
    results[name] = res
    print(f"{name}: n={res.get('n')} noEq={res.get('noEq')} dots={res.get('dots')} err={res.get('err')}", flush=True)

with open("scraper/agent16_results.json", "w") as f:
    json.dump(results, f, indent=1)
print("saved scraper/agent16_results.json")
