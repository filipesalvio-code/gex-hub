#!/usr/bin/env python3
"""Plot the SPX (or any symbol) gamma-exposure profile from gex_data.db.

Two panels sharing the strike axis:
  left  — per-strike call vs put gamma notional (diverging bars, $M)
  right — SpotGamma's total gamma curve (key_levels strike_list/current_list, $B)

Reference lines: spot price, call wall, put wall, zero-gamma flip.

Usage:
  python3 plot_spx_gamma.py                 # latest SPX row in gex_data.db
  python3 plot_spx_gamma.py --sym QQQ
  python3 plot_spx_gamma.py --date 2026-07-23 --window 800
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.executable).parent.parent.parent))
from daimon_runtime import setup_plot  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "gex_data.db"


def load_data(db: sqlite3.Connection, sym: str, date: str | None):
    if date:
        eq = db.execute(
            "SELECT * FROM equities_gex WHERE sym=? AND trade_date LIKE ?",
            (sym, f"{date}%")).fetchone()
        kl = db.execute(
            "SELECT * FROM key_levels WHERE sym=? AND trade_date LIKE ?",
            (sym, f"{date}%")).fetchone()
    else:
        eq = db.execute(
            "SELECT * FROM equities_gex WHERE sym=? ORDER BY trade_date DESC LIMIT 1",
            (sym,)).fetchone()
        kl = db.execute(
            "SELECT * FROM key_levels WHERE sym=? ORDER BY trade_date DESC LIMIT 1",
            (sym,)).fetchone()
    return eq, kl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="SPX")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: latest)")
    ap.add_argument("--window", type=float, default=700.0,
                    help="strike window half-width around spot (default 700)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    sym = args.sym.upper()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    eq, kl = load_data(conn, sym, args.date)
    if not eq:
        print(f"No equities_gex row for {sym}", file=sys.stderr)
        return 1

    raw = json.loads(eq["raw_json"])
    trade_date = str(eq["trade_date"])[:10]
    spot = float(eq["upx"])

    strikes = json.loads(raw["call_strikes_list_absg"])
    call_g = json.loads(raw["call_gnot_list_absg"])
    put_g = json.loads(raw["put_gnot_list_absg"])
    df = pd.DataFrame({"strike": strikes,
                       "call_g": [abs(v) / 1e6 for v in call_g],
                       "put_g": [abs(v) / 1e6 for v in put_g]})
    lo, hi = spot - args.window, spot + args.window
    df = df[(df.strike >= lo) & (df.strike <= hi)]
    # Bin to 25-pt buckets so bars stay readable (raw grid is 5-pt near spot).
    df["bin"] = (df.strike // 25) * 25
    df = df.groupby("bin", as_index=False)[["call_g", "put_g"]].sum()
    df = df.rename(columns={"bin": "strike"}).reset_index(drop=True)

    # Reference levels (from key_levels when available)
    cw = pw = flip = None
    curve = None
    if kl:
        cw, pw, flip = kl["callwallstrike"], kl["putwallstrike"], kl["zero_g_strike"]
        cs = json.loads(kl["strike_list"])
        cc = json.loads(kl["current_list"])
        curve = pd.DataFrame({"strike": cs, "gamma_b": [v / 1e9 for v in cc]})
        curve = curve[(curve.strike >= lo) & (curve.strike <= hi)]

    setup_plot()
    fig, (ax_bars, ax_curve) = plt.subplots(
        1, 2, figsize=(13, min(14, max(8, len(df) * 0.24))), sharey=True,
        gridspec_kw={"width_ratios": [1.35, 1.0], "wspace": 0.06})

    # --- left: diverging call/put bars -------------------------------------
    bar_h = (df.strike.diff().median() or 20) * 0.9
    ax_bars.barh(df.strike, df.call_g, height=bar_h,
                 color="#2ea043", alpha=0.9, label="Call gamma")
    ax_bars.barh(df.strike, -df.put_g, height=bar_h,
                 color="#e5534b", alpha=0.9, label="Put gamma")
    ax_bars.axvline(0, color="#888", lw=0.8)
    ax_bars.set_xlabel("Gamma notional per 25-pt strike bin ($M, abs)")
    ax_bars.set_ylabel("Strike")
    ax_bars.legend(loc="lower right", fontsize=9)
    xmax = max(df.call_g.max(), df.put_g.max()) * 1.12
    ax_bars.set_xlim(-xmax, xmax)

    # --- right: total gamma curve -------------------------------------------
    if curve is not None and len(curve):
        ax_curve.plot(curve.gamma_b, curve.strike, color="#d29922", lw=1.8)
        ax_curve.fill_betweenx(curve.strike, 0, curve.gamma_b, color="#d29922", alpha=0.25)
        ax_curve.set_xlabel("Total gamma curve ($B)")
        ax_curve.set_xlim(left=0)

    # --- reference lines on both panels --------------------------------------
    def hline(y, color, label, ax_label, x_frac, va, ha):
        for ax in (ax_bars, ax_curve):
            ax.axhline(y, color=color, lw=1.2, ls="--", alpha=0.85)
        ax_label.annotate(label, xy=(x_frac, y), xycoords=("axes fraction", "data"),
                          va=va, ha=ha, fontsize=9, color=color, fontweight="bold")

    hline(spot, "#58a6ff", f"Spot {spot:,.0f}", ax_curve, 0.03, "top", "left")
    if cw:
        hline(cw, "#2ea043", f"Call wall {cw:,.0f}", ax_bars, 0.99, "bottom", "right")
    if pw:
        hline(pw, "#e5534b", f"Put wall {pw:,.0f}", ax_bars, 0.01, "top", "left")
    if flip:
        hline(flip, "#d29922", f"Zero-gamma {flip:,.0f}", ax_curve, 0.03, "bottom", "left")

    net_gamma = kl["gamma_not"] / 1e9 if kl and kl["gamma_not"] is not None else None
    subtitle = (f"trade date {trade_date}   ·   spot {spot:,.2f}   ·   "
                f"net gamma {net_gamma:+.2f}B" if net_gamma is not None
                else f"trade date {trade_date}   ·   spot {spot:,.2f}")
    fig.suptitle(f"{sym} Gamma Exposure by Strike\n{subtitle}", fontsize=13,
                 fontweight="bold")
    fig.subplots_adjust(top=0.92, left=0.08, right=0.98, bottom=0.06)

    out = Path(args.out) if args.out else SCRIPT_DIR / f"{sym.lower()}_gamma_curve.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
