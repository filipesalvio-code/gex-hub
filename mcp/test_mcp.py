#!/usr/bin/env python3
"""Smoke-test menthorq_mcp.py over stdio JSON-RPC."""
import json
import subprocess
import sys

SERVER = [sys.executable, "mcp/menthorq_mcp.py"]


def rpc(proc, method, params=None, msg_id=None, is_notification=False):
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    if not is_notification:
        msg["id"] = msg_id
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    if is_notification:
        return None
    line = proc.stdout.readline()
    return json.loads(line)


def main():
    proc = subprocess.Popen(SERVER, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, cwd=".")
    try:
        r = rpc(proc, "initialize", {"protocolVersion": "2024-11-05",
                                     "capabilities": {},
                                     "clientInfo": {"name": "smoke-test", "version": "0.1"}}, 1)
        srv = r["result"]["serverInfo"]
        print(f"initialize OK -> {srv['name']} v{srv['version']}")

        rpc(proc, "notifications/initialized", is_notification=True)

        r = rpc(proc, "tools/list", msg_id=2)
        tools = r["result"]["tools"]
        print(f"tools/list OK -> {len(tools)} tools")
        names = [t["name"] for t in tools]
        assert len(names) == len(set(names)), "duplicate tool names!"

        calls = [
            ("menthorq_gamma_levels", {"ticker": "SPX", "frequency": "eod"}),
            ("menthorq_metrics_intraday", {"ticker": "SPX", "fields": ["iv_1m_50d", "skew_1m"], "limit": 3}),
            ("menthorq_dealer_positioning", {"ticker": "NVDA"}),
            ("menthorq_market_status", {"exchange": "NYSE"}),
            ("menthorq_put_call_ratio", {"ticker": "SPY", "frequency": "intraday"}),
        ]
        mid = 10
        for name, args in calls:
            r = rpc(proc, "tools/call", {"name": name, "arguments": args}, mid)
            mid += 1
            content = r["result"]["content"][0]["text"]
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                raise AssertionError(f"{name} returned non-JSON content: {content[:300]}")
            status = payload["http_status"]
            is_err = r["result"].get("isError")
            data = payload["data"]
            size = len(content)
            keys = list(data.keys())[:6] if isinstance(data, dict) else f"list[{len(data)}]"
            print(f"  {name}: http={status} isError={is_err} bytes={size} keys={keys}")
            assert status == 200 and not is_err, f"{name} failed: {content[:200]}"

        # unknown tool -> JSON-RPC error, server stays alive
        r = rpc(proc, "tools/call", {"name": "nope", "arguments": {}}, 99)
        assert "error" in r and r["error"]["code"] == -32602
        r = rpc(proc, "ping", msg_id=100)
        assert r["result"] == {}
        print("error handling + ping OK")
        print("ALL SMOKE TESTS PASSED")
    finally:
        proc.kill()
        err = proc.stderr.read()
        if err.strip():
            print("--- server stderr ---")
            print(err[-2000:])


if __name__ == "__main__":
    main()
