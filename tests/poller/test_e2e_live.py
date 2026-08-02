import pytest

from poller.db import init_db
from poller.mcp_client import MENTHORQ_ARGV, SPOTGAMMA_ARGV, McpClient
from poller.observe import JsonlLogger
from poller.poll import CAPTURE, run_cycle

pytestmark = pytest.mark.live


def test_live_cycle(tmp_path):
    conn = init_db(tmp_path / "live.db")
    with McpClient(MENTHORQ_ARGV) as m, McpClient(SPOTGAMMA_ARGV) as sg:
        rep = run_cycle({"m": m, "sg": sg}, conn, JsonlLogger(tmp_path / "l.jsonl"))
    ok = conn.execute("SELECT COUNT(*) FROM scrape_runs WHERE error IS NULL").fetchone()[0]
    assert ok >= len(CAPTURE) * 0.4, f"only {ok}/{len(CAPTURE)} tools succeeded"
    assert rep["rows"] > 0
