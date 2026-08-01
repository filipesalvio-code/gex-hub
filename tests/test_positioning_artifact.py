from conftest import insert_key_level

import gex_scraper
import positioning_artifact


def _make_db(tmp_path):
    db_path = str(tmp_path / "gex_test.db")
    conn = gex_scraper.init_db(db_path)
    insert_key_level(conn, sym="SPX", trade_date="2026-07-30", upx=6300.0,
                     cws=6700.0, pws=5900.0, zero_g=6400.0)
    insert_key_level(conn, sym="SPX", trade_date="2026-07-31", upx=6400.0,
                     cws=6800.0, pws=6000.0, zero_g=6500.0, max_g=6700.0,
                     topabs=6750.0, gamma_not=1.23e9)
    insert_key_level(conn, sym="QQQ", trade_date="2026-07-31", upx=560.0,
                     cws=600.0, pws=520.0, zero_g=570.0, gamma_not=4.5e8)
    conn.close()
    return db_path


def test_build_artifact_aggregates_levels_from_injected_db(tmp_path, monkeypatch):
    db_path = _make_db(tmp_path)
    monkeypatch.setattr(positioning_artifact, "OI_GLOB",
                        str(tmp_path / "no-such" / "oi_*_*.parquet"))

    artifact = positioning_artifact.build_artifact(db_path=db_path)

    assert artifact["regime"] == {
        "gamma_not": 1.23e9,
        "upx": 6400.0,
        "zero_g": 6500.0,
        "trade_date": "2026-07-31",
    }
    assert artifact["walls"] == {
        "cws": 6800.0,
        "pws": 6000.0,
        "zero_g": 6500.0,
        "max_g": 6700.0,
        "topabs": 6750.0,
    }
    assert {r["sym"] for r in artifact["indices"]} == {"SPX", "QQQ"}
    assert all(r["trade_date"] == "2026-07-31" for r in artifact["indices"])
    assert [d["trade_date"] for d in artifact["drift"]] == ["2026-07-30", "2026-07-31"]
    assert artifact["positioning"] == {"strikes": [], "mm": [], "cust": []}
    assert artifact["oi_date"] is None


def test_build_artifact_handles_empty_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "empty.db")
    gex_scraper.init_db(db_path).close()
    monkeypatch.setattr(positioning_artifact, "OI_GLOB",
                        str(tmp_path / "no-such" / "oi_*_*.parquet"))

    artifact = positioning_artifact.build_artifact(db_path=db_path)

    assert artifact["indices"] == []
    assert artifact["drift"] == []
    assert artifact["regime"]["upx"] is None
    assert artifact["positioning"] == {"strikes": [], "mm": [], "cust": []}
