"""Smoke test for GET /api/dashboard."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_dashboard_endpoint_returns_full_shape(client):
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    j = r.json()
    for key in ("this_week", "this_month", "ytd", "open_trades",
                "monthly", "weekly", "daily_heatmap", "equity_curve"):
        assert key in j, f"missing key: {key}"
    assert len(j["monthly"]) == 12
    assert len(j["weekly"]) == 4
    assert len(j["daily_heatmap"]) == 90
