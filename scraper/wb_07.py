"""WebBridge helper for sg-agent-07: POST evaluate/navigate to the daemon."""
import json
import sys
import urllib.request

SESSION = "spotgamma-scrape-07"
DAEMON = "http://127.0.0.1:10086/command"


def cmd(action, args, timeout=90):
    body = json.dumps({"action": action, "args": args, "session": SESSION}).encode()
    req = urllib.request.Request(
        DAEMON, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def evaluate(code, timeout=90):
    return cmd("evaluate", {"code": code}, timeout)


def evaluate_value(code, timeout=90):
    """Evaluate and decode the returned string payload as JSON if possible."""
    out = evaluate(code, timeout)
    if not out.get("ok"):
        raise RuntimeError(json.dumps(out))
    data = out["data"]
    val = data.get("value")
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return val
    return val


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            code = f.read()
    else:
        code = sys.stdin.read()
    result = evaluate_value(code)
    print(json.dumps(result, indent=2, ensure_ascii=False))
