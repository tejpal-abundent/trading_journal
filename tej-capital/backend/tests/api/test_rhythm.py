from datetime import date, timedelta

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete

from app.db import SessionLocal
from app.domain.nav import NavSnapshot
from app.main import app


async def _reset_nav_state():
    """tej_nav_snapshots is a real table in the same non-ephemeral database
    the app itself uses (app.db.engine), so rows survive across pytest
    invocations. Delete them directly so the empty-history and
    hand-computation assertions below are deterministic regardless of what
    earlier test runs (or other test files) left behind — same pattern as
    test_metrics.py's `_reset_metrics_state`.

    Cash flows are intentionally left alone: `_load_series` only folds an
    account into the composite series once it has >=2 NAV points, so
    leftover flow rows from other test files don't affect these
    assertions.
    """
    async with SessionLocal() as s:
        await s.execute(delete(NavSnapshot))
        await s.commit()


async def _make_account(ac, name="RhythmTest"):
    r = await ac.post("/api/accounts", json={
        "name": name, "broker": "IBKR", "currency": "USD",
        "account_type": "live",
    })
    assert r.status_code == 201
    return r.json()["id"]


async def _mark(ac, aid, as_of_date: date, closing_equity: float):
    r = await ac.post(f"/api/accounts/{aid}/nav", json={
        "as_of_date": as_of_date.isoformat(), "closing_equity": f"{closing_equity:.8f}",
    })
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_rhythm_empty_returns_null_for_all_periods():
    await _reset_nav_state()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/rhythm")
    assert r.status_code == 200
    body = r.json()

    assert body["today"]["return"] == {"value": None, "n": 0}
    assert body["this_week"]["return"] == {"value": None, "n": 0}
    assert body["this_week"]["trading_days_so_far"] == 0
    assert body["this_week"]["gap_pct"] is None
    assert body["this_month"]["return"] == {"value": None, "n": 0}
    assert body["this_month"]["trading_days_so_far"] == 0
    assert body["this_month"]["gap_pct"] is None
    assert body["weekly_returns"] == []


@pytest.mark.asyncio
async def test_rhythm_weekly_aggregation_matches_hand_computation():
    await _reset_nav_state()
    # Two full ISO weeks: Mon 2026-08-03..Fri 2026-08-07, Mon 2026-08-10..Fri 2026-08-14.
    dates = [
        date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5), date(2026, 8, 6), date(2026, 8, 7),
        date(2026, 8, 10), date(2026, 8, 11), date(2026, 8, 12), date(2026, 8, 13), date(2026, 8, 14),
    ]
    equities = [15000, 15150, 15300, 15450, 15600, 15750, 15900, 16050, 16200, 16350]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        for d, e in zip(dates, equities):
            await _mark(ac, aid, d, e)

        # Hand-computed day-over-day returns (first date has no prior mark, so it's dropped).
        rets = [(equities[i] - equities[i - 1]) / equities[i - 1] for i in range(1, len(equities))]
        ret_dates = dates[1:]

        week1_rets = [rets[i] for i, d in enumerate(ret_dates) if d <= date(2026, 8, 7)]
        week2_rets = [rets[i] for i, d in enumerate(ret_dates) if d >= date(2026, 8, 10)]

        def compound(vals):
            total = 1.0
            for v in vals:
                total *= 1.0 + v
            return total - 1.0

        expected_week1 = compound(week1_rets)
        expected_week2 = compound(week2_rets)

        r = await ac.get("/api/rhythm")
    assert r.status_code == 200
    weekly = r.json()["weekly_returns"]
    assert len(weekly) == 2

    assert weekly[0]["week_start"] == "2026-08-03"
    assert weekly[0]["trading_days"] == len(week1_rets)
    assert weekly[0]["return_pct"] == pytest.approx(expected_week1)

    assert weekly[1]["week_start"] == "2026-08-10"
    assert weekly[1]["trading_days"] == len(week2_rets)
    assert weekly[1]["return_pct"] == pytest.approx(expected_week2)


@pytest.mark.asyncio
async def test_rhythm_ignores_superseded_marks():
    await _reset_nav_state()
    today = date.today()
    prior_day = today - timedelta(days=1)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        await _mark(ac, aid, prior_day, 10000)
        await _mark(ac, aid, today, 10100)  # original — would give a 1.00% return

        corr = await ac.post(f"/api/accounts/{aid}/nav/correct", json={
            "as_of_date": today.isoformat(), "closing_equity": "10200.00",
            "reason": "broker restated overnight swap",
        })
        assert corr.status_code == 201

        r = await ac.get("/api/rhythm")
    assert r.status_code == 200
    today_metric = r.json()["today"]["return"]
    assert today_metric["n"] == 1
    assert today_metric["value"] == pytest.approx((10200 - 10000) / 10000)


@pytest.mark.asyncio
async def test_rhythm_gap_is_actual_minus_target():
    await _reset_nav_state()
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    prior_day = week_start - timedelta(days=1)

    # A generous target that no plausible weekly return will exceed, so the
    # gap sign is deterministic regardless of which weekday "today" is.
    weekly_target = 0.5

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.patch("/api/settings", json={"weekly_target_pct": str(weekly_target)})

        aid = await _make_account(ac)
        equity = 10000.0
        await _mark(ac, aid, prior_day, equity)
        d = week_start
        num_days = 0
        while d <= today:
            equity *= 1.01
            await _mark(ac, aid, d, equity)
            num_days += 1
            d += timedelta(days=1)

        r = await ac.get("/api/rhythm")

        # restore the default so later tests aren't affected
        await ac.patch("/api/settings", json={"weekly_target_pct": "0.015"})

    assert r.status_code == 200
    this_week = r.json()["this_week"]
    expected_return = 1.01 ** num_days - 1.0
    expected_gap = expected_return - weekly_target

    assert this_week["return"]["value"] == pytest.approx(expected_return)
    assert this_week["target_pct"] == pytest.approx(weekly_target)
    assert this_week["gap_pct"] == pytest.approx(expected_gap)
    assert this_week["gap_pct"] < 0
