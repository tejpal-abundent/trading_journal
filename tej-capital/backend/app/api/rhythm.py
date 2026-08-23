"""Rhythm: daily / weekly / monthly return pacing against configurable targets.

MVP scope only — pace strip + 52-week bar chart. Reuses the same composite
TWR series as the tearsheet (`app.services.snapshot._load_series`) so the
numbers here are always consistent with Performance/Monthly.

R3 applies here too: weeks with no trading are simply absent from
`weekly_returns` — never zero-padded.
"""
from __future__ import annotations
from datetime import date, timedelta

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.domain.settings import Settings as SettingsModel
from app.services.snapshot import _load_series, _wrap

router = APIRouter(prefix="/api/rhythm", tags=["rhythm"])


def _compound(values) -> float | None:
    """Geometric compound of an iterable of period returns. None if empty."""
    values = list(values)
    if not values:
        return None
    total = 1.0
    for v in values:
        total *= 1.0 + float(v)
    return total - 1.0


@router.get("")
async def rhythm(db: SessionDep):
    settings = await db.get(SettingsModel, 1)
    daily_target = float(settings.daily_target_pct) if settings else 0.003
    weekly_target = float(settings.weekly_target_pct) if settings else 0.015
    monthly_target = float(settings.monthly_target_pct) if settings else 0.0614

    returns, _trades, _n = await _load_series(db, "composite", None)

    today = date.today()

    # --- Today ---
    if len(returns) and returns.index[-1] == today:
        today_metric = _wrap(float(returns.iloc[-1]), 1)
    else:
        today_metric = _wrap(None, 0)

    # --- This week: Monday of the current ISO week through today ---
    week_start = today - timedelta(days=today.weekday())
    week_returns = returns[(returns.index >= week_start) & (returns.index <= today)] if len(returns) else returns
    week_value = _compound(week_returns.values)
    week_gap = (week_value - weekly_target) if week_value is not None else None

    # --- This month: day 1 of the current calendar month through today ---
    month_start = today.replace(day=1)
    month_returns = returns[(returns.index >= month_start) & (returns.index <= today)] if len(returns) else returns
    month_value = _compound(month_returns.values)
    month_gap = (month_value - monthly_target) if month_value is not None else None

    # --- Weekly returns: group by ISO year+week, compound each, last 52 with data ---
    groups: dict[tuple[int, int], list[float]] = {}
    group_week_start: dict[tuple[int, int], date] = {}
    for d, v in returns.items():
        iso_year, iso_week, _iso_weekday = d.isocalendar()
        key = (iso_year, iso_week)
        groups.setdefault(key, []).append(float(v))
        group_week_start.setdefault(key, d - timedelta(days=d.weekday()))

    weekly_returns = [
        {
            "week_start": group_week_start[key].isoformat(),
            "return_pct": _compound(groups[key]),
            "trading_days": len(groups[key]),
            "iso_year": key[0],
            "iso_week": key[1],
        }
        for key in sorted(groups.keys())
    ][-52:]

    return {
        "today": {
            "return": today_metric,
            "target_pct": daily_target,
            "trading_date": today.isoformat(),
        },
        "this_week": {
            "return": _wrap(week_value, len(week_returns)),
            "target_pct": weekly_target,
            "week_start": week_start.isoformat(),
            "trading_days_so_far": len(week_returns),
            "gap_pct": week_gap,
        },
        "this_month": {
            "return": _wrap(month_value, len(month_returns)),
            "target_pct": monthly_target,
            "month_start": month_start.isoformat(),
            "trading_days_so_far": len(month_returns),
            "gap_pct": month_gap,
        },
        "weekly_returns": weekly_returns,
    }
