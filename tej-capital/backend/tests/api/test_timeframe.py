from decimal import Decimal

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete

from app.db import SessionLocal
from app.domain.settings import Settings as SettingsModel
from app.main import app


async def _acct(ac):
    r = await ac.post("/api/accounts", json={"name": "M", "broker": "IBKR", "currency": "USD", "account_type": "live"})
    return r.json()["id"]


async def _mark_nav(ac, account_id: str, equity: str = "15000.00", as_of_date: str = "2026-08-16"):
    r = await ac.post(f"/api/accounts/{account_id}/nav", json={
        "as_of_date": as_of_date, "closing_equity": equity,
    })
    assert r.status_code == 201
    return r.json()


async def _reset_settings_row():
    """The settings row is a real singleton (id=1) persisted in the same
    non-ephemeral database the app itself uses. Delete it so a subsequent
    GET auto-creates a fresh row with risk_by_timeframe left at its column
    default (NULL), matching test_settings.py's established pattern."""
    async with SessionLocal() as s:
        await s.execute(delete(SettingsModel).where(SettingsModel.id == 1))
        await s.commit()


BASE_TRADE = {
    "instrument": "XAUUSD", "direction": "long",
    "entry_price": "2400.00", "position_size": "0.10",
    "opened_at": "2026-08-16T10:00:00+00:00",
}


@pytest.mark.asyncio
async def test_trade_with_tf_and_risk_below_threshold_succeeds():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        await _mark_nav(ac, aid, "15000.00")

        # 0.2% of 15000 = 30.00, below the 0.25% (37.50) limit for 1m.
        r = await ac.post("/api/trades", json={
            **BASE_TRADE, "account_id": aid, "timeframe": "1m", "risk_amount": "30.00",
        })
        assert r.status_code == 201
        assert r.json()["timeframe"] == "1m"


@pytest.mark.asyncio
async def test_trade_with_tf_and_risk_above_threshold_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        await _mark_nav(ac, aid, "15000.00")

        # 0.3% of 15000 = 45.00, above the 0.25% (37.50) limit for 1m.
        r = await ac.post("/api/trades", json={
            **BASE_TRADE, "account_id": aid, "timeframe": "1m", "risk_amount": "45.00",
        })
        assert r.status_code == 400
        detail = r.json()["detail"]
        assert detail["error"] == "risk_exceeds_timeframe_limit"
        assert detail["timeframe"] == "1m"
        assert "hint" in detail


@pytest.mark.asyncio
async def test_trade_without_tf_skips_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        await _mark_nav(ac, aid, "15000.00")

        # Risk far above any threshold, but no timeframe -> validation is skipped.
        r = await ac.post("/api/trades", json={
            **BASE_TRADE, "account_id": aid, "risk_amount": "10000.00",
        })
        assert r.status_code == 201
        assert r.json()["timeframe"] is None


@pytest.mark.asyncio
async def test_trade_without_risk_skips_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        await _mark_nav(ac, aid, "15000.00")

        # Timeframe present but risk_amount missing (enrichment queue path).
        r = await ac.post("/api/trades", json={
            **BASE_TRADE, "account_id": aid, "timeframe": "1m",
        })
        assert r.status_code == 201
        assert r.json()["enrichment_needed"] is True


@pytest.mark.asyncio
async def test_trade_with_no_nav_history_skips_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        # No NAV mark recorded for this account at all.

        r = await ac.post("/api/trades", json={
            **BASE_TRADE, "account_id": aid, "timeframe": "1m", "risk_amount": "10000.00",
        })
        assert r.status_code == 201


@pytest.mark.asyncio
async def test_enrich_trade_re_validates_tf_risk():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        await _mark_nav(ac, aid, "15000.00")

        created = await ac.post("/api/trades", json={**BASE_TRADE, "account_id": aid})
        assert created.status_code == 201
        trade_id = created.json()["id"]
        assert created.json()["risk_amount"] is None

        # PATCH adds a 1m timeframe with a risk (45.00 / 15000 = 0.3%) above
        # the 0.25% 1m limit -> should be rejected just like at creation time.
        patched = await ac.patch(f"/api/trades/{trade_id}", json={
            "timeframe": "1m", "risk_amount": "45.00",
        })
        assert patched.status_code == 400
        detail = patched.json()["detail"]
        assert detail["error"] == "risk_exceeds_timeframe_limit"


@pytest.mark.asyncio
async def test_settings_default_risk_by_timeframe_when_null():
    await _reset_settings_row()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/settings")
        assert r.status_code == 200
        body = r.json()
        risk_map = body["risk_by_timeframe"]
        assert Decimal(str(risk_map["1m"])) == Decimal("0.0025")
        assert Decimal(str(risk_map["5m"])) == Decimal("0.0025")
        assert Decimal(str(risk_map["15m"])) == Decimal("0.005")
        assert Decimal(str(risk_map["1w"])) == Decimal("0.005")
