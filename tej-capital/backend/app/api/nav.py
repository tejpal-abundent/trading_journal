import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, condecimal
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.domain.nav import NavSnapshot
from app.services.corrections import InvalidReason, apply_correction

router = APIRouter(prefix="/api/accounts", tags=["nav"])

Money = condecimal(gt=Decimal("0"), max_digits=20, decimal_places=8)


class NavCreate(BaseModel):
    as_of_date: date
    closing_equity: Money


class NavCorrect(BaseModel):
    as_of_date: date
    closing_equity: Money
    reason: str = Field(min_length=10)


class NavRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    as_of_date: date
    closing_equity: Decimal
    superseded_by: uuid.UUID | None
    superseded_reason: str | None
    model_config = {"from_attributes": True}


async def _current_mark(db: SessionDep, account_id: uuid.UUID, as_of_date: date) -> NavSnapshot | None:
    return (await db.execute(
        select(NavSnapshot).where(
            NavSnapshot.account_id == account_id,
            NavSnapshot.as_of_date == as_of_date,
            NavSnapshot.superseded_by.is_(None),
        )
    )).scalar_one_or_none()


@router.post("/{account_id}/nav", status_code=201, response_model=NavRead)
async def create_nav(account_id: uuid.UUID, payload: NavCreate, db: SessionDep):
    existing = await _current_mark(db, account_id, payload.as_of_date)
    if existing:
        raise HTTPException(status_code=409, detail={
            "error": "mark_exists",
            "existing_id": str(existing.id),
            "hint": "Use POST /nav/correct to supersede this mark.",
        })
    row = NavSnapshot(
        id=uuid.uuid4(),
        account_id=account_id,
        as_of_date=payload.as_of_date,
        closing_equity=payload.closing_equity,
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _current_mark(db, account_id, payload.as_of_date)
        raise HTTPException(status_code=409, detail={
            "error": "mark_exists",
            "existing_id": str(existing.id) if existing else None,
            "hint": "Use POST /nav/correct to supersede this mark.",
        })
    await db.refresh(row)
    return NavRead.model_validate(row)


@router.post("/{account_id}/nav/correct", status_code=201, response_model=NavRead)
async def correct_nav(account_id: uuid.UUID, payload: NavCorrect, db: SessionDep):
    old = await _current_mark(db, account_id, payload.as_of_date)
    if not old:
        raise HTTPException(status_code=404, detail={
            "error": "mark_not_found",
            "hint": "No current mark exists for that account/date to correct.",
        })
    new = NavSnapshot(
        id=uuid.uuid4(),
        account_id=account_id,
        as_of_date=payload.as_of_date,
        closing_equity=payload.closing_equity,
    )
    try:
        persisted = await apply_correction(
            db, table_name="tej_nav_snapshots",
            old_row=old, new_row=new, reason=payload.reason,
        )
    except InvalidReason as e:
        raise HTTPException(status_code=422, detail=str(e))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail={
            "error": "mark_exists",
            "hint": "A concurrent write already superseded this mark.",
        })
    await db.refresh(persisted)
    return NavRead.model_validate(persisted)


@router.get("/{account_id}/nav", response_model=list[NavRead])
async def list_nav(account_id: uuid.UUID, db: SessionDep, since: date | None = Query(default=None)):
    stmt = select(NavSnapshot).where(
        NavSnapshot.account_id == account_id,
        NavSnapshot.superseded_by.is_(None),
    )
    if since is not None:
        stmt = stmt.where(NavSnapshot.as_of_date >= since)
    rows = (await db.execute(stmt.order_by(NavSnapshot.as_of_date))).scalars().all()
    return [NavRead.model_validate(r) for r in rows]
