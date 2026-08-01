#!/usr/bin/env python3
"""Exhaustive test of every menthorq MCP tool, launched via the exact
command/args registered in Kimi's mcp.json (simulates what Kimi spawns)."""
import json
import subprocess

MCP_JSON = ("/Users/filipesalvio/Library/Application Support/kimi-desktop/"
            "daimon-share/daimon/runtime/kimi-code/home/mcp.json")

CALLS = [
    ("menthorq_tickers", {}),
    ("menthorq_prices", {"tickers": "SPX,SPY,QQQ"}),
    ("menthorq_market_status", {"exchange": "NYSE"}),
    ("menthorq_gamma_levels", {"ticker": "SPX", "frequency": "eod"}),
    ("menthorq_gamma_levels", {"ticker": "TSLA", "frequency": "intraday"}),
    ("menthorq_gamma_insights", {"ticker": "SPY", "limit": 5}),
    ("menthorq_gamma_insights_expirations", {"ticker": "QQQ", "frequency": "eod"}),
    ("menthorq_metrics_eod", {"ticker": "NVDA", "fields": ["option", "volatility"], "limit": 5}),
    ("menthorq_metrics_intraday", {"ticker": "SPX", "fields": ["iv_1m_50d", "skew_1m"], "limit": 3}),
    ("menthorq_options_matrix", {"ticker": "AAPL", "frequency": "eod"}),
    ("menthorq_put_call_ratio", {"ticker": "SPY", "frequency": "intraday"}),
    ("menthorq_dealer_positioning", {"ticker": "NVDA"}),
    ("menthorq_volatility_insights", {"ticker": "SPX"}),
    ("menthorq_candles", {"ticker": "SPX", "interval": "15m", "count_back": 20}),
    ("menthorq_tradingview", {"ticker": "SPX"}),
    ("menthorq_screener_columns", {}),
    ("menthorq_screener", {"tickers": "SPX,NVDA", "columns": "name,sector,market_cap"}),
    ("menthorq_qbot_assets", {}),
    ("menthorq_events", {"ticker": "AAPL", "start_date": "2026-07-11", "end_date": "2026-07-25"}),
    ("menthorq_company_news", {"ticker": "AAPL", "date": "2026-07-25", "number": 3}),
    ("menthorq_user_me", {}),
    ("menthorq_watchlists", {}),
    ("menthorq_chats", {}),
    ("menthorq_screener_templates", {}),
    ("menthorq_chat_templates", {}),
]


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
    return json.loads(proc.stdout.readline())


def main():
    cfg = json.load(open(MCP_JSON))["mcpServers"]["menthorq"]
    print(f"launching via mcp.json: {cfg['command']} {cfg['args'][0].split('/')[-1]}")
    proc = subprocess.Popen([cfg["command"]] + cfg["args"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True,
                            env={**__import__("os").environ, **cfg.get("env", {})})
    passed = failed = 0
    try:
        r = rpc(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                     "clientInfo": {"name": "full-test", "version": "1"}}, 1)
        assert r["result"]["serverInfo"]["name"] == "menthorq-mcp"
        rpc(proc, "notifications/initialized", is_notification=True)
        r = rpc(proc, "tools/list", msg_id=2)
        tools = {t["name"] for t in r["result"]["tools"]}
        missing = {c[0] for c in CALLS} - tools
        assert not missing, f"tools missing from server: {missing}"
        print(f"handshake OK, {len(tools)} tools advertised\n")

        for i, (name, args) in enumerate(CALLS, start=10):
            r = rpc(proc, "tools/call", {"name": name, "arguments": args}, i)
            try:
                content = r["result"]["content"][0]["text"]
                payload = json.loads(content)
                status = payload["http_status"]
                is_err = r["result"].get("isError", False)
                data = payload["data"]
                n = len(content)
                shape = (f"list[{len(data)}]" if isinstance(data, list)
                         else f"dict[{len(data)}]" if isinstance(data, dict) else type(data).__name__)
                ok = status == 200 and not is_err
                passed += ok
                failed += not ok
                print(f"  {'PASS' if ok else 'FAIL'} {name:<40} http={status} {shape} {n}B")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"  FAIL {name:<40} malformed result: {str(r)[:200]} ({e})")
        print(f"\n{passed} passed, {failed} failed out of {len(CALLS)} calls")
        print("RESULT:", "ALL TOOLS OK" if failed == 0 else "FAILURES PRESENT")
    finally:
        proc.kill()
        err = proc.stderr.read().strip()
        if err:
            print("--- server stderr ---")
            print(err[-1500:])


if __name__ == "__main__":
    main()
