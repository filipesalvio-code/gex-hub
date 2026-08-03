import pytest

from poller.db import begin_cycle, finish_cycle, init_db, record_call
from poller.observe import status_report
from poller.status import main

pytestmark = pytest.mark.integration


def test_status_prints_summary(tmp_path, capsys):
    db = tmp_path / "t.db"
    conn = init_db(db)
    c = begin_cycle(conn, "poller")
    record_call(conn, c, "menthorq_prices", 200, 3, None)
    conn.close()
    assert main(["--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert "cycles (24h): 1" in out and "failed: 0" in out
    assert "menthorq_prices" in out


def test_status_last_cycle_is_newest(tmp_path):
    conn = init_db(tmp_path / "t.db")
    for _ in range(2):
        c = begin_cycle(conn, "poller")
        record_call(conn, c, "menthorq_prices", 200, 1, None)
        finish_cycle(conn, c)
    rep = status_report(conn)
    newest = conn.execute("SELECT MAX(cycle_id) FROM scrape_runs").fetchone()[0]
    assert rep["cycles_24h"] == 2 and rep["last_cycle"] == newest
