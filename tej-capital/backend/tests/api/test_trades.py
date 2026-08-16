import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _acct(ac):
    r = await ac.post("/api/accounts", json={"name": "M", "broker": "IBKR", "currency": "USD", "account_type": "live"})
    return r.json()["id"]


@pytest.mark.asyncio
async def test_trade_without_risk_flagged_for_enrichment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        r = await ac.post("/api/trades", json={
            "account_id": aid,
            "instrument": "XAUUSD", "direction": "long",
            "entry_price": "2400.00", "position_size": "0.10",
            "opened_at": "2026-08-16T10:00:00+00:00",
        })
        assert r.status_code == 201
        trade_id = r.json()["id"]
        assert r.json()["enrichment_needed"] is True

        # /api/trades/enrichment is a global queue (no account filter per
        # spec), so scope the assertion to this test's own account to avoid
        # collisions with rows left by other test runs against the shared db.
        queue = await ac.get("/api/trades/enrichment")
        own = [row for row in queue.json() if row["account_id"] == aid]
        assert len(own) == 1
        assert own[0]["id"] == trade_id


@pytest.mark.asyncio
async def test_r_multiple_computed_on_read():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        r = await ac.post("/api/trades", json={
            "account_id": aid,
            "instrument": "XAUUSD", "direction": "long",
            "entry_price": "2400.00", "exit_price": "2430.00",
            "initial_stop": "2390.00", "position_size": "0.10",
            "risk_amount": "100.00", "gross_pnl": "300.00", "costs": "5.00",
            "opened_at": "2026-08-16T10:00:00+00:00",
            "closed_at": "2026-08-16T15:00:00+00:00",
        })
        assert r.status_code == 201
        # (300 - 5) / 100 = 2.95
        assert r.json()["r_multiple"] == pytest.approx(2.95)
