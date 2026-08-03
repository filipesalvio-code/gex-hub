"""Minimal stdio JSON-RPC client for the gex-hub MCP servers."""
import json
import queue
import subprocess
import sys
import threading
from typing import Self

from poller.normalize import ToolResult, parse_tool_text

MENTHORQ_ARGV = [sys.executable, "mcp/menthorq_mcp.py"]
SPOTGAMMA_ARGV = ["node", "spotgamma-mcp/server.js"]

_PROTOCOL = "2024-11-05"


class McpError(Exception):
    pass


class McpClient:
    def __init__(self, argv: list[str], cwd: str | None = None,
                 read_timeout: float = 60.0):
        self._argv, self._cwd = argv, cwd
        self._read_timeout = read_timeout
        self._proc: subprocess.Popen | None = None
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._next_id = 0

    def __enter__(self) -> Self:
        try:
            self._proc = subprocess.Popen(
                self._argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, cwd=self._cwd)
        except OSError as e:
            raise McpError(f"spawn failed: {e}") from e
        threading.Thread(target=self._pump, daemon=True).start()
        try:
            resp = self._rpc("initialize",
                             {"protocolVersion": _PROTOCOL, "capabilities": {},
                              "clientInfo": {"name": "gex-poller", "version": "0.1"}})
            if "error" in resp:
                raise McpError(f"initialize failed: {resp['error'].get('message')}")
            negotiated = resp.get("result", {}).get("protocolVersion")
            if negotiated != _PROTOCOL:
                raise McpError(
                    f"protocol mismatch: server negotiated {negotiated!r},"
                    f" client requires {_PROTOCOL!r}")
            self._rpc("notifications/initialized", is_notification=True)
        except Exception:
            self._kill()
            raise
        return self

    def __exit__(self, *exc) -> None:
        self._kill()

    def _kill(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.kill()
        if self._proc:
            self._proc.wait()

    def _pump(self) -> None:
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def _readline(self) -> str:
        try:
            line = self._lines.get(timeout=self._read_timeout)
        except queue.Empty:
            self._kill()
            raise McpError(f"read timeout after {self._read_timeout}s") from None
        if line is None:
            raise McpError("server closed stdout")
        return line

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
        while True:
            resp = json.loads(self._readline())
            if "id" not in resp or "method" in resp:
                continue  # server notification; not a response
            if resp["id"] != self._next_id:
                raise McpError(
                    f"unexpected response id {resp['id']!r}, expected {self._next_id}")
            return resp

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
