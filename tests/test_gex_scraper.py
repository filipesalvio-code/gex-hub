import builtins

import pytest

import gex_scraper


def test_token_needs_refresh_missing_token():
    assert gex_scraper.token_needs_refresh(None) is True
    assert gex_scraper.token_needs_refresh("") is True


def test_token_needs_refresh_future_token(future_token):
    assert gex_scraper.token_needs_refresh(future_token) is False


def test_refresh_token_via_webbridge_returns_token_without_disk(monkeypatch, future_token):
    calls = []

    def fake_webbridge(action, args, timeout=15.0):
        calls.append(action)
        if action == "find_tab":
            return {"ok": True, "data": {"success": True}}
        if action == "evaluate":
            return {"ok": True, "data": {"value": future_token}}
        raise AssertionError(f"unexpected action {action}")

    monkeypatch.setattr(gex_scraper, "_webbridge_call", fake_webbridge)
    monkeypatch.setattr(builtins, "open", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("token must never be written to disk")))

    token = gex_scraper.refresh_token_via_webbridge()

    assert token == future_token
    assert calls == ["find_tab", "evaluate"]


def _fake_payload(sym="SPX"):
    return {"data": [{
        "sym": sym,
        "trade_date": "2026-07-31",
        "upx": 6400.0,
        "callwallstrike": 6800.0,
        "putwallstrike": 6000.0,
    }]}


def test_run_prefers_env_token(monkeypatch, tmp_path, future_token):
    monkeypatch.setenv("SG_TOKEN", future_token)

    def _refresh_must_not_run(*a, **k):
        raise AssertionError("WebBridge refresh must not run when $SG_TOKEN is valid")

    monkeypatch.setattr(gex_scraper, "refresh_token_via_webbridge", _refresh_must_not_run)

    seen = {}

    def fake_fetch(path, token, timeout=30.0):
        seen["token"] = token
        return _fake_payload()

    monkeypatch.setattr(gex_scraper, "fetch_json", fake_fetch)

    summary = gex_scraper.run(db_path=str(tmp_path / "test.db"))

    assert seen["token"] == future_token
    assert summary["token_refreshed"] is False
    assert summary["status"] == "ok"
    assert summary["key_levels_rows"] == 1


def test_run_falls_back_to_webbridge_when_env_unset(monkeypatch, tmp_path, future_token):
    monkeypatch.delenv("SG_TOKEN", raising=False)

    refresh_calls = []

    def fake_refresh(timeout=15.0):
        refresh_calls.append(timeout)
        return future_token

    monkeypatch.setattr(gex_scraper, "refresh_token_via_webbridge", fake_refresh)

    seen = {}

    def fake_fetch(path, token, timeout=30.0):
        seen["token"] = token
        return _fake_payload()

    monkeypatch.setattr(gex_scraper, "fetch_json", fake_fetch)

    summary = gex_scraper.run(db_path=str(tmp_path / "test.db"))

    assert refresh_calls, "WebBridge refresh should be attempted when $SG_TOKEN is unset"
    assert seen["token"] == future_token
    assert summary["token_refreshed"] is True
    assert summary["status"] == "ok"


def test_run_raises_without_any_token(monkeypatch, tmp_path):
    monkeypatch.delenv("SG_TOKEN", raising=False)
    monkeypatch.setattr(gex_scraper, "refresh_token_via_webbridge", lambda *a, **k: None)

    with pytest.raises(RuntimeError, match="No sgToken"):
        gex_scraper.run(db_path=str(tmp_path / "test.db"))
