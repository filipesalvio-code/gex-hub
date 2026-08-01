#!/usr/bin/env python3
"""Generate MCP_DOCS.md: full MenthorQ MCP documentation with real SPX examples.

Tool schemas are imported from menthorq_mcp.py (single source of truth).
Example responses come from the scrape archive (menthorq.db), trimmed for
readability; personal data (user profile, chat titles) is redacted.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcp"))
import menthorq_mcp

DB = ROOT / "menthorq.db"
OUT = ROOT / "mcp" / "MCP_DOCS.md"


# ------------------------------------------------------------ db examples
def fetch_example(url_like, status=200):
    con = sqlite3.connect(DB)
    row = con.execute(
        "SELECT payload_json FROM raw_responses WHERE url LIKE ? AND http_status=? "
        "ORDER BY id DESC LIMIT 1", (url_like, status)).fetchone()
    con.close()
    return json.loads(row[0]) if row else None


def trim(obj, depth=0, max_items=2, max_keys=8, max_str=140):
    if isinstance(obj, dict):
        items = list(obj.items())
        out = {}
        for k, v in items[:max_keys]:
            out[k] = trim(v, depth + 1, max_items, max_keys, max_str)
        if len(items) > max_keys:
            out["…"] = f"(+{len(items) - max_keys} more keys)"
        return out
    if isinstance(obj, list):
        out = [trim(v, depth + 1, max_items, max_keys, max_str) for v in obj[:max_items]]
        if len(obj) > max_items:
            out.append(f"… (+{len(obj) - max_items} more items)")
        return out
    if isinstance(obj, str) and len(obj) > max_str:
        return obj[:max_str] + "…"
    return obj


def redact_strings(obj, keep_keys=(), redact_keys=None):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if redact_keys and k in redact_keys or isinstance(v, str) and k not in keep_keys:
                out[k] = "«redacted»"
            else:
                out[k] = redact_strings(v, keep_keys, redact_keys)
        return out
    if isinstance(obj, list):
        return [redact_strings(v, keep_keys, redact_keys) for v in obj]
    return obj


# ------------------------------------------------------------ tool metadata
INFO = {
 "menthorq_tickers": {
   "endpoint": "clickhouse-api GET /api/web/v1/tickers",
   "why": "Discover every instrument the platform covers — stocks, ETFs and futures (with contract chains). Use it to resolve provider-specific ticker formats such as `DATABENTO#ES`.",
   "db": ("%/clickhouse-api/api/web/v1/tickers", {}),
   "note": "The full list has 1,256 entries and weighs ~300 KB; the example shows one futures entry."},
 "menthorq_prices": {
   "endpoint": "clickhouse-api GET /api/web/v1/prices?tickers={csv}",
   "why": "Quick price snapshot (current, open, high, low, previous close) for one or many tickers in a single batched call.",
   "db": ("%/prices?tickers=SPX%", {"max_items": 3})},
 "menthorq_market_status": {
   "endpoint": "clickhouse-api GET /api/web/v1/market-status/{exchange}",
   "why": "Check whether a venue is open before polling intraday data; returns session times in UTC and local time plus the next open date.",
   "db": ("%/market-status/NYSE", {}),
   "note": "Only NYSE and NASDAQ are supported upstream; other exchanges return 404."},
 "menthorq_gamma_levels": {
   "endpoint": "clickhouse-api GET /api/web/v1/gamma-levels/{ticker}/{frequency}",
   "why": "The flagship MenthorQ levels: ten GEX strikes, call resistance / put support (incl. 0DTE variants), gamma wall, HVL (high-volatility level) and the 1-day expected move band. `eod` = previous close snapshot, `intraday` = latest 15-min update.",
   "db": ("%/gamma-levels/SPX/eod", {})},
 "menthorq_gamma_insights": {
   "endpoint": "clickhouse-api GET /api/web/v1/gamma-insights/{ticker}?limit={n}",
   "why": "Per-expiration gamma positioning — GEX value and its 1-year percentile for each of the nearest expirations.",
   "db": ("%/gamma-insights/SPX?limit%", {"max_items": 2})},
 "menthorq_gamma_insights_expirations": {
   "endpoint": "clickhouse-api GET /api/web/v1/gamma-insights/{ticker}/expirations?frequency={f}",
   "why": "The full expiration ladder for a ticker (SPX has 50+), each with GEX and percentile — the input for term-structure analysis.",
   "db": ("%/gamma-insights/SPX/expirations%", {"max_items": 2})},
 "menthorq_metrics_eod": {
   "endpoint": "clickhouse-api GET /api/web/v1/metrics/{ticker}/eod?fields=…&limit={n}",
   "why": "Daily history (default 30 rows) of four metric families: `option` (GEX/DEX positioning), `momentum`, `volatility`, `seasonality`.",
   "db": ("%/metrics/SPX/eod%fields=option%", {"max_items": 1})},
 "menthorq_metrics_intraday": {
   "endpoint": "clickhouse-api GET /api/web/v1/metrics/{ticker}/intraday?fields=…&limit={n}",
   "why": "30-minute-bar IV and skew series. Only these literal fields are accepted: `iv_1m_50d`, `iv_3m_50d`, `iv_0dte_50d`, `skew_1m`, `skew_3m`, `skew_0dte` — the family aliases used by `metrics_eod` return HTTP 422 here.",
   "db": ("%/metrics/SPX/intraday%fields=iv_1m_50d%", {"max_items": 2}),
   "status": 200},
 "menthorq_options_matrix": {
   "endpoint": "clickhouse-api GET /api/web/v1/options/matrix/{ticker}?frequency={f}",
   "why": "The complete option matrix: every expiration with a per-strike grid (GEX/DEX/greeks) plus aggregated totals — the heaviest dataset (10–30 KB per call).",
   "db": ("%/options/matrix/SPX?frequency=eod", {"max_items": 1, "max_keys": 6}),
   "note": "Example heavily trimmed; SPX carries ~54 expirations × ~19 strikes."},
 "menthorq_put_call_ratio": {
   "endpoint": "clickhouse-api GET /api/web/v1/options/put-call-ratio/{ticker}?frequency={f}",
   "why": "Latest volume-based put/call ratio with call/put volumes. Returns the most recent snapshot only, not a series. `frequency` is required.",
   "db": ("%/put-call-ratio/SPX?frequency=eod", {})},
 "menthorq_dealer_positioning": {
   "endpoint": "clickhouse-api GET /api/web/v1/dealer-positioning/{ticker}",
   "why": "Estimated dealer book: net GEX / net DEX right now, 1h and 1d deltas, and GEX split by DTE bucket (0–7d, 8–30d, >30d).",
   "db": ("%/dealer-positioning/SPX", {})},
 "menthorq_volatility_insights": {
   "endpoint": "clickhouse-api GET /api/web/v1/volatility-insights/{ticker}",
   "why": "Volatility dashboard in one call: skew (0DTE/1M/3M with percentiles), ATM IV vs its 50-day history, and variance risk premium (VRP with 63-day average and 1-year percentile).",
   "db": ("%/volatility-insights/SPX", {})},
 "menthorq_candles": {
   "endpoint": "clickhouse-api GET /api/web/v1/tickers/{ticker}/candles?interval=…&from=…&to=…&countBack=…",
   "why": "OHLC bars for charting. Intervals are case-sensitive: `1m…45m`, `1h…4h`, `1D`, `1W`, `1M`. If you omit `from_ms`/`to_ms` the server uses the last 48 hours.",
   "db": ("%/tickers/SPX/candles?interval=5m%", {"max_items": 2})},
 "menthorq_tradingview": {
   "endpoint": "clickhouse-api GET /api/web/v1/tickers/{ticker}/tradingview",
   "why": "Symbol metadata formatted for TradingView chart embedding (ticker description, session, timezone, price scale).",
   "db": ("%/tickers/SPX/tradingview", {})},
 "menthorq_screener_columns": {
   "endpoint": "clickhouse-api GET /api/web/v1/screeners/columns",
   "why": "Catalog of all 90 screener columns with labels, categories and formatters — call this first to build valid `columns` lists for `menthorq_screener`.",
   "db": ("%/screeners/columns", {"max_items": 2})},
 "menthorq_screener": {
   "endpoint": "clickhouse-api GET /api/web/v1/screeners?columns={csv}&tickers={csv}",
   "why": "Tabular fundamentals/positioning data across tickers — one row per ticker with the requested columns.",
   "db": ("%/screeners?columns=%&tickers=SPX%", {"max_items": 2})},
 "menthorq_qbot_assets": {
   "endpoint": "qbot-service GET /api/web/v1/assets",
   "why": "QBot's asset catalog (~1,400) with asset type, category and open-interest / volume percentiles.",
   "db": ("%/api/web/v1/assets", {"max_items": 2})},
 "menthorq_events": {
   "endpoint": "qbot-service GET /api/web/v1/events?ticker=…&kind=…&start_date=…&end_date=…",
   "why": "Significant detected events for a ticker inside a date range (dates are `YYYY-MM-DD`).",
   "db": ("%/events?ticker=SPX%", {"max_items": 1})},
 "menthorq_company_news": {
   "endpoint": "qbot-service GET /api/web/v1/company-news?ticker=…&date=…&number=…",
   "why": "Curated company news articles for a given day, with title, source and sentiment fields.",
   "db": ("%/company-news?ticker=SPX%", {"max_items": 1, "max_str": 100})},
 "menthorq_user_me": {
   "endpoint": "user-service GET /api/web/v1/users/me",
   "why": "The logged-in account's profile and entitlements (plan, features). Personal fields are redacted in this documentation.",
   "db": ("%/users/me", {}),
   "redact": True},
 "menthorq_watchlists": {
   "endpoint": "user-service GET /api/web/v1/watchlists",
   "why": "The user's saved watchlists (empty list if none have been created).",
   "db": ("%/watchlists", {})},
 "menthorq_chats": {
   "endpoint": "chat-service GET /api/web/v1/chats",
   "why": "QUIN conversation list, paginated (`next_page` cursor for more).",
   "db": ("%/chat-service/api/web/v1/chats", {"max_items": 1}),
   "redact_keys": ("title",)},
 "menthorq_screener_templates": {
   "endpoint": "chat-service GET /api/web/v1/screener-templates",
   "why": "Pre-built screener templates (with their UUIDs); fetch one by ID via the same service path `/screener-templates/{id}`.",
   "db": ("%/screener-templates", {"max_items": 1, "max_str": 100})},
 "menthorq_chat_templates": {
   "endpoint": "chat-service GET /api/web/v1/templates?type=suggested",
   "why": "Suggested QUIN prompt templates grouped by use case — good inspiration for what the platform can answer.",
   "db": ("%/templates?type=suggested", {"max_items": 1, "max_str": 100})},
}


def example_block(name):
    meta = INFO[name]
    url_like, opts = meta["db"]
    status = meta.get("status", 200)
    data = fetch_example(url_like, status)
    if data is None:
        return "_No archived example available._"
    if meta.get("redact"):
        data = redact_strings(data)
    if meta.get("redact_keys"):
        data = redact_strings(data, keep_keys=("id", "created_at", "updated_at"),
                                 redact_keys=meta["redact_keys"])
    trimmed = trim(data, **opts)
    payload = json.dumps({"http_status": 200, "data": trimmed},
                         ensure_ascii=False, indent=2)
    return "```json\n" + payload + "\n```"


def schema_table(tool):
    props = tool["inputSchema"]["properties"]
    req = set(tool["inputSchema"].get("required", []))
    if not props:
        return "_No parameters._"
    lines = ["| Parameter | Type | Required | Default | Description |", "|---|---|---|---|---|"]
    for k, v in props.items():
        t = v.get("type", "?")
        if "enum" in v:
            t += " (" + "\\|".join(f"`{e}`" for e in v["enum"]) + ")"
        if "items" in v:
            t = f"array of {v['items'].get('type','?')}"
        default = f"`{json.dumps(v['default'])}`" if "default" in v else "—"
        desc = v.get("description", "").replace("|", "\\|")
        lines.append(f"| `{k}` | {t} | {'✅' if k in req else '—'} | {default} | {desc} |")
    return "\n".join(lines)


# ------------------------------------------------------------ build doc
H = []
H.append("""# MenthorQ MCP — Tool Reference with SPX Examples

Complete documentation for the `menthorq-mcp` server (`mcp/menthorq_mcp.py`).
Every tool wraps a live endpoint of the MenthorQ data platform
(`gateway.menthorq.io` — see `../API_ENDPOINTS.md` for the full API map).

## How it works

```
MCP client (Kimi)  ──stdio JSON-RPC──▶  menthorq_mcp.py  ──HTTPS──▶  gateway.menthorq.io
                                            │
                                            └─ auth: Cognito accessToken, resolved per call from
                                               MENTHORQ_TOKEN env var, or pulled live from your
                                               logged-in dashboard.menthorq.io Chrome tab (WebBridge)
```

- Transport: newline-delimited JSON-RPC 2.0 on stdio, protocol `2024-11-05`.
- Every tool returns one text content item with JSON
  `{"http_status": <int>, "data": <endpoint JSON>}`; `http_status >= 400`
  (or a failed request) also sets `isError: true`.
- Dates are `YYYY-MM-DD`; candle timestamps are millisecond epoch; token cache
  is in-memory only (5 min) — nothing is written to disk.
- Already registered in Kimi (`…/kimi-code/home/mcp.json`); new sessions see
  the tools automatically.

## Calling a tool

Natural language works in Kimi (e.g. *“get SPX gamma levels”*). On the wire,
a call looks like this:

```json
{"jsonrpc": "2.0", "id": 7, "method": "tools/call",
 "params": {"name": "menthorq_gamma_levels",
            "arguments": {"ticker": "SPX", "frequency": "eod"}}}
```

## Conventions used in the examples below

- All examples use **SPX** and come from real captured responses
  (archive date 2026-07-24/25, stored in `../menthorq.db`).
- Output is trimmed for readability: `… (+N more items)` markers show where.
- Personal data (profile, chat titles) is redacted.

---

""")

tools_by_name = {t["name"]: t for t in menthorq_mcp.TOOLS}
order = [t["name"] for t in menthorq_mcp.TOOLS]
for i, name in enumerate(order, 1):
    tool = tools_by_name[name]
    meta = INFO[name]
    H.append(f"### {i}. `{name}`\n")
    H.append(f"**Endpoint:** `{meta['endpoint']}`\n")
    H.append(f"{tool['description']}\n")
    H.append(f"**When to use it:** {meta['why']}\n")
    H.append("**Parameters:**\n")
    H.append(schema_table(tool) + "\n")
    # example arguments
    args = {}
    for k, v in tool["inputSchema"]["properties"].items():
        if k == "ticker":
            args[k] = "SPX"
        elif k == "tickers":
            args[k] = "SPX,SPY,QQQ"
        elif k == "exchange":
            args[k] = "NYSE"
        elif "default" in v:
            args[k] = v["default"]
        elif k == "start_date":
            args[k] = "2026-07-11"
        elif k in ("end_date", "date"):
            args[k] = "2026-07-25"
    args = {k: v for k, v in args.items()
            if k in tool["inputSchema"].get("required", []) or k in
            ("ticker", "tickers", "exchange", "frequency", "interval")}
    call = {"name": name, "arguments": args}
    H.append("**Example call:**\n\n```json\n" + json.dumps(call, ensure_ascii=False) + "\n```\n")
    H.append("**Example response** (real, trimmed):\n")
    H.append(example_block(name) + "\n")
    if meta.get("note"):
        H.append(f"> **Note:** {meta['note']}\n")
    H.append("\n---\n")

H.append("""
## Error behavior

| Situation | What you get |
|---|---|
| Endpoint returns 4xx/5xx | `http_status` set accordingly, `isError: true`, upstream error body in `data` |
| Session expired | `isError: true`, message: “MenthorQ session expired — … log in again” |
| WebBridge unreachable | `isError: true`, message advising to open Chrome or set `MENTHORQ_TOKEN` |
| Rate limit (429) / 5xx | retried automatically with backoff (up to 3 attempts) |

## Tips

- Start with `menthorq_market_status` before requesting intraday series on
  weekends/holidays — markets closed means the latest bars end at Friday's close.
- `metrics_intraday` rejects the `option`/`momentum`/`volatility`/`seasonality`
  aliases (HTTP 422); use the literal IV/skew field names.
- Futures need provider tickers (`DATABENTO#ES`); find exact symbols via
  `menthorq_tickers`.
- Large payloads (`options_matrix`, `tickers`, `qbot_assets`) can exceed
  150 KB — prefer targeted calls in interactive sessions.

*Generated by `mcp/gen_docs.py` from the live server schema and the scrape
archive — regenerate after changing the server.*
""")

OUT.write_text("\n".join(H))
print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
