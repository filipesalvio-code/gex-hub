import json
import sys
from pathlib import Path

import pytest

from poller.mcp_client import McpClient, McpError

pytestmark = pytest.mark.integration

SILENT_SERVER = str(Path(__file__).parent / "silent_mcp_server.py")
HANG_SERVER = str(Path(__file__).parent / "hang_mcp_server.py")


def test_call_tool_success(fake_mcp):
    with fake_mcp({"menthorq_prices": json.dumps({"http_status": 200, "data": [1]})}) as c:
        r = c.call_tool("menthorq_prices", {"tickers": "SPX"})
        assert r.ok and r.data == [1] and r.http_status == 200


def test_unknown_tool_raises(fake_mcp):
    with fake_mcp({}) as c, pytest.raises(McpError):
        c.call_tool("nope", {})


def test_dead_process_raises():
    with pytest.raises((McpError, OSError)), McpClient(["/nonexistent/binary-xyz"]) as c:
        c.call_tool("x", {})


def test_handshake_timeout_kills_process():
    c = McpClient([sys.executable, SILENT_SERVER], read_timeout=2.0)
    with pytest.raises(McpError):
        c.__enter__()
    assert c._proc is not None
    assert c._proc.poll() is not None


def test_read_timeout_kills_process():
    with McpClient([sys.executable, HANG_SERVER], read_timeout=2.0) as c:
        with pytest.raises(McpError, match="timeout"):
            c.call_tool("anything", {})
        assert c._proc.poll() is not None
