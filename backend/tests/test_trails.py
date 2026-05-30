"""Tests for trail mutation endpoints."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def _make_entered_trade(client, pair="TRAILS1"):
    r = client.post("/api/trades", json={
        "pair": pair, "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    return r.json()["id"]


def test_post_trail_appends(client):
    tid = _make_entered_trade(client, pair="TRAILS_A")
    r = client.post(f"/api/trades/{tid}/trails", json={"price": 95.0})
    assert r.status_code == 200
    ts = r.json()["trailed_stops"]
    assert len(ts) == 1
    assert ts[0]["price"] == 95.0
    assert "at" in ts[0]


def test_post_trail_keeps_chronological_order(client):
    tid = _make_entered_trade(client, pair="TRAILS_B")
    client.post(f"/api/trades/{tid}/trails", json={"price": 95.0})
    client.post(f"/api/trades/{tid}/trails", json={"price": 105.0})
    client.post(f"/api/trades/{tid}/trails", json={"price": 110.0, "note": "swing high"})
    ts = client.get(f"/api/trades/{tid}").json()["trailed_stops"]
    assert [s["price"] for s in ts] == [95.0, 105.0, 110.0]
    assert ts[2]["note"] == "swing high"


def test_post_trail_rejects_non_entered_trade(client):
    tid = _make_entered_trade(client, pair="TRAILS_C")
    client.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 120.0,
    })
    r = client.post(f"/api/trades/{tid}/trails", json={"price": 115.0})
    assert r.status_code == 400


def test_post_trail_404_on_missing(client):
    r = client.post("/api/trades/999999/trails", json={"price": 100.0})
    assert r.status_code == 404


def test_delete_trail_by_index(client):
    tid = _make_entered_trade(client, pair="TRAILS_D")
    client.post(f"/api/trades/{tid}/trails", json={"price": 95.0})
    client.post(f"/api/trades/{tid}/trails", json={"price": 105.0})
    r = client.delete(f"/api/trades/{tid}/trails/0")
    assert r.status_code == 200
    ts = r.json()["trailed_stops"]
    assert len(ts) == 1
    assert ts[0]["price"] == 105.0


def test_delete_trail_out_of_range(client):
    tid = _make_entered_trade(client, pair="TRAILS_E")
    client.post(f"/api/trades/{tid}/trails", json={"price": 95.0})
    r = client.delete(f"/api/trades/{tid}/trails/5")
    assert r.status_code == 400
