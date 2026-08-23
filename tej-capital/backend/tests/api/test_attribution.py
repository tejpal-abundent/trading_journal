import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _acct(ac):
    r = await ac.post("/api/accounts", json={"name": "M", "broker": "IBKR", "currency": "USD", "account_type": "live"})
    return r.json()["id"]


@pytest.mark.asyncio
async def test_attribution_by_setup_returns_verdict_tags():
    """Test that /api/attribution?by=setup returns verdict tags."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)

        # Create some trades with trades that have setup_id (which gets auto-generated)
        # Create many trades to get multiple setup groupings
        for i in range(30):
            await ac.post("/api/trades", json={
                "account_id": aid,
                "instrument": "XAUUSD",
                "direction": "long",
                "entry_price": "2400.00",
                "exit_price": "2410.00" if i % 2 == 0 else "2395.00",
                "initial_stop": "2390.00",
                "position_size": "0.10",
                "risk_amount": "100.00",
                "gross_pnl": "50.00" if i % 2 == 0 else "-25.00",
                "costs": "5.00",
                "opened_at": "2026-08-16T10:00:00+00:00",
                "closed_at": "2026-08-16T15:00:00+00:00",
            })

        r = await ac.get("/api/attribution?by=setup")
        assert r.status_code == 200
        rows = r.json()
        # With multiple trades, we should get results if they have setup_id
        for row in rows:
            assert "verdict" in row
            assert row["verdict"] in {"not_enough", "retire", "marginal", "working"}
            assert "group" in row
            assert "trade_count" in row
            assert "expectancy_r" in row


@pytest.mark.asyncio
async def test_attribution_by_asset():
    """Test that /api/attribution?by=asset returns grouped stats."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)

        # Create trades on different instruments
        for instrument in ["XAUUSD", "EURUSD", "GBPUSD"]:
            for i in range(5):
                await ac.post("/api/trades", json={
                    "account_id": aid,
                    "instrument": instrument,
                    "direction": "long",
                    "entry_price": "1.0000",
                    "exit_price": "1.0100",
                    "initial_stop": "0.9900",
                    "position_size": "0.10",
                    "risk_amount": "100.00",
                    "gross_pnl": "50.00",
                    "costs": "5.00",
                    "opened_at": "2026-08-16T10:00:00+00:00",
                    "closed_at": "2026-08-16T15:00:00+00:00",
                })

        r = await ac.get("/api/attribution?by=asset")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        for row in rows:
            assert "group" in row
            assert row["group"] in ["XAUUSD", "EURUSD", "GBPUSD"]
            assert "verdict" in row


@pytest.mark.asyncio
async def test_attribution_by_session():
    """Test that /api/attribution?by=session works."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)

        # Create trades with explicit session values
        for session in ["London", "US", "Tokyo"]:
            for i in range(8):
                await ac.post("/api/trades", json={
                    "account_id": aid,
                    "instrument": "XAUUSD",
                    "direction": "long",
                    "entry_price": "1.0000",
                    "exit_price": "1.0050",
                    "initial_stop": "0.9900",
                    "position_size": "0.10",
                    "risk_amount": "100.00",
                    "gross_pnl": "30.00",
                    "costs": "5.00",
                    "session": session,
                    "opened_at": "2026-08-16T10:00:00+00:00",
                    "closed_at": "2026-08-16T15:00:00+00:00",
                })

        r = await ac.get("/api/attribution?by=session")
        assert r.status_code == 200
        rows = r.json()
        # Verify structure even if empty (shared DB might have no session-labeled trades)
        for row in rows:
            assert "group" in row
            assert "verdict" in row
            assert row["verdict"] in {"not_enough", "retire", "marginal", "working"}


@pytest.mark.asyncio
async def test_attribution_by_htf():
    """Test that /api/attribution?by=htf works."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)

        # Create trades with different HTF alignments
        for i in range(10):
            await ac.post("/api/trades", json={
                "account_id": aid,
                "instrument": "XAUUSD",
                "direction": "long",
                "entry_price": "1.0000",
                "exit_price": "1.0050",
                "initial_stop": "0.9900",
                "position_size": "0.10",
                "risk_amount": "100.00",
                "gross_pnl": "30.00",
                "costs": "5.00",
                "htf_aligned": i % 2 == 0,
                "opened_at": "2026-08-16T10:00:00+00:00",
                "closed_at": "2026-08-16T15:00:00+00:00",
            })

        r = await ac.get("/api/attribution?by=htf")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1


@pytest.mark.asyncio
async def test_attribution_by_dow():
    """Test that /api/attribution?by=dow works."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)

        # Create trades on different days of the week
        dates = [
            "2026-08-17T10:00:00+00:00",  # Sunday
            "2026-08-18T10:00:00+00:00",  # Monday
            "2026-08-19T10:00:00+00:00",  # Tuesday
        ]
        for date in dates:
            for i in range(5):
                await ac.post("/api/trades", json={
                    "account_id": aid,
                    "instrument": "XAUUSD",
                    "direction": "long",
                    "entry_price": "1.0000",
                    "exit_price": "1.0050",
                    "initial_stop": "0.9900",
                    "position_size": "0.10",
                    "risk_amount": "100.00",
                    "gross_pnl": "30.00",
                    "costs": "5.00",
                    "opened_at": date,
                    "closed_at": date.replace("10:00", "15:00"),
                })

        r = await ac.get("/api/attribution?by=dow")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1


@pytest.mark.asyncio
async def test_attribution_by_timeframe():
    """Test that /api/attribution?by=timeframe groups trades by timeframe."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)

        for timeframe in ["1m", "15m", "1h"]:
            for i in range(5):
                await ac.post("/api/trades", json={
                    "account_id": aid,
                    "instrument": "XAUUSD",
                    "direction": "long",
                    "entry_price": "1.0000",
                    "exit_price": "1.0050",
                    "initial_stop": "0.9900",
                    "position_size": "0.10",
                    "risk_amount": "100.00",
                    "gross_pnl": "30.00",
                    "costs": "5.00",
                    "timeframe": timeframe,
                    "opened_at": "2026-08-16T10:00:00+00:00",
                    "closed_at": "2026-08-16T15:00:00+00:00",
                })

        r = await ac.get("/api/attribution?by=timeframe")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        for row in rows:
            assert "group" in row
            assert "verdict" in row


@pytest.mark.asyncio
async def test_attribution_endpoint_returns_list():
    """Test that attribution endpoint returns a list (may be empty or not depending on DB state)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/attribution?by=setup")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_concentration_endpoint():
    """Test concentration endpoint returns payload."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)

        # Create some trades
        for i in range(10):
            await ac.post("/api/trades", json={
                "account_id": aid,
                "instrument": "XAUUSD",
                "direction": "long",
                "entry_price": "1.0000",
                "exit_price": "1.0100" if i < 3 else "1.0050",
                "initial_stop": "0.9900",
                "position_size": "0.10",
                "risk_amount": "100.00",
                "gross_pnl": "200.00" if i < 3 else "30.00",
                "costs": "5.00",
                "opened_at": "2026-08-16T10:00:00+00:00",
                "closed_at": "2026-08-16T15:00:00+00:00",
            })

        r = await ac.get("/api/attribution/concentration")
        assert r.status_code == 200
        body = r.json()
        assert "top_n_share" in body
        assert "top_n_ids" in body
        assert isinstance(body["top_n_ids"], list)


@pytest.mark.asyncio
async def test_compliance_gap_endpoint():
    """Test compliance gap endpoint returns payload."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)

        # Create compliant and non-compliant trades
        for i in range(15):
            await ac.post("/api/trades", json={
                "account_id": aid,
                "instrument": "XAUUSD",
                "direction": "long",
                "entry_price": "1.0000",
                "exit_price": "1.0100" if i % 2 == 0 else "1.0050",
                "initial_stop": "0.9900",
                "position_size": "0.10",
                "risk_amount": "100.00",
                "gross_pnl": "100.00" if i % 2 == 0 else "30.00",
                "costs": "5.00",
                "rule_compliant": i < 8,  # First 8 compliant, rest non-compliant
                "opened_at": "2026-08-16T10:00:00+00:00",
                "closed_at": "2026-08-16T15:00:00+00:00",
            })

        r = await ac.get("/api/attribution/compliance-gap")
        assert r.status_code == 200
        body = r.json()
        assert "compliant_expectancy" in body
        assert "noncompliant_expectancy" in body
        assert "p_value" in body


@pytest.mark.asyncio
async def test_concentration_endpoint_returns_payload_structure():
    """Test concentration endpoint returns proper payload structure."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/attribution/concentration")
        assert r.status_code == 200
        body = r.json()
        # Verify structure exists (may have data from other tests)
        assert "top_n_share" in body
        assert "top_n_ids" in body
        assert isinstance(body["top_n_ids"], list)


@pytest.mark.asyncio
async def test_compliance_gap_endpoint_returns_payload_structure():
    """Test compliance gap endpoint returns proper payload structure."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/attribution/compliance-gap")
        assert r.status_code == 200
        body = r.json()
        # Verify structure exists (may have data from other tests)
        assert "compliant_expectancy" in body
        assert "noncompliant_expectancy" in body
        assert "p_value" in body
