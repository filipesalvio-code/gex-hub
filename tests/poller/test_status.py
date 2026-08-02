import pytest

from poller.db import begin_cycle, init_db, record_call
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
