#!/usr/bin/env python3
"""Build the positioning-dashboard artifact from the local SpotGamma archive.

Reads:
  - gex_data.db        (key_levels -> regime, walls, indices, drift)
  - data/oi/*.parquet  (latest per-actor OI matrix -> MM vs customer net OI by strike)

Pure stdlib + duckdb; no network access.
"""

from __future__ import annotations

import glob
import os
import re
import sqlite3
from datetime import UTC, datetime

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(WORKSPACE, "gex_data.db")
OI_GLOB = os.path.join(WORKSPACE, "data", "oi", "oi_*_*.parquet")

WINDOW_PTS = 400   # strikes within +/- this many points of spot
BIN_PTS = 50       # strike bin width


def _latest_indices(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT k.sym, k.upx, k.callwallstrike AS cws, k.putwallstrike AS pws,
               k.zero_g_strike AS zero_g, k.max_g_strike AS max_g,
               k.topabs_strike AS topabs, k.gamma_not, k.trade_date
        FROM key_levels k
        JOIN (SELECT sym, MAX(trade_date) AS td FROM key_levels GROUP BY sym) m
          ON k.sym = m.sym AND k.trade_date = m.td
        ORDER BY k.sym
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _drift(conn: sqlite3.Connection, sym: str = "SPX", limit: int = 60) -> list[dict]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT trade_date, upx, callwallstrike AS cws, putwallstrike AS pws,
               zero_g_strike AS zero_g
        FROM key_levels WHERE sym = ? ORDER BY trade_date DESC LIMIT ?
        """,
        (sym, limit),
    ).fetchall()
    out = [dict(r) for r in rows]
    for r in out:
        r["trade_date"] = str(r["trade_date"])[:10]
    out.reverse()
    return out


def _positioning(spot: float) -> tuple[dict, str | None]:
    files = sorted(glob.glob(OI_GLOB))
    if not files:
        return {"strikes": [], "mm": [], "cust": []}, None
    latest = files[-1]
    m = re.search(r"_(\d{4}-\d{2}-\d{2})\.parquet$", latest)
    oi_date = m.group(1) if m else None

    import duckdb
    lo, hi = spot - WINDOW_PTS, spot + WINDOW_PTS
    con = duckdb.connect()
    df = con.execute(
        f"""
        SELECT CAST(FLOOR(strike / {BIN_PTS}) * {BIN_PTS} AS INTEGER) AS bin,
               SUM(mm_buy_oi - mm_sell_oi)     AS mm_net,
               SUM(cust_buy_oi - cust_sell_oi) AS cust_net
        FROM read_parquet(?)
        WHERE strike BETWEEN ? AND ?
        GROUP BY bin ORDER BY bin
        """,
        [latest, lo, hi],
    ).df()
    return (
        {
            "strikes": [int(v) for v in df["bin"]],
            "mm": [float(v) for v in df["mm_net"]],
            "cust": [float(v) for v in df["cust_net"]],
        },
        oi_date,
    )


def build_artifact(db_path: str = DB_PATH) -> dict:
    conn = sqlite3.connect(db_path)
    indices = _latest_indices(conn)
    drift = _drift(conn)
    conn.close()

    spx = next((r for r in indices if r["sym"] == "SPX"), indices[0] if indices else {})
    regime = {
        "gamma_not": spx.get("gamma_not"),
        "upx": spx.get("upx"),
        "zero_g": spx.get("zero_g"),
        "trade_date": str(spx.get("trade_date") or "")[:10],
    }
    walls = {
        "cws": spx.get("cws"),
        "pws": spx.get("pws"),
        "zero_g": spx.get("zero_g"),
        "max_g": spx.get("max_g"),
        "topabs": spx.get("topabs"),
    }
    spot = float(spx.get("upx") or 0)
    positioning, oi_date = _positioning(spot) if spot else ({"strikes": [], "mm": [], "cust": []}, None)

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "oi_date": oi_date,
        "regime": regime,
        "walls": walls,
        "indices": [
            {k: (str(v)[:10] if k == "trade_date" else v) for k, v in r.items()}
            for r in indices
        ],
        "positioning": positioning,
        "drift": drift,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build_artifact(), indent=1)[:3000])
