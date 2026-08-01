import base64
import json
import socket
import time

import pytest

import gex_scraper


def _b64(obj) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def make_jwt(exp: int) -> str:
    return f"{_b64({'alg': 'HS256', 'typ': 'JWT'})}.{_b64({'exp': exp})}.fakesig"


@pytest.fixture
def future_token() -> str:
    return make_jwt(int(time.time()) + 7 * 24 * 3600)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _blocked(*args, **kwargs):
        raise AssertionError("network access is forbidden in tests")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)


@pytest.fixture
def mem_db():
    conn = gex_scraper.init_db(":memory:")
    yield conn
    conn.close()


def insert_key_level(conn, *, sym="SPX", trade_date="2026-07-31", upx=6400.0,
                     cws=6800.0, pws=6000.0, zero_g=6500.0, max_g=6700.0,
                     topabs=6750.0, gamma_not=1.23e9):
    conn.execute(
        "INSERT OR REPLACE INTO key_levels "
        "(sym, trade_date, pulled_at, raw_json, upx, callwallstrike, putwallstrike,"
        " zero_g_strike, max_g_strike, topabs_strike, gamma_not)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (sym, trade_date, "2026-07-31T12:00:00+00:00", "{}", upx, cws, pws,
         zero_g, max_g, topabs, gamma_not),
    )
    conn.commit()
