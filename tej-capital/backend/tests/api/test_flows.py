import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _make_account(ac):
    r = await ac.post("/api/accounts", json={
        "name": "Main", "broker": "IBKR", "currency": "USD",
        "account_type": "live",
    })
    return r.json()["id"]


@pytest.mark.asyncio
async def test_create_flow_returns_201():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        r = await ac.post(f"/api/accounts/{aid}/flows", json={
            "as_of_date": "2026-08-16", "amount": "1000.00",
            "flow_type": "deposit",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["account_id"] == aid
        assert body["amount"] == "1000.00000000"
        assert body["flow_type"] == "deposit"
        assert body["flow_timing"] == "end_of_day"
        assert body["superseded_by"] is None


@pytest.mark.asyncio
async def test_amount_zero_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        r = await ac.post(f"/api/accounts/{aid}/flows", json={
            "as_of_date": "2026-08-16", "amount": "0",
            "flow_type": "deposit",
        })
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_negative_amount_allowed_for_withdrawal():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        r = await ac.post(f"/api/accounts/{aid}/flows", json={
            "as_of_date": "2026-08-16", "amount": "-500.00",
            "flow_type": "withdrawal",
        })
        assert r.status_code == 201
        assert r.json()["amount"] == "-500.00000000"


@pytest.mark.asyncio
async def test_multiple_flows_same_day_allowed_R2():
    # R2: flows are never profit, and there's no per-day uniqueness on
    # cash flows (unlike NAV marks) — a deposit and a fee can land same day.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        first = await ac.post(f"/api/accounts/{aid}/flows", json={
            "as_of_date": "2026-08-16", "amount": "1000.00", "flow_type": "deposit",
        })
        second = await ac.post(f"/api/accounts/{aid}/flows", json={
            "as_of_date": "2026-08-16", "amount": "-25.00", "flow_type": "platform_fee",
        })
        assert first.status_code == 201
        assert second.status_code == 201
        listing = await ac.get(f"/api/accounts/{aid}/flows?since=2026-08-16")
        assert len(listing.json()) == 2


@pytest.mark.asyncio
async def test_correction_creates_new_row_and_supersedes_old_R1():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        first = await ac.post(f"/api/accounts/{aid}/flows", json={
            "as_of_date": "2026-08-16", "amount": "1000.00", "flow_type": "deposit",
        })
        original_id = first.json()["id"]
        corr = await ac.post(f"/api/accounts/{aid}/flows/correct", json={
            "id": original_id, "as_of_date": "2026-08-16", "amount": "1050.00",
            "flow_type": "deposit", "reason": "broker restated deposit amount",
        })
        assert corr.status_code == 201
        assert corr.json()["id"] != original_id
        assert corr.json()["amount"] == "1050.00000000"

        listing = await ac.get(f"/api/accounts/{aid}/flows?since=2026-08-16")
        rows = listing.json()
        assert len(rows) == 1
        assert rows[0]["id"] != original_id
        assert rows[0]["amount"] == "1050.00000000"


@pytest.mark.asyncio
async def test_correction_reason_min_length():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        first = await ac.post(f"/api/accounts/{aid}/flows", json={
            "as_of_date": "2026-08-16", "amount": "1000.00", "flow_type": "deposit",
        })
        bad = await ac.post(f"/api/accounts/{aid}/flows/correct", json={
            "id": first.json()["id"], "as_of_date": "2026-08-16", "amount": "1050.00",
            "flow_type": "deposit", "reason": "typo",
        })
        assert bad.status_code == 422


@pytest.mark.asyncio
async def test_correcting_unknown_flow_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        bad = await ac.post(f"/api/accounts/{aid}/flows/correct", json={
            "id": "00000000-0000-0000-0000-000000000000",
            "as_of_date": "2026-08-16", "amount": "1050.00",
            "flow_type": "deposit", "reason": "there is nothing to correct",
        })
        assert bad.status_code == 404


@pytest.mark.asyncio
async def test_correcting_already_superseded_flow_returns_409():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        first = await ac.post(f"/api/accounts/{aid}/flows", json={
            "as_of_date": "2026-08-16", "amount": "1000.00", "flow_type": "deposit",
        })
        original_id = first.json()["id"]
        await ac.post(f"/api/accounts/{aid}/flows/correct", json={
            "id": original_id, "as_of_date": "2026-08-16", "amount": "1050.00",
            "flow_type": "deposit", "reason": "broker restated deposit amount",
        })
        again = await ac.post(f"/api/accounts/{aid}/flows/correct", json={
            "id": original_id, "as_of_date": "2026-08-16", "amount": "1075.00",
            "flow_type": "deposit", "reason": "correcting an already-corrected row",
        })
        assert again.status_code == 409
        assert again.json()["detail"]["error"] == "flow_already_superseded"
