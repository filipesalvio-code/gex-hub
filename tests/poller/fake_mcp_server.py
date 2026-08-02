"""Fake MCP stdio server: replays canned tool responses from FIXTURE env."""
import json
import os
import sys

FIXTURE = json.loads(os.environ.get("FAKE_MCP_FIXTURE", "{}"))
PROTOCOL = os.environ.get("FAKE_MCP_PROTOCOL", "2024-11-05")
NOTIFY = os.environ.get("FAKE_MCP_NOTIFY", "")

for line in sys.stdin:
    msg = json.loads(line)
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        if os.environ.get("FAKE_MCP_INIT_ERROR"):
            out = {"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32600, "message": "init rejected"}}
        else:
            out = {"jsonrpc": "2.0", "id": mid,
                   "result": {"protocolVersion": PROTOCOL, "capabilities": {},
                              "serverInfo": {"name": "fake", "version": "0.0"}}}
    elif method == "notifications/initialized":
        continue
    elif method == "ping":
        out = {"jsonrpc": "2.0", "id": mid, "result": {}}
    elif method == "tools/call":
        if NOTIFY:
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "method": NOTIFY, "params": {}}) + "\n")
        if os.environ.get("FAKE_MCP_WRONG_ID"):
            mid = mid + 1000
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
