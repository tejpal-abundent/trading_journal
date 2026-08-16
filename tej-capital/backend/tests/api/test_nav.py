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
async def test_create_nav_mark_returns_201():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        r = await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15000.00",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["account_id"] == aid
        assert body["closing_equity"] == "15000.00000000"
        assert body["superseded_by"] is None


@pytest.mark.asyncio
async def test_duplicate_mark_returns_409():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        first = await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15000.00",
        })
        assert first.status_code == 201
        dup = await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15100.00",
        })
        assert dup.status_code == 409
        assert dup.json()["detail"]["error"] == "mark_exists"
        assert dup.json()["detail"]["existing_id"] == first.json()["id"]


@pytest.mark.asyncio
async def test_correction_creates_new_row_and_supersedes_old_R1():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        first = await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15000.00",
        })
        original_id = first.json()["id"]
        corr = await ac.post(f"/api/accounts/{aid}/nav/correct", json={
            "as_of_date": "2026-08-16", "closing_equity": "15050.00",
            "reason": "broker restated overnight swap",
        })
        assert corr.status_code == 201
        assert corr.json()["id"] != original_id
        # Listing returns the corrected value, not the original
        listing = await ac.get(f"/api/accounts/{aid}/nav?since=2026-08-16")
        rows = listing.json()
        current = [r for r in rows if r["closing_equity"] == "15050.00000000"]
        assert len(current) == 1
        assert current[0]["id"] != original_id
        # The original row no longer appears as a current row
        assert all(r["id"] != original_id for r in rows)


@pytest.mark.asyncio
async def test_correction_reason_min_length():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15000.00"})
        bad = await ac.post(f"/api/accounts/{aid}/nav/correct", json={
            "as_of_date": "2026-08-16", "closing_equity": "15050.00", "reason": "typo"})
        assert bad.status_code == 422


@pytest.mark.asyncio
async def test_correct_with_no_current_mark_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        r = await ac.post(f"/api/accounts/{aid}/nav/correct", json={
            "as_of_date": "2026-08-16", "closing_equity": "15050.00",
            "reason": "nothing to correct here",
        })
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_closing_equity_must_be_positive():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        r = await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "0",
        })
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_nav_without_since_returns_all_current_rows():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-14", "closing_equity": "14000.00",
        })
        await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-15", "closing_equity": "14500.00",
        })
        listing = await ac.get(f"/api/accounts/{aid}/nav")
        assert listing.status_code == 200
        assert len(listing.json()) == 2

        since = await ac.get(f"/api/accounts/{aid}/nav?since=2026-08-15")
        assert len(since.json()) == 1
        assert since.json()[0]["as_of_date"] == "2026-08-15"
