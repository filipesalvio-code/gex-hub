#!/usr/bin/env python3
"""MenthorQ MCP server (stdio, zero-dependency).

Exposes the MenthorQ data platform APIs (gateway.menthorq.io) as MCP tools.
Discovered 2026-07-25 from dashboard.menthorq.io (see API_ENDPOINTS.md).

Auth (resolved per call, cached ~5 min):
  1. env MENTHORQ_TOKEN          — explicit Cognito accessToken (highest priority)
  2. Kimi WebBridge daemon        — pulls a fresh accessToken from the user's
     open dashboard.menthorq.io Chrome tab (GET /api/auth/session).
     Env overrides: MENTHORQ_BRIDGE_URL (default http://127.0.0.1:10086/command),
     MENTHORQ_BRIDGE_SESSION (default "menthorq-scrape").

Transport: newline-delimited JSON-RPC 2.0 on stdio (MCP stdio transport).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GATEWAY = "https://gateway.menthorq.io"
BRIDGE_URL = os.environ.get("MENTHORQ_BRIDGE_URL", "http://127.0.0.1:10086/command")
BRIDGE_SESSION = os.environ.get("MENTHORQ_BRIDGE_SESSION", "menthorq-scrape")
PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "menthorq-mcp", "version": "1.0.0"}

_token_cache = {"value": None, "fetched_at": 0.0}


# ---------------------------------------------------------------- auth/http
def _bridge(action: str, args: dict, timeout: int = 60) -> dict:
    body = json.dumps({"action": action, "args": args,
                       "session": BRIDGE_SESSION}).encode()
    req = urllib.request.Request(BRIDGE_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


_SESSION_PROBE = (
    "(async()=>{"
    "if(!location.href.startsWith('https://dashboard.menthorq.io'))"
    "return JSON.stringify({state:'wrong_tab'});"
    "const r=await fetch('/api/auth/session');"
    "const ct=r.headers.get('content-type')||'';"
    "if(!ct.includes('json'))return JSON.stringify({state:'not_json'});"
    "const j=await r.json();"
    "return JSON.stringify({state:j.accessToken?'ok':'no_token',token:j.accessToken||''})"
    "})()")


def _probe_session() -> dict:
    out = _bridge("evaluate", {"code": _SESSION_PROBE})
    raw = (out.get("data") or {}).get("value") or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"state": "error", "raw": raw[:200]}


def _fetch_token_via_bridge() -> str:
    """Get accessToken from a dashboard.menthorq.io tab.

    Fast path: re-select an existing dashboard tab (list_tabs + find_tab) and
    read /api/auth/session. The daemon's evaluate target can stick to an older
    tab, so on 'wrong_tab' fall back to opening a fresh dashboard tab via
    navigate (which reliably becomes the evaluate target).
    """
    try:
        tabs = (_bridge("list_tabs", {}).get("data") or {}).get("tabs") or []
        dash = next((t for t in tabs
                     if str(t.get("url", "")).startswith("https://dashboard.menthorq.io")), None)
        if dash:
            _bridge("find_tab", {"url": dash["url"]})
            for _ in range(2):
                p = _probe_session()
                if p.get("state") == "ok":
                    return p["token"]
                if p.get("state") == "not_json":
                    break
                time.sleep(1)
    except Exception:
        pass

    # Fallback: open a fresh dashboard tab (navigate makes it the target).
    _bridge("navigate", {"url": "https://dashboard.menthorq.io/en/chats",
                         "newTab": True}, timeout=90)
    time.sleep(7)
    last = "no response"
    for _ in range(3):
        p = _probe_session()
        state = p.get("state", "error")
        if state == "ok":
            return p["token"]
        if state == "not_json":
            raise RuntimeError(
                "MenthorQ session expired — /api/auth/session returned HTML. "
                "Open https://dashboard.menthorq.io in Chrome, log in again, "
                "then retry (or set MENTHORQ_TOKEN).")
        last = state
        time.sleep(2)
    raise RuntimeError(
        f"Could not read a MenthorQ session token from the browser (last state: {last}). "
        "Make sure Chrome is open with dashboard.menthorq.io logged in, or set MENTHORQ_TOKEN.")


def get_token(force: bool = False) -> str:
    env = os.environ.get("MENTHORQ_TOKEN", "").strip()
    if env:
        return env
    now = time.time()
    if not force and _token_cache["value"] and now - _token_cache["fetched_at"] < 300:
        return _token_cache["value"]
    try:
        token = _fetch_token_via_bridge()
    except RuntimeError:
        raise
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "Cannot reach Kimi WebBridge to obtain a MenthorQ token. Open "
            "dashboard.menthorq.io in Chrome (logged in) or set MENTHORQ_TOKEN. "
            f"Detail: {e!r}")
    if not token:
        raise RuntimeError(
            "WebBridge returned no accessToken — is dashboard.menthorq.io open "
            "and logged in? Or set MENTHORQ_TOKEN explicitly.")
    _token_cache.update(value=token, fetched_at=now)
    return token


def api_get(service: str, path: str, timeout: int = 60):
    """GET gateway endpoint -> (http_status, parsed_json). Retries 429/5xx."""
    if not path.startswith("/"):
        path = "/" + path
    url = f"{GATEWAY}/{service}{path}"
    last = None
    for attempt in range(3):
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {get_token(force=attempt > 0)}",
                          "Accept": "application/json",
                          "Origin": "https://dashboard.menthorq.io"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")[:2000]
            if e.code in (429,) or e.code >= 500:
                last = f"HTTP {e.code}: {text}"
                time.sleep(2 * (attempt + 1))
                continue
            try:
                return e.code, json.loads(text)
            except json.JSONDecodeError:
                return e.code, {"error": text}
        except Exception as e:  # noqa: BLE001
            last = repr(e)
            time.sleep(2 * (attempt + 1))
    return 0, {"error": f"request failed after retries: {last}"}


def enc(s) -> str:
    return urllib.parse.quote(str(s), safe="")


# ------------------------------------------------------------------- tools
def _t(name, desc, props, required=()):
    return {"name": name, "description": desc,
            "inputSchema": {"type": "object", "properties": props,
                            "required": list(required)}}


_FREQ = {"type": "string", "enum": ["eod", "intraday"], "default": "eod",
         "description": "eod = previous close snapshot; intraday = latest intraday update"}
_TICKER = {"type": "string", "description": "Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers)."}

TOOLS = [
    _t("menthorq_tickers", "Full instrument universe (~1250 stocks/ETFs/futures with contracts).", {}),
    _t("menthorq_prices", "Latest price snapshot (current/open/high/low/previous_close) for a comma-separated list of tickers.",
       {"tickers": {"type": "string", "description": "Comma-separated tickers, e.g. 'SPX,SPY,QQQ'"}}, ["tickers"]),
    _t("menthorq_market_status", "Market open/closed status and session times. Only NYSE and NASDAQ are supported.",
       {"exchange": {"type": "string", "default": "NYSE"}}),
    _t("menthorq_gamma_levels", "Gamma exposure key levels: gex_1..gex_10, call resistance, put support, 0DTE variants, gamma wall, HVL, 1-day expected move.",
       {"ticker": _TICKER, "frequency": _FREQ}, ["ticker"]),
    _t("menthorq_gamma_insights", "Per-expiration gamma insights (GEX, percentiles) for a ticker.",
       {"ticker": _TICKER, "limit": {"type": "integer", "default": 20}}, ["ticker"]),
    _t("menthorq_gamma_insights_expirations", "Gamma insight summary across expirations.",
       {"ticker": _TICKER, "frequency": _FREQ}, ["ticker"]),
    _t("menthorq_metrics_eod", "Daily metrics history (default 30 rows). Fields: option, momentum, volatility, seasonality.",
       {"ticker": _TICKER,
        "fields": {"type": "array", "items": {"type": "string", "enum": ["option", "momentum", "volatility", "seasonality"]},
                   "default": ["option", "momentum", "volatility", "seasonality"]},
        "limit": {"type": "integer", "default": 30}}, ["ticker"]),
    _t("menthorq_metrics_intraday", "Intraday (30-min bar) IV/skew metrics. Valid fields only: iv_1m_50d, iv_3m_50d, iv_0dte_50d, skew_1m, skew_3m, skew_0dte.",
       {"ticker": _TICKER,
        "fields": {"type": "array", "items": {"type": "string", "enum": ["iv_1m_50d", "iv_3m_50d", "iv_0dte_50d", "skew_1m", "skew_3m", "skew_0dte"]},
                   "default": ["iv_1m_50d", "skew_1m"]},
        "limit": {"type": "integer", "default": 30}}, ["ticker"]),
    _t("menthorq_options_matrix", "Full option matrix: per-expiration strike grid with greeks/positioning and totals.",
       {"ticker": _TICKER, "frequency": _FREQ}, ["ticker"]),
    _t("menthorq_put_call_ratio", "Latest put/call ratio snapshot (volume-based).",
       {"ticker": _TICKER, "frequency": _FREQ}, ["ticker"]),
    _t("menthorq_dealer_positioning", "Dealer positioning: net GEX/DEX current + 1h/1d deltas, GEX by DTE bucket.",
       {"ticker": _TICKER}, ["ticker"]),
    _t("menthorq_volatility_insights", "Volatility dashboard: skew (0DTE/1M/3M + percentiles), ATM IV vs 50d, variance risk premium.",
       {"ticker": _TICKER}, ["ticker"]),
    _t("menthorq_candles", "OHLC candles. Intervals (case-sensitive): 1m..45m, 1h..4h, 1D, 1W, 1M. from_ms/to_ms are millisecond epoch.",
       {"ticker": _TICKER,
        "interval": {"type": "string", "default": "5m"},
        "from_ms": {"type": "integer", "description": "Start, ms epoch (default: 48h ago)"},
        "to_ms": {"type": "integer", "description": "End, ms epoch (default: now)"},
        "count_back": {"type": "integer", "default": 288}}, ["ticker"]),
    _t("menthorq_tradingview", "TradingView chart configuration payload for a ticker.",
       {"ticker": _TICKER}, ["ticker"]),
    _t("menthorq_screener_columns", "Catalog of all ~90 screener columns (name, label, category, description).", {}),
    _t("menthorq_screener", "Run screener over given tickers with chosen columns.",
       {"tickers": {"type": "string", "description": "Comma-separated tickers"},
        "columns": {"type": "string", "description": "Comma-separated column names, e.g. 'name,sector,market_cap,volume'",
                    "default": "name,quote_type,sector,industry,market_cap,volume"}}, ["tickers"]),
    _t("menthorq_qbot_assets", "QBot asset catalog (~1400) with type, category, OI/volume percentiles.", {}),
    _t("menthorq_events", "Significant market events for a ticker in a date range.",
       {"ticker": _TICKER,
        "kind": {"type": "string", "default": "news_significant"},
        "start_date": {"type": "string", "description": "YYYY-MM-DD"},
        "end_date": {"type": "string", "description": "YYYY-MM-DD"}},
       ["ticker", "start_date", "end_date"]),
    _t("menthorq_company_news", "Latest company news articles for a ticker.",
       {"ticker": _TICKER,
        "date": {"type": "string", "description": "YYYY-MM-DD"},
        "number": {"type": "integer", "default": 12}}, ["ticker", "date"]),
    _t("menthorq_user_me", "Account profile of the logged-in MenthorQ user.", {}),
    _t("menthorq_watchlists", "User watchlists (user-service).", {}),
    _t("menthorq_chats", "QUIN chat list (chat-service, paginated).", {}),
    _t("menthorq_screener_templates", "QUIN screener templates list.", {}),
    _t("menthorq_chat_templates", "Suggested QUIN chat templates.", {}),
]


def call_tool(name: str, a: dict):
    ch = "clickhouse-api"
    if name == "menthorq_tickers":
        return api_get(ch, "/api/web/v1/tickers")
    if name == "menthorq_prices":
        return api_get(ch, f"/api/web/v1/prices?tickers={enc(a['tickers'])}")
    if name == "menthorq_market_status":
        return api_get(ch, f"/api/web/v1/market-status/{enc(a.get('exchange', 'NYSE'))}")
    if name == "menthorq_gamma_levels":
        return api_get(ch, f"/api/web/v1/gamma-levels/{enc(a['ticker'])}/{a.get('frequency', 'eod')}")
    if name == "menthorq_gamma_insights":
        return api_get(ch, f"/api/web/v1/gamma-insights/{enc(a['ticker'])}?limit={int(a.get('limit', 20))}")
    if name == "menthorq_gamma_insights_expirations":
        return api_get(ch, f"/api/web/v1/gamma-insights/{enc(a['ticker'])}/expirations?frequency={a.get('frequency', 'eod')}")
    if name == "menthorq_metrics_eod":
        fs = "".join(f"&fields={f}" for f in a.get("fields", ["option", "momentum", "volatility", "seasonality"]))
        return api_get(ch, f"/api/web/v1/metrics/{enc(a['ticker'])}/eod?{fs.lstrip('&')}&limit={int(a.get('limit', 30))}")
    if name == "menthorq_metrics_intraday":
        fs = "".join(f"&fields={f}" for f in a.get("fields", ["iv_1m_50d", "skew_1m"]))
        return api_get(ch, f"/api/web/v1/metrics/{enc(a['ticker'])}/intraday?{fs.lstrip('&')}&limit={int(a.get('limit', 30))}")
    if name == "menthorq_options_matrix":
        return api_get(ch, f"/api/web/v1/options/matrix/{enc(a['ticker'])}?frequency={a.get('frequency', 'eod')}")
    if name == "menthorq_put_call_ratio":
        return api_get(ch, f"/api/web/v1/options/put-call-ratio/{enc(a['ticker'])}?frequency={a.get('frequency', 'eod')}")
    if name == "menthorq_dealer_positioning":
        return api_get(ch, f"/api/web/v1/dealer-positioning/{enc(a['ticker'])}")
    if name == "menthorq_volatility_insights":
        return api_get(ch, f"/api/web/v1/volatility-insights/{enc(a['ticker'])}")
    if name == "menthorq_candles":
        now_ms = int(time.time() * 1000)
        frm = int(a.get("from_ms") or now_ms - 48 * 3600 * 1000)
        to = int(a.get("to_ms") or now_ms)
        return api_get(ch, f"/api/web/v1/tickers/{enc(a['ticker'])}/candles?interval={a.get('interval', '5m')}"
                           f"&from={frm}&to={to}&countBack={int(a.get('count_back', 288))}")
    if name == "menthorq_tradingview":
        return api_get(ch, f"/api/web/v1/tickers/{enc(a['ticker'])}/tradingview")
    if name == "menthorq_screener_columns":
        return api_get(ch, "/api/web/v1/screeners/columns")
    if name == "menthorq_screener":
        cols = enc(a.get("columns", "name,quote_type,sector,industry,market_cap,volume"))
        return api_get(ch, f"/api/web/v1/screeners?columns={cols}&tickers={enc(a['tickers'])}")
    if name == "menthorq_qbot_assets":
        return api_get("qbot-service", "/api/web/v1/assets")
    if name == "menthorq_events":
        return api_get("qbot-service", f"/api/web/v1/events?ticker={enc(a['ticker'])}&kind={enc(a.get('kind', 'news_significant'))}"
                                       f"&start_date={a['start_date']}&end_date={a['end_date']}")
    if name == "menthorq_company_news":
        return api_get("qbot-service", f"/api/web/v1/company-news?ticker={enc(a['ticker'])}&date={a['date']}&number={int(a.get('number', 12))}")
    if name == "menthorq_user_me":
        return api_get("user-service", "/api/web/v1/users/me")
    if name == "menthorq_watchlists":
        return api_get("user-service", "/api/web/v1/watchlists")
    if name == "menthorq_chats":
        return api_get("chat-service", "/api/web/v1/chats")
    if name == "menthorq_screener_templates":
        return api_get("chat-service", "/api/web/v1/screener-templates")
    if name == "menthorq_chat_templates":
        return api_get("chat-service", "/api/web/v1/templates?type=suggested")
    raise KeyError(name)


# ------------------------------------------------------------- json-rpc loop
def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def result(msg_id, payload):
    send({"jsonrpc": "2.0", "id": msg_id, "result": payload})


def error(msg_id, code, message):
    send({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


def handle(req):
    method = req.get("method", "")
    msg_id = req.get("id")
    if method == "initialize":
        result(msg_id, {"protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO})
    elif method == "ping":
        result(msg_id, {})
    elif method == "tools/list":
        result(msg_id, {"tools": TOOLS})
    elif method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            status, data = call_tool(name, args)
            text = json.dumps({"http_status": status, "data": data}, ensure_ascii=False)
            result(msg_id, {"content": [{"type": "text", "text": text}],
                            "isError": status == 0 or status >= 400})
        except KeyError:
            error(msg_id, -32602, f"unknown tool: {name}")
        except Exception as e:  # noqa: BLE001
            result(msg_id, {"content": [{"type": "text", "text": f"error: {e}"}],
                            "isError": True})
    elif method.startswith("notifications/"):
        pass  # no response
    elif msg_id is not None:
        error(msg_id, -32601, f"method not found: {method}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            handle(json.loads(line))
        except json.JSONDecodeError:
            error(None, -32700, "parse error")


if __name__ == "__main__":
    main()
