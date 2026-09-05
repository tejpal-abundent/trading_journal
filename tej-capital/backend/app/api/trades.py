import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep
from app.domain.nav import NavSnapshot
from app.domain.settings import Settings
from app.domain.trades import Trade
from app.schemas.settings import DEFAULT_RISK_BY_TIMEFRAME
from app.schemas.trades import TradeCreate, TradeRead
from app.services.corrections import InvalidReason, apply_correction

router = APIRouter(prefix="/api/trades", tags=["trades"])

# Fields that were never "asserted" up front and so can be filled in later
# via PATCH without going through the correction/audit flow (Brief §4.2).
ENRICHABLE_FIELDS = {
    "setup_id", "risk_amount", "execution_grade", "state_of_mind",
    "mae_r", "mfe_r", "rule_compliant", "breach_note",
    "one_sentence_takeaway", "review", "timeframe",
}


async def _validate_tf_risk(db: AsyncSession, trade_data: dict, account_id: uuid.UUID) -> None:
    """If timeframe AND risk_amount both present, ensure risk_amount / latest_equity
    does not exceed the timeframe-specific limit. Skip validation if either is null."""
    tf = trade_data.get("timeframe")
    risk = trade_data.get("risk_amount")
    if tf is None or risk is None:
        return
    # Fetch most recent non-superseded NAV for this account
    latest = (await db.execute(
        select(NavSnapshot)
        .where(NavSnapshot.account_id == account_id, NavSnapshot.superseded_by.is_(None))
        .order_by(NavSnapshot.as_of_date.desc()).limit(1)
    )).scalar_one_or_none()
    if latest is None:
        return  # No equity to validate against; let trade through
    settings = await db.get(Settings, 1)
    risk_map = settings.risk_by_timeframe if settings and settings.risk_by_timeframe else DEFAULT_RISK_BY_TIMEFRAME
    threshold = Decimal(str(risk_map.get(tf, "0.005")))
    risk_pct = Decimal(risk) / Decimal(latest.closing_equity)
    if risk_pct > threshold:
        raise HTTPException(status_code=400, detail={
            "error": "risk_exceeds_timeframe_limit",
            "timeframe": tf,
            "risk_pct": float(risk_pct),
            "threshold": float(threshold),
            "hint": f"Risk {float(risk_pct)*100:.3f}% exceeds {tf} limit of {float(threshold)*100:.3f}%. "
                    f"Reduce position size or raise the limit in Settings → Risk by timeframe.",
        })

# Economic fields that WERE asserted at entry time; changing them requires
# the supersede-and-log correction flow with a reason (R1/R2).
CORRECTABLE_FIELDS = ("entry_price", "exit_price", "gross_pnl", "costs", "initial_stop")


class TradeEnrich(BaseModel):
    setup_id: uuid.UUID | None = None
    risk_amount: Decimal | None = None
    execution_grade: str | None = None
    state_of_mind: str | None = None
    mae_r: Decimal | None = None
    mfe_r: Decimal | None = None
    rule_compliant: bool | None = None
    breach_note: str | None = None
    one_sentence_takeaway: str | None = None
    review: str | None = None
    timeframe: str | None = None


class TradeCorrect(BaseModel):
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    gross_pnl: Decimal | None = None
    costs: Decimal | None = None
    initial_stop: Decimal | None = None
    reason: str = Field(min_length=10)


class TradeClose(BaseModel):
    """Finalise an open trade — sets the exit-side fields in place.

    NOT a correction: the trade wasn't wrong, it just wasn't over. No
    reason required, no supersede, no correction ledger row. Refused if
    the trade is already closed (must use /correct for that)."""

    exit_price: Decimal
    closed_at: datetime
    gross_pnl: Decimal
    costs: Decimal = Decimal("0")
    mae_r: Decimal | None = None
    mfe_r: Decimal | None = None
    rule_compliant: bool | None = None
    breach_note: str | None = None
    execution_grade: str | None = None
    state_of_mind: str | None = None
    review: str | None = None
    one_sentence_takeaway: str | None = None


def _serialize(t: Trade) -> dict:
    data = TradeRead.model_validate(t).model_dump(mode="json")
    data["enrichment_needed"] = t.risk_amount is None
    return data


async def _get_current(db: SessionDep, trade_id: uuid.UUID) -> Trade | None:
    return (await db.execute(
        select(Trade).where(Trade.id == trade_id, Trade.superseded_by.is_(None))
    )).scalar_one_or_none()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_trade(payload: TradeCreate, db: SessionDep):
    data = payload.model_dump()
    await _validate_tf_risk(db, data, payload.account_id)
    t = Trade(id=uuid.uuid4(), **data)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _serialize(t)


@router.get("/enrichment")
async def enrichment_queue(db: SessionDep):
    rows = (await db.execute(
        select(Trade)
        .where(Trade.risk_amount.is_(None), Trade.superseded_by.is_(None))
        .order_by(Trade.opened_at.desc())
    )).scalars().all()
    return [_serialize(r) for r in rows]


@router.get("/open")
async def open_positions(db: SessionDep):
    """Trades that have been opened but not yet closed. Used by the Trade
    Entry page's Open Positions panel so multi-day / multi-week holds are
    discoverable a day, a week, or a month later."""
    rows = (await db.execute(
        select(Trade)
        .where(Trade.closed_at.is_(None), Trade.superseded_by.is_(None))
        .order_by(Trade.opened_at.desc())
    )).scalars().all()
    return [_serialize(r) for r in rows]


@router.get("")
async def list_trades(
    db: SessionDep,
    since: date | None = Query(default=None),
    account_id: uuid.UUID | None = Query(default=None),
):
    q = select(Trade).where(Trade.superseded_by.is_(None))
    if since is not None:
        q = q.where(Trade.opened_at >= datetime(since.year, since.month, since.day))
    if account_id is not None:
        q = q.where(Trade.account_id == account_id)
    q = q.order_by(Trade.opened_at)
    rows = (await db.execute(q)).scalars().all()
    return [_serialize(r) for r in rows]


@router.patch("/{trade_id}")
async def enrich_trade(trade_id: uuid.UUID, payload: TradeEnrich, db: SessionDep):
    t = await _get_current(db, trade_id)
    if not t:
        raise HTTPException(status_code=404, detail="trade not found")

    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if k in ENRICHABLE_FIELDS:
            setattr(t, k, v)

    await _validate_tf_risk(db, {"timeframe": t.timeframe, "risk_amount": t.risk_amount}, t.account_id)

    await db.commit()
    await db.refresh(t)
    return _serialize(t)


@router.post("/{trade_id}/correct")
async def correct_trade(trade_id: uuid.UUID, payload: TradeCorrect, db: SessionDep):
    old = await _get_current(db, trade_id)
    if not old:
        raise HTTPException(status_code=404, detail={
            "error": "trade_not_found",
            "hint": "No current (non-superseded) trade exists with that id to correct.",
        })

    carry_over = {
        c.name: getattr(old, c.name)
        for c in Trade.__table__.columns
        if c.name not in {"id", "superseded_by", "superseded_reason", "entered_at"}
    }
    for field in CORRECTABLE_FIELDS:
        value = getattr(payload, field)
        if value is not None:
            carry_over[field] = value

    new = Trade(id=uuid.uuid4(), **carry_over)

    try:
        persisted = await apply_correction(
            db, table_name="tej_trades", old_row=old, new_row=new, reason=payload.reason,
        )
    except InvalidReason as e:
        raise HTTPException(status_code=422, detail=str(e))

    await db.commit()
    await db.refresh(persisted)
    return _serialize(persisted)


@router.post("/{trade_id}/close")
async def close_trade(trade_id: uuid.UUID, payload: TradeClose, db: SessionDep):
    """Finalise an open trade. Sets the exit-side fields in place — NOT a
    correction. R-multiple is auto-computed on the model as (gross_pnl - costs)
    / risk_amount and will land in the closed_at week/month/attribution
    automatically (see services/snapshot._load_series bucketing)."""
    t = await _get_current(db, trade_id)
    if not t:
        raise HTTPException(status_code=404, detail={
            "error": "trade_not_found",
            "hint": "No current (non-superseded) trade with that id.",
        })

    if t.closed_at is not None:
        raise HTTPException(status_code=409, detail={
            "error": "already_closed",
            "closed_at": t.closed_at.isoformat(),
            "hint": "This trade is already closed. Use POST /trades/{id}/correct if "
                    "you need to change the exit price or P&L after the fact.",
        })

    # Compare using UTC to avoid tz-aware vs tz-naive TypeError. Trade.opened_at
    # is TIMESTAMPTZ; incoming closed_at is parsed by Pydantic as tz-aware.
    if payload.closed_at < t.opened_at:
        raise HTTPException(status_code=400, detail={
            "error": "close_before_open",
            "hint": f"closed_at ({payload.closed_at.isoformat()}) must be >= "
                    f"opened_at ({t.opened_at.isoformat()}).",
        })

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, field, value)

    # Defensive: risk_amount usually set at open, but re-validate anyway
    # in case the exit-side payload changed timeframe or risk fields.
    await _validate_tf_risk(
        db, {"timeframe": t.timeframe, "risk_amount": t.risk_amount}, t.account_id,
    )

    await db.commit()
    await db.refresh(t)
    return _serialize(t)
