"""Tests for the new POST /api/trades creation flow."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_post_trades_creates_entered_with_risk(client):
    r = client.post("/api/trades", json={
        "pair": "NEW1", "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    assert r.status_code == 200
    t = r.json()
    assert t["status"] == "entered"
    assert t["entry_price"] == 100.0
    assert t["risk_dollars"] == 10.0
    assert t["risk_percent"] == 1.0


def test_post_trades_rejects_without_required_fields(client):
    r = client.post("/api/trades", json={
        "pair": "NEW2", "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        # Missing entry_price, stop_loss, position_size, account_size
    })
    assert r.status_code == 422


def test_enter_endpoint_removed(client):
    create = client.post("/api/trades", json={
        "pair": "NEW3", "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    tid = create.json()["id"]
    r = client.post(f"/api/trades/{tid}/enter", json={
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    assert r.status_code == 404  # route removed


def test_skip_endpoint_removed(client):
    create = client.post("/api/trades", json={
        "pair": "NEW4", "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    tid = create.json()["id"]
    r = client.post(f"/api/trades/{tid}/skip", json={"skip_reason": "x"})
    assert r.status_code == 404
