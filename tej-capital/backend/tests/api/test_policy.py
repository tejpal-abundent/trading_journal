import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_amendment_blocked_during_drawdown_without_override(monkeypatch):
    from app.services import drawdown_guard
    monkeypatch.setattr(drawdown_guard, "current_drawdown_pct", lambda db: -0.08)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/policy/limits/risk_per_trade", json={
            "threshold": "0.01", "unit": "pct", "effective_from": "2026-08-16",
            "committed_action": "reduce to 0.5% and step away",
            "reason": "want to be more careful",
        })
        assert r.status_code == 409
        assert r.json()["detail"]["error"] == "amendment_blocked_during_drawdown"


@pytest.mark.asyncio
async def test_amendment_allowed_with_override_and_long_reason(monkeypatch):
    from app.services import drawdown_guard
    monkeypatch.setattr(drawdown_guard, "current_drawdown_pct", lambda db: -0.08)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/policy/limits/risk_per_trade", json={
            "threshold": "0.005", "unit": "pct", "effective_from": "2026-08-16",
            "committed_action": "reduce to 0.5% for next 30 days",
            "reason": "explicitly overriding drawdown block; documenting: I am cutting risk in half",
            "override_during_drawdown": True,
        })
        assert r.status_code == 201
        assert r.json()["is_override_during_drawdown"] is True


@pytest.mark.asyncio
async def test_set_limit_happy_path_when_not_in_drawdown():
    """No monkeypatch here: drawdown_guard.current_drawdown_pct runs for real
    against the app DB. With no metric snapshot present it returns 0.0, which
    is not a drawdown, so the amendment should go through without an override."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/policy/limits/daily_loss", json={
            "threshold": "0.02", "unit": "pct", "effective_from": "2026-08-16",
            "committed_action": "stop trading for the day",
            "reason": "initial policy setup for daily loss limit",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["limit_type"] == "daily_loss"
        assert body["is_override_during_drawdown"] is False
        assert body["effective_to"] is None

        listing = await ac.get("/api/policy/limits")
        assert listing.status_code == 200
        daily_loss_rows = [row for row in listing.json() if row["limit_type"] == "daily_loss"]
        assert len(daily_loss_rows) == 1
        assert daily_loss_rows[0]["id"] == body["id"]


@pytest.mark.asyncio
async def test_setting_new_limit_closes_previous_version():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        first = await ac.post("/api/policy/limits/weekly_loss", json={
            "threshold": "0.05", "unit": "pct", "effective_from": "2026-08-16",
            "committed_action": "stop trading for the week",
            "reason": "initial weekly loss limit",
        })
        assert first.status_code == 201
        first_id = first.json()["id"]

        second = await ac.post("/api/policy/limits/weekly_loss", json={
            "threshold": "0.04", "unit": "pct", "effective_from": "2026-08-16",
            "committed_action": "stop trading for the week, tighter",
            "reason": "tightening weekly loss limit after review",
        })
        assert second.status_code == 201
        assert second.json()["previous_limit_id"] == first_id

        listing = await ac.get("/api/policy/limits")
        weekly_rows = [row for row in listing.json() if row["limit_type"] == "weekly_loss"]
        # only one open (effective_to IS NULL) version remains
        assert len(weekly_rows) == 1
        assert weekly_rows[0]["id"] == second.json()["id"]


@pytest.mark.asyncio
async def test_document_get_and_patch_section():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        patch = await ac.patch("/api/policy/document/mandate", json={
            "body": "Preserve capital first; compound second.",
        })
        assert patch.status_code == 200
        assert patch.json()["section"] == "mandate"
        assert patch.json()["body"] == "Preserve capital first; compound second."

        listing = await ac.get("/api/policy/document")
        assert listing.status_code == 200
        sections = {row["section"]: row["body"] for row in listing.json()}
        assert sections["mandate"] == "Preserve capital first; compound second."


@pytest.mark.asyncio
async def test_breaches_lists_only_unresolved():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/policy/breaches")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        for row in r.json():
            assert row["resolved_on"] is None
