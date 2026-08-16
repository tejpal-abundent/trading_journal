"""Reads current drawdown from the latest composite metric snapshot.

Task 18 will populate `tej_metric_snapshots` on a schedule; until then (or
whenever no snapshot exists yet) this returns 0.0, which the policy API
treats as "not in drawdown" (never blocks amendments).

`current_drawdown_pct` is deliberately a module-level function (not a
class/service method) so tests can monkeypatch it directly:

    monkeypatch.setattr(drawdown_guard, "current_drawdown_pct", lambda db: -0.08)

Callers must therefore tolerate either a coroutine (the real implementation)
or a plain value (a synchronous test stub) — see `app.api.policy` for the
`inspect.isawaitable` guard used at the call site.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.metrics import MetricSnapshot


async def current_drawdown_pct(db: AsyncSession) -> float:
    """Current drawdown as a signed fraction (e.g. -0.08 for -8%).

    Negative means "in drawdown". Returns 0.0 when there is no snapshot yet,
    or when the snapshot has no `current_drawdown` key.
    """
    row = (await db.execute(
        select(MetricSnapshot)
        .where(MetricSnapshot.scope == "composite")
        .order_by(MetricSnapshot.as_of_date.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not row:
        return 0.0
    return float(row.metrics.get("current_drawdown", 0.0) or 0.0)
