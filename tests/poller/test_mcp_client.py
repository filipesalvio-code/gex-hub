import json

import pytest

from poller.mcp_client import McpClient, McpError

pytestmark = pytest.mark.integration


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
