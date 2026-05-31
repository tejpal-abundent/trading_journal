"""Tests for trading rules endpoints."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_list_rules_returns_seeded(client):
    r = client.get("/api/rules")
    assert r.status_code == 200
    rules = r.json()
    # 4 seeded rules should exist
    assert len(rules) >= 4
    titles = [x["title"] for x in rules]
    assert any("Cut losses" in t for t in titles)
    assert any("Quality trades" in t for t in titles)
    assert any("4%" in t for t in titles)
    assert any("4H candle close" in t for t in titles)


def test_create_rule_assigns_next_position(client):
    before = client.get("/api/rules").json()
    max_pos = max((r["position"] for r in before), default=-1)
    r = client.post("/api/rules", json={"title": "Test rule", "body": "Body"})
    assert r.status_code == 200
    created = r.json()
    assert created["position"] == max_pos + 1
    assert created["title"] == "Test rule"
    # cleanup
    client.delete(f"/api/rules/{created['id']}")


def test_patch_rule(client):
    create = client.post("/api/rules", json={"title": "Patch test", "body": "x"}).json()
    rid = create["id"]
    r = client.patch(f"/api/rules/{rid}", json={"title": "Patched", "body": "y"})
    assert r.status_code == 200
    assert r.json()["title"] == "Patched"
    assert r.json()["body"] == "y"
    client.delete(f"/api/rules/{rid}")


def test_delete_rule(client):
    create = client.post("/api/rules", json={"title": "Delete test"}).json()
    rid = create["id"]
    r = client.delete(f"/api/rules/{rid}")
    assert r.status_code == 200
    after = client.get("/api/rules").json()
    assert rid not in [x["id"] for x in after]
