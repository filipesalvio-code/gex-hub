#!/usr/bin/env python3
"""mcp.json guard — self-healing registration for the menthorq MCP server.

Ensures `mcpServers.menthorq` exists in Kimi's mcp.json. Idempotent and
MERGE-only: reads the file, adds/updates just the menthorq key, writes back,
never touches other entries. Safe to run anytime (session start, watcher,
cron). Keeps file mode 600.

Usage:
  python3 mcp_guard.py           # ensure entry exists; silent if already OK
  python3 mcp_guard.py --status  # print current state, change nothing
"""
import json
import os
import stat
import sys

MCP_JSON = ("/Users/filipesalvio/Library/Application Support/kimi-desktop/"
            "daimon-share/daimon/runtime/kimi-code/home/mcp.json")

MENTHORQ_ENTRY = {
    "command": ("/Users/filipesalvio/Library/Application Support/kimi-desktop/"
                "daimon-share/daimon/runtime/python/.venv/bin/python3"),
    "args": ["/Users/filipesalvio/gex-hub/mcp/menthorq_mcp.py"],
    "env": {"MENTHORQ_BRIDGE_SESSION": "menthorq-scrape"},
}

SPOTGAMMA_ENTRY = {
    "command": "/Applications/Kimi.app/Contents/Resources/resources/runtime/node",
    "args": ["/Users/filipesalvio/gex-hub/spotgamma-mcp/server.js"],
}

SYNERGI_ENTRY = {
    "command": ("/Users/filipesalvio/Library/Application Support/kimi-desktop/"
                "daimon-share/daimon/runtime/python/.venv/bin/python3"),
    "args": ["/Users/filipesalvio/Documents/Kimi/Workspaces/APIs/mcp/synergi_mcp.py"],
}

PROTECTED_KEYS = ("menthorq", "spotgamma", "synergi")


def ensure(servers, key, desired, preserve_env=False):
    """Ensure servers[key] matches desired. Returns a change label or None.

    With preserve_env, an existing `env` block (e.g. a live user token) is
    carried over untouched; only command/args are repaired.
    """
    current = servers.get(key)
    if current is None:
        servers[key] = dict(desired)
        return "restored"
    repaired = dict(desired)
    if preserve_env and current.get("env"):
        repaired["env"] = current["env"]
    if current != repaired:
        servers[key] = repaired
        return "repaired"
    return None


def main() -> int:
    status_only = "--status" in sys.argv
    try:
        with open(MCP_JSON) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        cfg = {}
    except json.JSONDecodeError:
        backup = MCP_JSON + f".corrupt-{int(os.path.getmtime(MCP_JSON))}"
        os.replace(MCP_JSON, backup)
        print(f"mcp.json was corrupt; moved aside to {backup}")
        cfg = {}

    servers = cfg.setdefault("mcpServers", {})
    if status_only:
        for key in PROTECTED_KEYS:
            cur = servers.get(key)
            tok = bool((cur or {}).get("env", {}).get("SPOTGAMMA_SG_TOKEN"))
            print(f"{key}: {'registered' if cur else 'missing'}"
                  + (" (with user token)" if tok else ""))
        print("other servers:", sorted(k for k in servers
                                     if k not in PROTECTED_KEYS))
        return 0

    changes = {k: v for k, v in {
        "menthorq": ensure(servers, "menthorq", MENTHORQ_ENTRY),
        "spotgamma": ensure(servers, "spotgamma", SPOTGAMMA_ENTRY,
                            preserve_env=True),
        "synergi": ensure(servers, "synergi", SYNERGI_ENTRY,
                          preserve_env=True),
    }.items() if v}

    if not changes:
        return 0  # fully idempotent — no rewrite, no watcher churn

    tmp = MCP_JSON + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, MCP_JSON)  # atomic: no half-written file on crash
    print(f"mcp.json guard: {changes}; other entries preserved: "
          f"{sorted(k for k in servers if k not in changes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
