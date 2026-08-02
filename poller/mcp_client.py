"""Minimal stdio JSON-RPC client for the gex-hub MCP servers."""
import json
import subprocess
import sys
from typing import Self

from poller.normalize import ToolResult, parse_tool_text

MENTHORQ_ARGV = [sys.executable, "mcp/menthorq_mcp.py"]
SPOTGAMMA_ARGV = ["node", "spotgamma-mcp/server.js"]

_PROTOCOL = "2024-11-05"


class McpError(Exception):
    pass


class McpClient:
    def __init__(self, argv: list[str], cwd: str | None = None):
        self._argv, self._cwd = argv, cwd
        self._proc: subprocess.Popen | None = None
        self._next_id = 0

    def __enter__(self) -> Self:
        try:
            self._proc = subprocess.Popen(
                self._argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, cwd=self._cwd)
        except OSError as e:
            raise McpError(f"spawn failed: {e}") from e
        self._rpc("initialize", {"protocolVersion": _PROTOCOL, "capabilities": {},
                                 "clientInfo": {"name": "gex-poller", "version": "0.1"}})
        self._rpc("notifications/initialized", is_notification=True)
        return self

    def __exit__(self, *exc) -> None:
        if self._proc:
            self._proc.kill()
            self._proc.wait()

    def _rpc(self, method: str, params: dict | None = None,
             is_notification: bool = False) -> dict:
        if not self._proc or self._proc.poll() is not None:
            raise McpError("server process is dead")
        self._next_id += 1
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not is_notification:
            msg["id"] = self._next_id
        assert self._proc.stdin and self._proc.stdout
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()
        if is_notification:
            return {}
        line = self._proc.stdout.readline()
        if not line:
            raise McpError("server closed stdout")
        return json.loads(line)

    def call_tool(self, name: str, arguments: dict) -> ToolResult:
        r = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if "error" in r:
            raise McpError(f"{name}: {r['error'].get('message')}")
        result = r.get("result", {})
        if result.get("isError"):
            text = result["content"][0]["text"] if result.get("content") else "isError"
            return ToolResult(name, ok=False, error=text[:300], raw=text)
        text = result["content"][0]["text"]
        return parse_tool_text(name, text)
