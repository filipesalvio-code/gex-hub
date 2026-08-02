import json
import sys
from pathlib import Path

import pytest

FAKE_SERVER = str(Path(__file__).parent / "fake_mcp_server.py")


def pytest_addoption(parser):
    parser.addoption("--runlive", action="store_true", help="run live e2e tests")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runlive"):
        return
    skip = pytest.mark.skip(reason="needs --runlive")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def fake_mcp(monkeypatch):
    def _make(fixture: dict[str, str]):
        env_fixture = json.dumps(fixture)
        monkeypatch.setenv("FAKE_MCP_FIXTURE", env_fixture)
        from poller.mcp_client import McpClient
        return McpClient([sys.executable, FAKE_SERVER])
    return _make
