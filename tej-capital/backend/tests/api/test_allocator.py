import pytest
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient, ASGITransport

from app.main import app


async def _acct(ac):
    r = await ac.post("/api/accounts", json={
        "name": "Allocator Test", "broker": "IBKR", "currency": "USD", "account_type": "live",
    })
    return r.json()["id"]


async def _seed_trade_with_journal_fields(ac):
    """Creates a trade and enriches it with state_of_mind /
    one_sentence_takeaway, plus a journal entry, so the hidden-fields test
    has something to actually hide."""
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
    await ac.patch(f"/api/trades/{trade_id}", json={
        "state_of_mind": "calm",
        "one_sentence_takeaway": "waited for confirmation, worked out",
    })
    await ac.post("/api/journal", json={
        "entry_date": "2026-08-16",
        "body": "Felt anxious before this trade but stuck to the plan.",
        "tags": ["emotion"],
    })


@pytest.mark.asyncio
async def test_allocator_view_hides_journal_and_emotional_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await _seed_trade_with_journal_fields(ac)

        tok = await ac.post("/api/allocator/tokens", json={
            "label": "Prospect A",
            "expires_at": "2027-01-01T00:00:00+00:00",
        })
        assert tok.status_code == 201, tok.text
        token = tok.json()["token"]

        r = await ac.get(f"/api/allocator/view?token={token}")
        assert r.status_code == 200, r.text

    body = r.json()
    assert "journal" not in body
    assert "journal_entries" not in body
    for t in body.get("trades", []):
        assert "state_of_mind" not in t
        assert "one_sentence_takeaway" not in t
    assert all("account_balance" not in acct for acct in body.get("accounts", []))


@pytest.mark.asyncio
async def test_allocator_tokens_create_returns_expected_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/allocator/tokens", json={
            "label": "Prospect B",
            "expires_at": "2027-01-01T00:00:00+00:00",
        })
        assert r.status_code == 201
        body = r.json()
        for key in ("id", "token", "label", "expires_at"):
            assert key in body
        assert body["label"] == "Prospect B"


@pytest.mark.asyncio
async def test_allocator_view_with_expired_token_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        past = (datetime.now(tz=timezone.utc) - timedelta(days=1)).isoformat()
        tok = await ac.post("/api/allocator/tokens", json={
            "label": "Expired Prospect",
            "expires_at": past,
        })
        assert tok.status_code == 201
        token = tok.json()["token"]

        r = await ac.get(f"/api/allocator/view?token={token}")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_allocator_view_with_revoked_token_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        future = (datetime.now(tz=timezone.utc) + timedelta(days=30)).isoformat()
        tok = await ac.post("/api/allocator/tokens", json={
            "label": "Revoked Prospect",
            "expires_at": future,
        })
        assert tok.status_code == 201
        token_id = tok.json()["id"]
        token = tok.json()["token"]

        deleted = await ac.delete(f"/api/allocator/tokens/{token_id}")
        assert deleted.status_code == 204

        r = await ac.get(f"/api/allocator/view?token={token}")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_allocator_view_with_invalid_token_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/allocator/view?token=this-token-does-not-exist")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_revoke_unknown_token_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.delete("/api/allocator/tokens/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404
