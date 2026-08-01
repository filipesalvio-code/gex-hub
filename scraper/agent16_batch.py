#!/usr/bin/env python3
"""sg-agent-16: fire select (ignore timeout), sleep, light capture."""
import json, sys, time, urllib.request

DAEMON = "http://127.0.0.1:10086/command"
SESSION = "spotgamma-scrape-16"

SELECT_JS = r"""
(async () => {
  const SCANNER = %s;
  const sleep = ms => new Promise(r=>setTimeout(r,ms));
  const sels=[...document.querySelectorAll(".MuiSelect-select")];
  sels[0].dispatchEvent(new MouseEvent("mousedown",{bubbles:true}));
  await sleep(500);
  const items=[...document.querySelectorAll(".MuiMenuItem-root")];
  for(const o of items){
    const cb=o.querySelector("input[type=checkbox]");
    const t=(o.innerText||"").trim();
    if(cb && cb.checked && !/History/.test(t)){ o.click(); await sleep(80); }
  }
  const target=[...document.querySelectorAll(".MuiMenuItem-root")].find(o=>(o.innerText||"").trim()===SCANNER);
  if(target){ target.click(); await sleep(200); }
  document.body.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));
  return JSON.stringify({ok:true});
})()
"""

CAPTURE_JS = r"""
(() => {
  const noEq=/No Equities Found/.test(document.body.innerText);
  const dots=document.querySelectorAll(".recharts-scatter path.recharts-symbols").length;
  const trs=[...document.querySelectorAll(".MuiPaper-root .MuiTableRow-root")];
  const rows=trs.map(tr=>[...tr.children].map(c=>(c.innerText||"").replace(/\s+/g," ").trim()))
    .filter(c=>c.length>=5&&c[1]&&c[1]!=="Symbol").map(c=>[c[1],c[2],c[3],c[4]]);
  return JSON.stringify({url:location.href.slice(0,700),noEq,dots,n:rows.length,rows});
})()
"""

def ev(code, timeout):
    payload = {"action": "evaluate", "args": {"code": code}, "session": SESSION}
    req = urllib.request.Request(DAEMON, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        outer = json.loads(r.read().decode())
    return json.loads(outer["data"]["value"])

if __name__ == "__main__":
    outfile = sys.argv[1]
    names = sys.argv[2:]
    out = {}
    for n in names:
        try:
            ev(SELECT_JS % json.dumps(n), 12)
        except Exception:
            pass  # response often lost on URL navigation; state still applies
        time.sleep(11)
        try:
            r = ev(CAPTURE_JS, 45)
        except Exception as e:
            r = {"err": str(e)}
        r["scanner"] = n
        out[n] = r
        print(f"{n}: n={r.get('n')} noEq={r.get('noEq')} dots={r.get('dots')} err={r.get('err')}", flush=True)
    with open(outfile, "w") as f:
        json.dump(out, f, indent=1)
    print("saved", outfile)
