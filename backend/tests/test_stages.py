import os
os.environ.pop("TURSO_DB_URL", None)

import sys
from fastapi.testclient import TestClient


def _client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for m in list(sys.modules):
        if m in ("main", "models", "database", "migrations"):
            sys.modules.pop(m)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import main
    db_path = os.path.join(os.path.dirname(main.__file__), "trading_journal.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    main.startup()
    return TestClient(main.app)


def test_full_stage_flow(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/trades", json={
        "pair": "XAU/USD", "direction": "LONG", "timeframe": "4H",
        "setup_score": 80, "verdict": "B SETUP",
        "criteria_checked": ["trend","zone","signal","failure"],
        "planned_entry": 2400.0, "planned_stop": 2380.0,
        "planned_target": 2440.0, "planned_rr": 2.0,
    })
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    assert r.json()["status"] == "planned"

    r = c.post(f"/api/trades/{tid}/enter", json={
        "entry_price": 2402.0, "stop_loss": 2380.0,
        "position_size": 1.0, "account_size": 10000.0,
        "entry_timing": "on_time",
        "emotions_entry": ["confident"],
    })
    assert r.json()["status"] == "entered"
    assert abs(r.json()["risk_dollars"] - 22.0) < 0.001
    assert abs(r.json()["risk_percent"] - 0.22) < 0.001

    r = c.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 2440.0,
        "pnl": 38.0, "rr_achieved": 1.7,
        "rules_followed": True,
        "mistake_tags": [], "emotions_exit": ["calm"],
        "lessons": "Patience paid off",
    })
    assert r.json()["status"] == "win"
    assert r.json()["rules_followed"] is True
    assert "calm" in r.json()["emotions_exit"]


def test_skip_flow(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/trades", json={
        "pair": "EUR/USD", "direction": "SHORT", "timeframe": "1H",
        "setup_score": 60, "verdict": "C SETUP",
        "criteria_checked": ["trend","zone","signal","failure"],
    })
    tid = r.json()["id"]
    r = c.post(f"/api/trades/{tid}/skip", json={
        "skip_reason": "News in 1h", "emotions_entry": ["patient"]
    })
    assert r.json()["status"] == "skipped"
    assert r.json()["skip_reason"] == "News in 1h"
