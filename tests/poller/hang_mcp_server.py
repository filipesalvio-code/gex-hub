"""Fake MCP server that answers the handshake then hangs on tools/call."""
import json
import sys
import time

for line in sys.stdin:
    msg = json.loads(line)
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        out = {"jsonrpc": "2.0", "id": mid,
               "result": {"protocolVersion": "2024-11-05", "capabilities": {},
                          "serverInfo": {"name": "hang", "version": "0.0"}}}
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()
    elif method == "notifications/initialized":
        continue
    else:
        time.sleep(120)
