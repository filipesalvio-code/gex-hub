"""Parse MCP tool response text and map payloads to table rows."""
import json
from dataclasses import dataclass
from typing import Any

SOURCE_MENTHORQ = "menthorq"
SOURCE_SPOTGAMMA = "spotgamma"


@dataclass
class ToolResult:
    tool: str
    ok: bool
    data: Any = None
    http_status: int | None = None
    error: str | None = None
    raw: str = ""


def parse_tool_text(tool: str, text: str) -> ToolResult:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return ToolResult(tool, ok=False, error=text[:300], raw=text)
    if isinstance(payload, dict) and "http_status" in payload:
        status = payload["http_status"]
        ok = status == 200
        return ToolResult(tool, ok=ok, data=payload.get("data"), http_status=status,
                          error=None if ok else str(payload.get("data"))[:300], raw=text)
    return ToolResult(tool, ok=True, data=payload, raw=text)


def _source(tool: str) -> str:
    return SOURCE_MENTHORQ if tool.startswith("menthorq_") else SOURCE_SPOTGAMMA


def _first(d: dict, *keys: str):
    return next((d[k] for k in keys if isinstance(d, dict) and d.get(k)), None)


def _req(tool: str, d: dict, key: str):
    if not isinstance(d, dict) or key not in d:
        raise ValueError(f"{tool}: missing required field '{key}'")
    return d[key]


def _base(tool: str, ticker: str, ts: str, cap: str) -> dict:
    return {"tool": tool, "ticker": ticker or "", "ts": ts,
            "captured_at": cap, "source": _source(tool)}


def to_rows(tool: str, result: ToolResult, captured_at: str) -> tuple[str, list[dict]]:
    if not result.ok:
        raise ValueError(f"{tool} failed: {result.error}")
    d = result.data
    payload = result.raw
    src = _source(tool)

    if tool == "menthorq_gamma_levels":
        row = {"ticker": _req(tool, d, "ticker"), "frequency": _req(tool, d, "frequency"),
               "ts": _req(tool, d, "timestamp"),
               "gex_1": d.get("gex_1"), "gex_2": d.get("gex_2"), "gex_3": d.get("gex_3"),
               "payload": payload, "captured_at": captured_at, "source": src}
        return "gamma_levels", [row]
    if tool == "menthorq_dealer_positioning":
        row = {"ticker": d.get("ticker", ""), "ts": _req(tool, d, "reference_timestamp"),
               "net_gex": d.get("net_gex"), "net_dex": d.get("net_dex"),
               "gex_dte_0_7d": d.get("gex_dte_0_7d"), "gex_dte_8_30d": d.get("gex_dte_8_30d"),
               "gex_dte_over_30d": d.get("gex_dte_over_30d"),
               "payload": payload, "captured_at": captured_at, "source": src}
        return "dealer_positioning", [row]
    if tool in ("menthorq_put_call_ratio", "spotgamma_equity_put_call_ratio"):
        row = {"ticker": d.get("ticker", d.get("sym", "")), "ts": d["timestamp"],
               "volume_calls": d.get("volume_calls"), "volume_puts": d.get("volume_puts"),
               "ratio": d.get("put_call_ratio"),
               "payload": payload, "captured_at": captured_at, "source": src}
        return "put_call_ratio", [row]
    if tool == "spotgamma_key_levels":
        items = d.get("data", []) if isinstance(d, dict) else d
        rows = [{"ticker": it.get("sym", ""), "ts": it.get("trade_date", captured_at),
                 "payload": json.dumps(it, ensure_ascii=False),
                 "captured_at": captured_at, "source": src} for it in items]
        return "key_levels", rows
    if tool == "spotgamma_compass":
        ts = _first(d, "date", "timestamp") or captured_at if isinstance(d, dict) else captured_at
        row = {"ticker": _first(d, "ticker", "sym") or "SPX" if isinstance(d, dict) else "SPX",
               "ts": ts, "payload": payload, "captured_at": captured_at, "source": src}
        return "compass", [row]

    items = d if isinstance(d, list) else [d]
    rows = []
    for it in items:
        b = _base(tool, _first(it, "ticker", "sym") or "",
                  _first(it, "timestamp", "trade_date", "date") or captured_at, captured_at)
        b.pop("tool")
        rows.append({**b, "tool": tool,
                     "payload": json.dumps(it, ensure_ascii=False)})
    return "snapshots", rows
