import uuid
from calendar import monthrange
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import SessionDep
from app.domain.metrics import MetricSnapshot
from app.schemas.metrics import MetricScope, MetricSnapshotRead
from app.services.snapshot import _load_series, compute_tearsheet, freeze_snapshot

router = APIRouter(prefix="/api/metrics", tags=["metrics"])
tearsheet_router = APIRouter(prefix="/api/tearsheet", tags=["tearsheet"])


class FreezeRequest(BaseModel):
    as_of_date: date
    scope: MetricScope = "composite"
    account_id: uuid.UUID | None = None


def _serialize_snapshot(snap: MetricSnapshot) -> dict:
    return MetricSnapshotRead.model_validate(snap).model_dump(mode="json")


@router.get("/live")
async def live_metrics(
    db: SessionDep,
    scope: MetricScope = Query(default="composite"),
    account_id: uuid.UUID | None = Query(default=None),
):
    if scope == "per_account" and account_id is None:
        raise HTTPException(status_code=422, detail={
            "error": "account_id_required",
            "hint": "scope=per_account requires an account_id query parameter.",
        })
    return await compute_tearsheet(db, scope, account_id)


@router.post("/freeze")
async def freeze(payload: FreezeRequest, db: SessionDep, response: Response):
    if payload.scope == "per_account" and payload.account_id is None:
        raise HTTPException(status_code=422, detail={
            "error": "account_id_required",
            "hint": "scope=per_account requires an account_id in the request body.",
        })
    snap, created = await freeze_snapshot(
        db, as_of_date=payload.as_of_date, scope=payload.scope, account_id=payload.account_id,
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return _serialize_snapshot(snap)


@router.get("/snapshots")
async def list_snapshots(
    db: SessionDep,
    since: date | None = Query(default=None),
    scope: MetricScope | None = Query(default=None),
    account_id: uuid.UUID | None = Query(default=None),
):
    q = select(MetricSnapshot)
    if since is not None:
        q = q.where(MetricSnapshot.as_of_date >= since)
    if scope is not None:
        q = q.where(MetricSnapshot.scope == scope)
    if account_id is not None:
        q = q.where(MetricSnapshot.account_id == account_id)
    q = q.order_by(MetricSnapshot.as_of_date)
    rows = (await db.execute(q)).scalars().all()
    return [_serialize_snapshot(r) for r in rows]


@tearsheet_router.get("/monthly")
async def tearsheet_monthly(
    db: SessionDep,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
):
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    frozen = (await db.execute(
        select(MetricSnapshot)
        .where(
            MetricSnapshot.scope == "composite",
            MetricSnapshot.account_id.is_(None),
            MetricSnapshot.as_of_date >= start,
            MetricSnapshot.as_of_date <= end,
        )
        .order_by(MetricSnapshot.as_of_date.desc())
    )).scalars().first()

    if frozen is not None:
        tearsheet = frozen.metrics
        source = "frozen"
        as_of = frozen.as_of_date
    else:
        tearsheet = await compute_tearsheet(db, "composite", None)
        source = "live"
        as_of = None

    returns, _trades, _n = await _load_series(db, "composite", None)
    month_returns = returns[(returns.index >= start) & (returns.index <= end)] if len(returns) else returns
    monthly_grid = [
        {"date": d.isoformat() if hasattr(d, "isoformat") else str(d), "return": float(v)}
        for d, v in month_returns.items()
    ]

    return {
        "year": year,
        "month": month,
        "source": source,
        "as_of_date": as_of.isoformat() if as_of else None,
        "headline": {
            "cumulative_twr": tearsheet["returns"]["cumulative_twr"],
            "cagr": tearsheet["returns"]["cagr"],
            "sharpe": tearsheet["risk_adjusted"]["sharpe"],
            "max_drawdown": tearsheet["risk"]["max_drawdown"],
        },
        "metric_groups": tearsheet,
        "verdict": tearsheet["verdict"],
        "monthly_grid": monthly_grid,
    }
