import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import SessionDep
from app.domain.trades import Trade
from app.schemas.trades import TradeCreate, TradeRead
from app.services.corrections import InvalidReason, apply_correction

router = APIRouter(prefix="/api/trades", tags=["trades"])

# Fields that were never "asserted" up front and so can be filled in later
# via PATCH without going through the correction/audit flow (Brief §4.2).
ENRICHABLE_FIELDS = {
    "setup_id", "risk_amount", "execution_grade", "state_of_mind",
    "mae_r", "mfe_r", "rule_compliant", "breach_note",
    "one_sentence_takeaway", "review",
}

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


class TradeCorrect(BaseModel):
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    gross_pnl: Decimal | None = None
    costs: Decimal | None = None
    initial_stop: Decimal | None = None
    reason: str = Field(min_length=10)


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
    t = Trade(id=uuid.uuid4(), **payload.model_dump())
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
