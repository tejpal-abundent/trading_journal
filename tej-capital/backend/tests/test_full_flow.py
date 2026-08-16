"""End-to-end backend smoke test (Task 32).

Exercises the full happy path through the real ASGI app: create an
account, mark its NAV once, log a closed trade, freeze a composite
metric snapshot, and confirm the live verdict correctly reports
"not yet meaningful" with zero return-days (a single NAV row produces
no day-over-day return).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.main import app
from app.db import engine as app_engine


@pytest.fixture(autouse=True)
async def _clean_composite_tables():
    """GET /api/metrics/live?scope=composite (the default) aggregates NAV,
    cash-flow and trade rows across every account in the database, not just
    the ones this test creates. Other test modules in the suite persist
    their own rows to this same database and never roll them back, so
    running the full suite (`pytest tests/ -v`) would otherwise leave this
    test's "n_days == 0 after a single NAV row" assertion order-dependent
    on whatever ran before it. Truncate the tables the composite curve is
    built from before this test runs so its view of "the whole app" is
    reproducible whether it's run alone or as part of the full suite.
    """
    async with app_engine.begin() as conn:
        await conn.execute(text(
            "TRUNCATE TABLE tej_trades, tej_cash_flows, tej_nav_snapshots RESTART IDENTITY CASCADE"
        ))
    yield


@pytest.mark.asyncio
async def test_end_to_end_flow_create_account_mark_trade_freeze(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        acct = (await ac.post("/api/accounts", json={
            "name": "Main", "broker": "IBKR", "currency": "USD", "account_type": "live"
        })).json()

        await ac.post(f"/api/accounts/{acct['id']}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15000.00"})

        await ac.post("/api/trades", json={
            "account_id": acct["id"], "instrument": "XAUUSD", "direction": "long",
            "entry_price": "2400", "exit_price": "2430", "initial_stop": "2390",
            "position_size": "0.10", "risk_amount": "100", "gross_pnl": "300", "costs": "5",
            "opened_at": "2026-08-16T10:00:00+00:00",
            "closed_at": "2026-08-16T15:00:00+00:00"})

        snap = (await ac.post("/api/metrics/freeze", json={
            "as_of_date": "2026-08-16", "scope": "composite"})).json()
        assert len(snap["ledger_hash"]) == 64

        live = (await ac.get("/api/metrics/live")).json()
        assert live["verdict"]["level"] == "not_yet_meaningful"
        assert "N=" not in str(live["verdict"]["headline"])  # N is in a separate field
        assert live["verdict"]["n_days"] == 0  # one NAV row → zero return days
