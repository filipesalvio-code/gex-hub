"""Shared API client for MenthorQ scraping agents.

Auth: fetches a fresh access token from the open dashboard.menthorq.io tab
via the WebBridge daemon (the user's own logged-in Chrome session). The token
is cached in-memory only, never written to disk or the database.

Usage:
    import sys; sys.path.insert(0, 'scraper')
    from mq_api import get
    status, data = get('clickhouse-api', '/api/web/v1/gamma-levels/SPX/eod')
"""
import json
import time
import urllib.error
import urllib.request

BRIDGE = "http://127.0.0.1:10086/command"
SESSION = "menthorq-scrape"
GATEWAY = "https://gateway.menthorq.io"

_token_cache = {"value": None, "fetched_at": 0.0}


def get_token(force: bool = False) -> str:
    """Fetch a fresh accessToken from the open dashboard tab (cached ~5 min)."""
    now = time.time()
    if not force and _token_cache["value"] and now - _token_cache["fetched_at"] < 300:
        return _token_cache["value"]
    code = (
        "(async()=>{const r=await fetch('/api/auth/session');"
        "const j=await r.json();return j.accessToken||''})()"
    )
    body = json.dumps({"action": "evaluate", "args": {"code": code},
                       "session": SESSION}).encode()
    req = urllib.request.Request(BRIDGE, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.loads(resp.read())
    token = (out.get("data") or {}).get("value") or ""
    if not token:
        raise RuntimeError(f"no accessToken from dashboard tab: {out!r}")
    _token_cache.update(value=token, fetched_at=now)
    return token


def _url(service: str, path: str) -> str:
    if path.startswith("http"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return f"{GATEWAY}/{service}{path}"


def get(service: str, path: str, retries: int = 3, timeout: int = 60):
    """GET gateway endpoint. Returns (http_status, parsed_json_or_text)."""
    url = _url(service, path)
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {get_token(force=attempt > 0)}",
                          "Accept": "application/json",
                          "Origin": "https://dashboard.menthorq.io"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", "replace")
                try:
                    return resp.status, json.loads(text)
                except json.JSONDecodeError:
                    return resp.status, {"_raw": text[:50000]}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:2000]
            if e.code == 429 or e.code >= 500:
                last_err = f"{e.code} {body}"
                time.sleep(2 * (attempt + 1))
                continue
            return e.code, {"_error": body}
        except Exception as e:
            last_err = repr(e)
            time.sleep(2 * (attempt + 1))
    return 0, {"_error": f"failed after {retries} tries: {last_err}"}


def path_of(service: str, path: str) -> str:
    """Absolute URL for a service+path (for logging/saving)."""
    return _url(service, path)
