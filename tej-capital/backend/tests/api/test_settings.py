from decimal import Decimal

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete

from app.db import SessionLocal
from app.domain.settings import Settings as SettingsModel
from app.main import app


async def _reset_settings_row():
    """The settings row is a real singleton (id=1) persisted in the same
    non-ephemeral database the app itself uses (app.db.engine), so it survives
    across pytest invocations. Delete it directly so the auto-create-defaults
    assertion below is deterministic regardless of prior runs."""
    async with SessionLocal() as s:
        await s.execute(delete(SettingsModel).where(SettingsModel.id == 1))
        await s.commit()


@pytest.mark.asyncio
async def test_get_settings_auto_creates_singleton_row_with_defaults():
    await _reset_settings_row()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/settings")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == 1
        assert body["base_currency"] == "USD"
        assert Decimal(body["starting_capital"]) == Decimal("15000")
        assert Decimal(body["risk_free_rate"]) == Decimal("0.04")


@pytest.mark.asyncio
async def test_get_settings_is_idempotent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        first = await ac.get("/api/settings")
        second = await ac.get("/api/settings")
        assert first.json()["id"] == second.json()["id"] == 1


@pytest.mark.asyncio
async def test_patch_settings_updates_fields_and_preserves_decimal_precision():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.get("/api/settings")  # ensure row exists

        patch = await ac.patch("/api/settings", json={
            "starting_capital": "25000.12345678",
            "trading_days_per_year": 260,
        })
        assert patch.status_code == 200
        body = patch.json()
        assert Decimal(body["starting_capital"]) == Decimal("25000.12345678")
        assert body["trading_days_per_year"] == 260

        # unspecified fields are untouched
        assert body["base_currency"] == "USD"


@pytest.mark.asyncio
async def test_patch_settings_only_touches_provided_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        before = await ac.get("/api/settings")
        prior_rate = before.json()["risk_free_rate"]

        patch = await ac.patch("/api/settings", json={"base_currency": "EUR"})
        assert patch.status_code == 200
        body = patch.json()
        assert body["base_currency"] == "EUR"
        assert body["risk_free_rate"] == prior_rate

        # restore to avoid polluting other tests relying on default currency
        await ac.patch("/api/settings", json={"base_currency": "USD"})
