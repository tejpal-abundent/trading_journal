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


# ─── Multi-day trade lifecycle: open + close endpoints ───────────────────

async def _open_trade(ac, aid, opened_at="2026-09-01T08:00:00+00:00"):
    r = await ac.post("/api/trades", json={
        "account_id": aid,
        "instrument": "XAUUSD", "direction": "long",
        "entry_price": "2400.00", "initial_stop": "2390.00", "position_size": "0.10",
        "risk_amount": "100.00",
        "opened_at": opened_at,
    })
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_create_open_trade_no_exit_fields():
    """POST /trades with no exit fields creates an open trade that appears
    in GET /trades/open scoped to its account."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        trade = await _open_trade(ac, aid)
        assert trade["exit_price"] is None
        assert trade["closed_at"] is None
        assert trade["gross_pnl"] is None

        open_list = await ac.get("/api/trades/open")
        own = [t for t in open_list.json() if t["account_id"] == aid]
        assert len(own) == 1
        assert own[0]["id"] == trade["id"]


@pytest.mark.asyncio
async def test_close_open_trade_computes_r_multiple():
    """POST /trades/{id}/close on an open trade sets exit fields + computes r_multiple."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        trade = await _open_trade(ac, aid, opened_at="2026-09-01T08:00:00+00:00")

        r = await ac.post(f"/api/trades/{trade['id']}/close", json={
            "exit_price": "2430.00",
            "closed_at": "2026-09-10T15:00:00+00:00",
            "gross_pnl": "300.00",
            "costs": "5.00",
            "rule_compliant": True,
            "execution_grade": "A",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        # (300 - 5) / 100 = 2.95
        assert body["r_multiple"] == pytest.approx(2.95)
        assert body["closed_at"].startswith("2026-09-10")
        assert body["rule_compliant"] is True

        # No longer in the open list
        open_list = await ac.get("/api/trades/open")
        own = [t for t in open_list.json() if t["account_id"] == aid]
        assert len(own) == 0


@pytest.mark.asyncio
async def test_close_already_closed_returns_409():
    """Closing a trade twice is a 409 — use /correct if you need to edit exit."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        trade = await _open_trade(ac, aid)

        first = await ac.post(f"/api/trades/{trade['id']}/close", json={
            "exit_price": "2430.00",
            "closed_at": "2026-09-05T15:00:00+00:00",
            "gross_pnl": "300.00", "costs": "5.00",
        })
        assert first.status_code == 200

        second = await ac.post(f"/api/trades/{trade['id']}/close", json={
            "exit_price": "2435.00",
            "closed_at": "2026-09-10T15:00:00+00:00",
            "gross_pnl": "350.00", "costs": "5.00",
        })
        assert second.status_code == 409
        assert second.json()["detail"]["error"] == "already_closed"


@pytest.mark.asyncio
async def test_close_before_open_returns_400():
    """closed_at < opened_at is refused."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        trade = await _open_trade(ac, aid, opened_at="2026-09-10T08:00:00+00:00")

        r = await ac.post(f"/api/trades/{trade['id']}/close", json={
            "exit_price": "2430.00",
            "closed_at": "2026-09-01T15:00:00+00:00",   # before open
            "gross_pnl": "300.00", "costs": "5.00",
        })
        assert r.status_code == 400
        assert r.json()["detail"]["error"] == "close_before_open"


@pytest.mark.asyncio
async def test_open_trade_excluded_from_expectancy():
    """Open trades (no gross_pnl → r_multiple = None) must not affect
    the expectancy calculation, which drops null r_multiple via _rr()."""
    from decimal import Decimal
    import pandas as pd
    from app.core.trades import expectancy_r

    trades_df = pd.DataFrame([
        {"r_multiple": 2.0, "risk_amount": Decimal("100")},   # closed
        {"r_multiple": None, "risk_amount": Decimal("100")},  # open (no PnL yet)
    ])
    # Only the closed trade counts: expectancy = 2.0
    assert expectancy_r(trades_df) == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_get_open_trades_ordered_by_opened_desc():
    """Most recently opened trade appears first."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        await _open_trade(ac, aid, opened_at="2026-09-01T08:00:00+00:00")
        await _open_trade(ac, aid, opened_at="2026-09-05T08:00:00+00:00")
        await _open_trade(ac, aid, opened_at="2026-09-03T08:00:00+00:00")

        r = await ac.get("/api/trades/open")
        own = [t for t in r.json() if t["account_id"] == aid]
        assert len(own) == 3
        dates = [t["opened_at"][:10] for t in own]
        assert dates == ["2026-09-05", "2026-09-03", "2026-09-01"]
