#!/usr/bin/env python3
"""SpotGamma token refresh — captures localStorage["sgToken"] from the owner's
Chrome via Kimi WebBridge and merges it into mcp.json (SPOTGAMMA_SG_TOKEN).

Designed for unattended runs (LaunchAgent, daily):
- Reuses an existing dashboard.spotgamma.com tab when one is open;
  opens (and later reuses) a single tab otherwise.
- Chrome closed / not logged in / token absent -> exit 2 with a quiet message;
  the next scheduled run retries. The sgToken JWT lives ~3 days, so a missed
  day is harmless.
- MERGE-only, atomic write, keeps mcp.json mode 600. Never touches other keys.

Exit codes: 0 = token refreshed (or already fresh), 2 = could not capture.
"""
import base64
import json
import os
import stat
import sys
import time
import urllib.request

BRIDGE = "http://127.0.0.1:10086/command"
SESSION = "spotgamma-scrape"
DASH = "https://dashboard.spotgamma.com"
MCP_JSON = ("/Users/filipesalvio/Library/Application Support/kimi-desktop/"
            "daimon-share/daimon/runtime/kimi-code/home/mcp.json")


def bridge(action, args, timeout=60):
    body = json.dumps({"action": action, "args": args, "session": SESSION}).encode()
    req = urllib.request.Request(BRIDGE, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def capture_token():
    """Return (token, error_message)."""
    probe = ("(()=>{if(!location.href.startsWith('" + DASH + "'))"
             "return JSON.stringify({state:'wrong_tab'});"
             "const t=localStorage.getItem('sgToken');"
             "return JSON.stringify({state:t?'ok':'no_token',token:t})})()")
    # 1) reuse an existing dashboard tab if present
    try:
        tabs = (bridge("list_tabs", {}).get("data") or {}).get("tabs") or []
        dash = next((t for t in tabs if str(t.get("url", "")).startswith(DASH)), None)
        if dash:
            bridge("find_tab", {"url": dash["url"]})
            out = bridge("evaluate", {"code": probe})
            val = (out.get("data") or {}).get("value") or ""
            try:
                p = json.loads(val)
            except json.JSONDecodeError:
                p = {"state": "error"}
            if p.get("state") == "ok" and p.get("token"):
                return p["token"], None
            if p.get("state") == "no_token":
                return None, "dashboard open but sgToken absent — user not logged in"
    except Exception:
        pass
    # 2) open a tab (fails quietly when Chrome has no window)
    try:
        nav = bridge("navigate", {"url": DASH + "/home", "newTab": True,
                                  "group_title": "SpotGamma token"}, timeout=90)
        if not nav.get("ok"):
            return None, ("cannot open tab (Chrome window closed?): "
                          + str((nav.get("error") or {}).get("message", nav)))
    except Exception as e:
        return None, f"cannot open tab (Chrome window closed?): {e!r}"
    time.sleep(8)
    try:
        out = bridge("evaluate", {"code": probe})
        val = (out.get("data") or {}).get("value") or ""
        p = json.loads(val) if val else {"state": "error"}
    except Exception as e:
        return None, f"probe failed: {e!r}"
    if p.get("state") == "ok" and p.get("token"):
        return p["token"], None
    if p.get("state") == "no_token":
        return None, "tab opened but sgToken absent — user not logged in"
    return None, f"probe state: {p.get('state', 'error')}"


def jwt_expiry(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload))["exp"]
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(exp))
    except Exception:
        return "unknown"


def merge_token(token):
    with open(MCP_JSON) as f:
        cfg = json.load(f)
    srv = cfg.setdefault("mcpServers", {}).setdefault("spotgamma", {
        "command": "/Applications/Kimi.app/Contents/Resources/resources/runtime/node",
        "args": ["/Users/filipesalvio/gex-hub/spotgamma-mcp/server.js"],
    })
    old = srv.get("env", {}).get("SPOTGAMMA_SG_TOKEN")
    if old == token:
        return False
    srv.setdefault("env", {})["SPOTGAMMA_SG_TOKEN"] = token
    tmp = MCP_JSON + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, MCP_JSON)
    return True


def main():
    token, err = capture_token()
    if not token:
        print(f"token refresh skipped: {err}")
        return 2
    changed = merge_token(token)
    print(f"token {'refreshed' if changed else 'already current'}; "
          f"JWT expires {jwt_expiry(token)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
