#!/usr/bin/env python3
"""Decoders for SpotGamma's binary API payloads.

The dashboard serves several heavy endpoints as binary, not JSON:

  endpoint                                        format
  ----------------------------------------------  ------------------------
  GET /v1/oi?sym=                                 MessagePack (expiry -> strike
                                                  -> [put, call] -> per-actor OI)
  GET /v2/latest_greeks?sym=                      MessagePack (expiry -> strike
  GET /v2/daily_greeks?sym=&date=                   -> [call_row, put_row])
  GET /v1/iv_stats?sym=                           MessagePack (tenor -> epoch
                                                  -> delta -> 9 IV values)
  GET api.stream.../intraday_strike_bars          Parquet (per-strike per-actor
    ?symbol=&bar_type=&date=                        intraday gamma/delta bars)

Dependencies: msgpack (pip), duckdb (already in the managed runtime).
Auth reuses gex_scraper's token handling ($SG_TOKEN env var / WebBridge
refresh on 401-403; no token file).

CLI:
  python3 gex_binary.py oi SPX            -> data/oi_spx.parquet (long format)
  python3 gex_binary.py greeks SPX        -> data/greeks_spx_latest.parquet
  python3 gex_binary.py ivstats SPX       -> prints tenor summary
  python3 gex_binary.py bars SPX gamma    -> data/strike_bars_spx_gamma.parquet
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import gex_scraper as gs

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
STREAM_HOST = "api.stream.spotgamma.com"

# OI record fields, in order, as served by /v1/oi (actor × side open interest)
OI_ACTOR_FIELDS = [
    "bd_buy_oi", "bd_sell_oi",           # broker-dealer
    "mm_buy_oi", "mm_sell_oi",           # market maker
    "cust_lt_100_buy_oi", "cust_lt_100_sell_oi",
    "cust_100_199_buy_oi", "cust_100_199_sell_oi",
    "cust_gt_199_buy_oi", "cust_gt_199_sell_oi",
    "procust_lt_100_buy_oi", "procust_lt_100_sell_oi",
    "procust_100_199_buy_oi", "procust_100_199_sell_oi",
    "procust_gt_199_buy_oi", "procust_gt_199_sell_oi",
    "firm_buy_oi", "firm_sell_oi",
    "cust_buy_oi", "cust_sell_oi",
    "procust_buy_oi", "procust_sell_oi",
]


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def fetch_binary(path: str, host: str | None = None, timeout: float = 120.0) -> bytes:
    """GET a binary endpoint with SpotGamma auth; decompress if needed."""
    token = os.environ.get("SG_TOKEN", "").strip() or None
    last_exc: Exception | None = None
    for attempt in (1, 2):
        headers = dict(gs.STATIC_HEADERS)
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept-Encoding"] = "gzip, deflate"
        req = urllib.request.Request(f"https://{host or gs.BASE_URL.split('//')[1]}/{path}",
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                enc = resp.headers.get("Content-Encoding", "")
                if enc == "gzip":
                    body = gzip.decompress(body)
                elif enc == "deflate":
                    import zlib
                    body = zlib.decompress(body)
                return body
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (401, 403) and attempt == 1:
                fresh = gs.refresh_token_via_webbridge()
                if fresh:
                    token = fresh
                    continue
            raise
    raise last_exc  # type: ignore[misc]


def fetch_msgpack(path: str, host: str | None = None) -> object:
    import msgpack
    return msgpack.unpackb(fetch_binary(path, host), raw=False, strict_map_key=False)


def _ts(epoch_ms: int | float) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000, timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Decoders -> pandas DataFrames
# ---------------------------------------------------------------------------

def decode_oi(data: dict) -> "pandas.DataFrame":
    """/v1/oi payload -> long DataFrame: expiry_utc, strike, side, <22 actor cols>."""
    import pandas as pd
    rows = []
    for exp_ms, strikes in data.items():
        exp_iso = _ts(int(exp_ms))
        for strike, pair in strikes.items():
            put_rec, call_rec = pair[0], pair[1]
            for side, rec in (("put", put_rec), ("call", call_rec)):
                if rec is None:
                    continue
                rows.append({"expiry_utc": exp_iso, "strike": float(strike),
                             "side": side, **{f: rec.get(f) for f in OI_ACTOR_FIELDS}})
    return pd.DataFrame(rows)


def fetch_oi(sym: str) -> "pandas.DataFrame":
    return decode_oi(fetch_msgpack(f"v1/oi?sym={urllib.parse.quote(sym)}"))


def decode_greeks(data: dict) -> "pandas.DataFrame":
    """/v2/latest_greeks|daily_greeks payload -> long DataFrame.

    Layout per expiry(int ms) -> strike(float) -> [call_row, put_row].
    Each row is ~8 numbers; exact per-position semantics are not published by
    SpotGamma, so columns are positional (v0..vN). Observed: v0/v1 look like
    bid/ask, v2 delta-like, v7 an epoch-ms timestamp.
    """
    import pandas as pd
    rows = []
    for exp_ms, strikes in data.items():
        exp_iso = _ts(int(exp_ms))
        for strike, pair in strikes.items():
            if not isinstance(pair, (list, tuple)):
                continue
            for side, rec in (("call", pair[0]), ("put", pair[1] if len(pair) > 1 else None)):
                if rec is None:
                    continue
                row = {"expiry_utc": exp_iso, "strike": float(strike), "side": side}
                for i, v in enumerate(rec):
                    row[f"v{i}"] = v
                rows.append(row)
    return pd.DataFrame(rows)


def fetch_greeks(sym: str, date: str | None = None) -> "pandas.DataFrame":
    q = urllib.parse.quote(sym)
    if date:
        return decode_greeks(fetch_msgpack(f"v2/daily_greeks?sym={q}&date={date}"))
    return decode_greeks(fetch_msgpack(f"v2/latest_greeks?sym={q}"))


def fetch_iv_stats(sym: str) -> dict:
    """/v1/iv_stats payload -> {tenor_days: {epoch_key: {delta: [9 floats]}}}.

    Tenors observed: 30/60/90. Structure as served; per-position semantics of
    the 9-value arrays are not published.
    """
    return fetch_msgpack(f"v1/iv_stats?sym={urllib.parse.quote(sym)}")


def fetch_strike_bars(symbol: str, bar_type: str = "gamma",
                      date: str | None = None) -> "pandas.DataFrame":
    """api.stream /v2/open_interest/intraday_strike_bars (Parquet) -> DataFrame.

    Columns: strike_price, timestamp, {bd,cust,firm,mm,procust}_gamma (or delta,
    per bar_type) and *_0 variants. Note the API returns a trailing multi-day
    window, not just the requested date.
    """
    import duckdb
    import tempfile
    params = f"symbol={urllib.parse.quote(symbol)}&bar_type={urllib.parse.quote(bar_type)}"
    if date:
        params += f"&date={date}"
    body = fetch_binary(f"v2/open_interest/intraday_strike_bars?{params}", host=STREAM_HOST)
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp.write(body)
        tmp_path = tmp.name
    try:
        con = duckdb.connect()
        return con.execute("SELECT * FROM read_parquet(?)", [tmp_path]).df()
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Nightly archive
# ---------------------------------------------------------------------------

def archive_oi(sym: str = "SPX", out_dir: str | Path | None = None,
               force: bool = False) -> dict:
    """Download the full per-actor OI matrix for `sym` and store it as a
    per-day parquet file (deduped by US-Eastern calendar date).

    Returns a JSON-serializable summary; never raises on API failure —
    check summary["status"].
    """
    from zoneinfo import ZoneInfo
    out_dir = Path(out_dir) if out_dir else DATA_DIR / "oi"
    out_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    out = out_dir / f"oi_{sym.lower()}_{day}.parquet"

    if out.exists() and not force:
        return {"status": "skipped_exists", "sym": sym, "date": day,
                "file": str(out), "rows": None}
    try:
        df = fetch_oi(sym)
    except Exception as exc:
        return {"status": "error", "sym": sym, "date": day,
                "file": None, "rows": 0, "error": str(exc)[:300]}
    df.to_parquet(out, index=False)
    return {"status": "ok", "sym": sym, "date": day, "file": str(out),
            "rows": int(len(df)), "expiries": int(df.expiry_utc.nunique()),
            "strikes": int(df.strike.nunique())}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="SpotGamma binary payload decoders")
    ap.add_argument("what", choices=("oi", "greeks", "ivstats", "bars"))
    ap.add_argument("sym")
    ap.add_argument("extra", nargs="?", default=None,
                    help="bars: bar_type (gamma|delta) | greeks: date YYYY-MM-DD")
    args = ap.parse_args()
    DATA_DIR.mkdir(exist_ok=True)
    sym = args.sym.upper()

    if args.what == "oi":
        df = fetch_oi(sym)
        out = DATA_DIR / f"oi_{sym.lower()}.parquet"
        df.to_parquet(out, index=False)
        print(f"{len(df):,} rows | expiries={df.expiry_utc.nunique()} "
              f"strikes={df.strike.nunique()} -> {out}")
    elif args.what == "greeks":
        df = fetch_greeks(sym, args.extra)
        tag = args.extra or "latest"
        out = DATA_DIR / f"greeks_{sym.lower()}_{tag}.parquet"
        df.to_parquet(out, index=False)
        print(f"{len(df):,} rows | expiries={df.expiry_utc.nunique()} "
              f"strikes={df.strike.nunique()} -> {out}")
    elif args.what == "ivstats":
        data = fetch_iv_stats(sym)
        for tenor, per_day in data.items():
            print(f"tenor {tenor}d: {len(per_day)} day-keys")
            k = next(iter(per_day))
            deltas = per_day[k]
            print(f"  sample day-key {k}: {len(deltas)} delta points, "
                  f"deltas {sorted(deltas)[:3]} ... value[0..8] e.g. {deltas[sorted(deltas)[0]][:3]}")
    else:
        df = fetch_strike_bars(sym, args.extra or "gamma",
                               date=None)
        out = DATA_DIR / f"strike_bars_{sym.lower()}_{args.extra or 'gamma'}.parquet"
        df.to_parquet(out, index=False)
        print(f"{len(df):,} rows | {df.timestamp.min()} .. {df.timestamp.max()} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
