"""Tests for mindset prompts endpoints."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_list_prompts_returns_seeded(client):
    r = client.get("/api/mindset-prompts")
    assert r.status_code == 200
    prompts = r.json()
    assert len(prompts) >= 5
    texts = [p["text"] for p in prompts]
    assert any("judging your system" in t for t in texts)
    assert any("risking too much" in t for t in texts)
    assert any("good outcomes" in t for t in texts)
    assert any("abandoning your edge" in t for t in texts)
    assert any("chasing certainty" in t for t in texts)


def test_create_prompt_assigns_next_position(client):
    before = client.get("/api/mindset-prompts").json()
    max_pos = max((p["position"] for p in before), default=-1)
    r = client.post("/api/mindset-prompts", json={"text": "Test prompt"})
    assert r.status_code == 200
    assert r.json()["position"] == max_pos + 1
    client.delete(f"/api/mindset-prompts/{r.json()['id']}")


def test_patch_prompt(client):
    create = client.post("/api/mindset-prompts", json={"text": "Original"}).json()
    pid = create["id"]
    r = client.patch(f"/api/mindset-prompts/{pid}", json={"text": "Updated"})
    assert r.status_code == 200
    assert r.json()["text"] == "Updated"
    client.delete(f"/api/mindset-prompts/{pid}")


def test_delete_prompt(client):
    create = client.post("/api/mindset-prompts", json={"text": "Delete test"}).json()
    pid = create["id"]
    r = client.delete(f"/api/mindset-prompts/{pid}")
    assert r.status_code == 200
    after = client.get("/api/mindset-prompts").json()
    assert pid not in [p["id"] for p in after]
