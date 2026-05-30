"""Tests for PATCH /api/trades/{id} and POST /api/trades/{id}/close."""
import time
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def _create_open_trade(client, pair="BTCUSDT"):
    r = client.post("/api/trades", json={
        "pair": pair, "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    return r.json()["id"]


def test_patch_bumps_updated_at(client):
    tid = _create_open_trade(client, pair="EDIT1")
    before = client.get(f"/api/trades/{tid}").json()["updated_at"]
    time.sleep(1.1)
    client.patch(f"/api/trades/{tid}", json={"notes": "hello"})
    after = client.get(f"/api/trades/{tid}").json()["updated_at"]
    assert after is not None
    assert after != before


def test_patch_recalcs_rr_when_exit_changes(client):
    tid = _create_open_trade(client, pair="EDIT2")
    client.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 130.0,
    })
    before_rr = client.get(f"/api/trades/{tid}").json()["rr_achieved"]
    assert before_rr == 3.0
    client.patch(f"/api/trades/{tid}", json={"exit_price": 120.0})
    after_rr = client.get(f"/api/trades/{tid}").json()["rr_achieved"]
    assert after_rr == 2.0


def test_patch_preserves_manual_pnl_override(client):
    tid = _create_open_trade(client, pair="EDIT3")
    client.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 130.0, "pnl": 12345.0,
    })
    assert client.get(f"/api/trades/{tid}").json()["pnl"] == 12345.0
    client.patch(f"/api/trades/{tid}", json={"notes": "still 12345"})
    assert client.get(f"/api/trades/{tid}").json()["pnl"] == 12345.0


def test_patch_trailed_stops_sorted_by_at(client):
    tid = _create_open_trade(client, pair="EDIT4")
    client.patch(f"/api/trades/{tid}", json={
        "trailed_stops": [
            {"price": 120.0, "at": "2026-05-30T16:00:00Z"},
            {"price": 105.0, "at": "2026-05-30T14:00:00Z"},
            {"price": 115.0, "at": "2026-05-30T15:00:00Z"},
        ]
    })
    ts = client.get(f"/api/trades/{tid}").json()["trailed_stops"]
    assert [s["price"] for s in ts] == [105.0, 115.0, 120.0]


def test_close_recalcs_locked_r_with_trails(client):
    tid = _create_open_trade(client, pair="EDIT5")
    client.patch(f"/api/trades/{tid}", json={
        "trailed_stops": [
            {"price": 105.0, "at": "2026-05-30T14:00:00Z"},
            {"price": 115.0, "at": "2026-05-30T15:00:00Z"},
            {"price": 125.0, "at": "2026-05-30T16:00:00Z"},
        ]
    })
    client.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 135.0,
    })
    t = client.get(f"/api/trades/{tid}").json()
    assert t["rr_achieved"] == 3.5
    assert t["r_locked_at_penultimate_trail"] == 2.0
