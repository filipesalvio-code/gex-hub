#!/usr/bin/env python3
"""Helper: send an evaluate request to WebBridge daemon for a given session.

Usage: python3 wb_eval.py <session> <js_file> [timeout_s]
Prints the daemon's JSON response (value string pretty-printed if JSON).
"""
import json
import sys
import urllib.request


def evaluate(session: str, code: str, timeout: int = 120) -> dict:
    payload = json.dumps({
        "action": "evaluate",
        "args": {"code": code},
        "session": session,
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:10086/command",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    session = sys.argv[1]
    with open(sys.argv[2]) as f:
        code = f.read()
    timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 120
    res = evaluate(session, code, timeout)
    val = res.get("data", {}).get("value")
    if isinstance(val, str):
        try:
            print(json.dumps(json.loads(val), indent=1, ensure_ascii=False))
            return
        except Exception:
            print(val)
            return
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
