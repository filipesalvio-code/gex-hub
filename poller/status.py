"""Print poller health summary from scrape_runs."""
import argparse

from poller.db import init_db
from poller.observe import status_report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gex-poller-status")
    p.add_argument("--db", default="timeseries.db")
    ns = p.parse_args(argv)
    rep = status_report(init_db(ns.db))
    print(f"cycles (24h): {rep['cycles_24h']}  failed: {rep['failed_24h']}"
          f"  last cycle: {rep['last_cycle']}")
    for tool, mins in sorted(rep["freshness"].items()):
        print(f"  {tool:<40} last ok {mins} min ago")
    if rep["last_errors"]:
        print("recent errors:")
        for e in rep["last_errors"]:
            print(f"  - {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
