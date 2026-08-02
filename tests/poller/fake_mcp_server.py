"""Fake MCP stdio server: replays canned tool responses from FIXTURE env."""
import json
import os
import sys

FIXTURE = json.loads(os.environ.get("FAKE_MCP_FIXTURE", "{}"))

for line in sys.stdin:
    msg = json.loads(line)
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        out = {"jsonrpc": "2.0", "id": mid,
               "result": {"protocolVersion": "2024-11-05", "capabilities": {},
                          "serverInfo": {"name": "fake", "version": "0.0"}}}
    elif method == "notifications/initialized":
        continue
    elif method == "ping":
        out = {"jsonrpc": "2.0", "id": mid, "result": {}}
    elif method == "tools/call":
        name = msg["params"]["name"]
        if name in FIXTURE:
            out = {"jsonrpc": "2.0", "id": mid, "result":
                   {"content": [{"type": "text", "text": FIXTURE[name]}], "isError": False}}
        else:
            out = {"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32602, "message": f"unknown tool: {name}"}}
    else:
        out = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "nope"}}
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()
