import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete

from app.db import SessionLocal
from app.domain.metrics import MetricSnapshot
from app.domain.nav import NavSnapshot
from app.main import app


async def _reset_metrics_state():
    """The nav/metric-snapshot tables are real rows persisted in the same
    non-ephemeral database the app itself uses (app.db.engine), so they
    survive across pytest invocations (same pattern as test_settings.py's
    `_reset_settings_row`). Delete them directly so the empty-history (R3)
    and freeze-idempotency assertions below are deterministic regardless of
    what earlier test runs left behind.

    Cash flows and trades are intentionally left alone: `_load_series` only
    folds an account into the composite series once it has >=2 NAV points,
    so leftover flow/trade rows from other test files don't affect these
    assertions.
    """
    async with SessionLocal() as s:
        await s.execute(delete(NavSnapshot))
        await s.execute(delete(MetricSnapshot))
        await s.commit()


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_null_for_empty_history_R3():
    await _reset_metrics_state()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/metrics/live?scope=composite")
    assert r.status_code == 200
    body = r.json()
    assert body["returns"]["cumulative_twr"]["value"] is None
    assert body["returns"]["cumulative_twr"]["n"] == 0


@pytest.mark.asyncio
async def test_freeze_snapshot_writes_ledger_hash():
    await _reset_metrics_state()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/metrics/freeze", json={"as_of_date": "2026-08-16", "scope": "composite"})
        assert r.status_code == 201
        body = r.json()
        assert len(body["ledger_hash"]) == 64
        # Idempotent
        again = await ac.post("/api/metrics/freeze", json={"as_of_date": "2026-08-16", "scope": "composite"})
        assert again.status_code == 200  # not 201 second time
        assert again.json()["id"] == body["id"]
        assert again.json()["ledger_hash"] == body["ledger_hash"]


@pytest.mark.asyncio
async def test_live_metrics_every_scalar_is_wrapped_R6():
    await _reset_metrics_state()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/metrics/live?scope=composite")
    assert r.status_code == 200
    body = r.json()
    for group in ("returns", "risk", "risk_adjusted"):
        for key, metric in body[group].items():
            if key == "top_5_drawdowns":
                continue
            assert set(metric.keys()) == {"value", "n"}, f"{group}.{key} was not wrapped"


@pytest.mark.asyncio
async def test_live_metrics_per_account_requires_account_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/metrics/live?scope=per_account")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_snapshots_list_filters_by_scope_and_since():
    await _reset_metrics_state()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/metrics/freeze", json={"as_of_date": "2026-08-16", "scope": "composite"})
        listing = await ac.get("/api/metrics/snapshots?since=2026-08-01&scope=composite")
        assert listing.status_code == 200
        rows = listing.json()
        assert len(rows) == 1
        assert rows[0]["as_of_date"] == "2026-08-16"
        assert rows[0]["scope"] == "composite"


@pytest.mark.asyncio
async def test_tearsheet_monthly_falls_back_to_live_when_no_frozen_snapshot():
    await _reset_metrics_state()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/tearsheet/monthly?year=2026&month=8")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "live"
    assert body["headline"]["cumulative_twr"]["value"] is None
    assert "monthly_grid" in body
    assert "verdict" in body


@pytest.mark.asyncio
async def test_tearsheet_monthly_reads_frozen_snapshot_when_present():
    await _reset_metrics_state()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/metrics/freeze", json={"as_of_date": "2026-08-16", "scope": "composite"})
        r = await ac.get("/api/tearsheet/monthly?year=2026&month=8")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "frozen"
    assert body["as_of_date"] == "2026-08-16"
