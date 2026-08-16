import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, condecimal, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.domain.flows import CashFlow
from app.services.corrections import InvalidReason, apply_correction

router = APIRouter(prefix="/api/accounts", tags=["flows"])

FlowType = Literal[
    "deposit", "withdrawal", "prop_payout", "platform_fee", "transfer_in", "transfer_out",
]
FlowTiming = Literal["start_of_day", "end_of_day"]

# R2: flows are never profit — this is just money moving in/out, so the
# amount is a signed, nonzero Decimal (not gt=0 like NAV closing_equity).
Money = condecimal(max_digits=20, decimal_places=8)


def _nonzero(v: Decimal) -> Decimal:
    if v == 0:
        raise ValueError("amount must not be zero")
    return v


class FlowCreate(BaseModel):
    as_of_date: date
    amount: Money
    flow_type: FlowType
    flow_timing: FlowTiming = "end_of_day"
    note: str | None = None

    _amount_nonzero = field_validator("amount")(_nonzero)


class FlowCorrect(BaseModel):
    id: uuid.UUID
    as_of_date: date
    amount: Money
    flow_type: FlowType
    flow_timing: FlowTiming = "end_of_day"
    note: str | None = None
    reason: str = Field(min_length=10)

    _amount_nonzero = field_validator("amount")(_nonzero)


class FlowRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    as_of_date: date
    amount: Decimal
    flow_type: FlowType
    flow_timing: FlowTiming
    note: str | None
    superseded_by: uuid.UUID | None
    superseded_reason: str | None
    model_config = {"from_attributes": True}


@router.post("/{account_id}/flows", status_code=201, response_model=FlowRead)
async def create_flow(account_id: uuid.UUID, payload: FlowCreate, db: SessionDep):
    row = CashFlow(
        id=uuid.uuid4(),
        account_id=account_id,
        as_of_date=payload.as_of_date,
        amount=payload.amount,
        flow_type=payload.flow_type,
        flow_timing=payload.flow_timing,
        note=payload.note,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return FlowRead.model_validate(row)


@router.post("/{account_id}/flows/correct", status_code=201, response_model=FlowRead)
async def correct_flow(account_id: uuid.UUID, payload: FlowCorrect, db: SessionDep):
    old = await db.get(CashFlow, payload.id)
    if not old or old.account_id != account_id:
        raise HTTPException(status_code=404, detail={
            "error": "flow_not_found",
            "hint": "No flow with that id exists on this account.",
        })
    if old.superseded_by is not None:
        raise HTTPException(status_code=409, detail={
            "error": "flow_already_superseded",
            "existing_id": str(old.superseded_by),
            "hint": "This flow was already corrected. Correct the superseding row instead.",
        })
    new = CashFlow(
        id=uuid.uuid4(),
        account_id=account_id,
        as_of_date=payload.as_of_date,
        amount=payload.amount,
        flow_type=payload.flow_type,
        flow_timing=payload.flow_timing,
        note=payload.note,
    )
    try:
        persisted = await apply_correction(
            db, table_name="tej_cash_flows",
            old_row=old, new_row=new, reason=payload.reason,
        )
    except InvalidReason as e:
        raise HTTPException(status_code=422, detail=str(e))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail={
            "error": "flow_already_superseded",
            "hint": "A concurrent write already superseded this flow.",
        })
    await db.refresh(persisted)
    return FlowRead.model_validate(persisted)


@router.get("/{account_id}/flows", response_model=list[FlowRead])
async def list_flows(account_id: uuid.UUID, db: SessionDep, since: date | None = Query(default=None)):
    stmt = select(CashFlow).where(
        CashFlow.account_id == account_id,
        CashFlow.superseded_by.is_(None),
    )
    if since is not None:
        stmt = stmt.where(CashFlow.as_of_date >= since)
    rows = (await db.execute(stmt.order_by(CashFlow.as_of_date))).scalars().all()
    return [FlowRead.model_validate(r) for r in rows]
