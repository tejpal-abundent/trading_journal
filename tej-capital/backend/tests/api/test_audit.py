import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


async def _acct(ac):
    r = await ac.post("/api/accounts", json={
        "name": "Audit Test", "broker": "IBKR", "currency": "USD", "account_type": "live",
    })
    return r.json()["id"]


async def _seed_correction(ac) -> str:
    """Creates a trade then corrects an economic field, producing a
    tej_corrections_ledger row. Returns the correction reason used."""
    aid = await _acct(ac)
    trade = await ac.post("/api/trades", json={
        "account_id": aid,
        "instrument": "XAUUSD",
        "direction": "long",
        "entry_price": "2400.00",
        "exit_price": "2410.00",
        "initial_stop": "2390.00",
        "position_size": "0.10",
        "risk_amount": "100.00",
        "gross_pnl": "50.00",
        "costs": "5.00",
        "opened_at": "2026-08-16T10:00:00+00:00",
        "closed_at": "2026-08-16T15:00:00+00:00",
    })
    trade_id = trade.json()["id"]
    reason = "broker statement had a fat-finger fill price"
    r = await ac.post(f"/api/trades/{trade_id}/correct", json={
        "exit_price": "2412.00",
        "reason": reason,
    })
    assert r.status_code == 200, r.text
    return reason


async def _seed_amendment(ac) -> str:
    """Creates a policy limit, producing a tej_policy_amendments row."""
    reason = "initial monthly loss limit setup for audit feed test"
    r = await ac.post("/api/policy/limits/monthly_loss", json={
        "threshold": "0.06", "unit": "pct", "effective_from": "2026-08-16",
        "committed_action": "halt trading for the month",
        "reason": reason,
    })
    assert r.status_code == 201, r.text
    return reason


@pytest.mark.asyncio
async def test_audit_feed_includes_both_correction_and_amendment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        correction_reason = await _seed_correction(ac)
        amendment_reason = await _seed_amendment(ac)

        r = await ac.get("/api/audit")
        assert r.status_code == 200
        rows = r.json()
        types = {row["type"] for row in rows}
        assert "correction" in types
        assert "amendment" in types

        reasons = {row["reason"] for row in rows}
        assert correction_reason in reasons
        assert amendment_reason in reasons


@pytest.mark.asyncio
async def test_audit_feed_filters_by_type_correction():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await _seed_correction(ac)
        await _seed_amendment(ac)

        r = await ac.get("/api/audit?type=correction")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        assert all(row["type"] == "correction" for row in rows)


@pytest.mark.asyncio
async def test_audit_feed_filters_by_type_amendment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await _seed_correction(ac)
        await _seed_amendment(ac)

        r = await ac.get("/api/audit?type=amendment")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        assert all(row["type"] == "amendment" for row in rows)


@pytest.mark.asyncio
async def test_audit_feed_filters_by_since_excludes_old_entries():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await _seed_correction(ac)
        await _seed_amendment(ac)

        # Far-future `since` should exclude everything seeded just now.
        r = await ac.get("/api/audit?since=2099-01-01")
        assert r.status_code == 200
        assert r.json() == []

        # A `since` in the past should include what was just seeded.
        r2 = await ac.get("/api/audit?since=2020-01-01")
        assert r2.status_code == 200
        assert len(r2.json()) >= 2


@pytest.mark.asyncio
async def test_audit_feed_items_have_expected_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await _seed_correction(ac)

        r = await ac.get("/api/audit?type=correction")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        for row in rows:
            assert "id" in row
            assert "type" in row
            assert "occurred_at" in row
            assert "reason" in row
            assert "details" in row
