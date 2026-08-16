import inspect
import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import SessionDep
from app.domain.policy import LimitBreach, PolicyAmendment, PolicyDocument, PolicyLimit
from app.schemas.policy import (
    LimitBreachRead,
    LimitType,
    LimitUnit,
    PolicyDocumentRead,
    PolicyDocumentUpdate,
    PolicyLimitRead,
    PolicySection,
)
from app.services import drawdown_guard

router = APIRouter(prefix="/api/policy", tags=["policy"])

MIN_OVERRIDE_REASON_LENGTH = 30


class PolicyLimitSetRequest(BaseModel):
    threshold: Decimal
    unit: LimitUnit
    effective_from: date
    committed_action: str = Field(min_length=1)
    reason: str = Field(min_length=10)
    override_during_drawdown: bool = False


class PolicyLimitSetResponse(BaseModel):
    id: uuid.UUID
    limit_type: LimitType
    threshold: Decimal
    unit: LimitUnit
    effective_from: date
    effective_to: date | None
    committed_action: str
    created_at: datetime
    amendment_id: uuid.UUID
    previous_limit_id: uuid.UUID | None
    reason: str
    is_override_during_drawdown: bool

    model_config = {"from_attributes": True}


async def _current_drawdown_pct(db) -> float:
    """Calls drawdown_guard.current_drawdown_pct via the module attribute
    (not a direct import) so tests can monkeypatch it, and tolerates both
    the real async implementation and a synchronous test stub."""
    result = drawdown_guard.current_drawdown_pct(db)
    if inspect.isawaitable(result):
        result = await result
    return result


@router.get("/limits", response_model=list[PolicyLimitRead])
async def list_current_limits(db: SessionDep):
    rows = (await db.execute(
        select(PolicyLimit)
        .where(PolicyLimit.effective_to.is_(None))
        .order_by(PolicyLimit.limit_type)
    )).scalars().all()
    return [PolicyLimitRead.model_validate(r) for r in rows]


@router.post("/limits/{limit_type}", response_model=PolicyLimitSetResponse, status_code=201)
async def set_limit(limit_type: LimitType, payload: PolicyLimitSetRequest, db: SessionDep):
    current_dd = await _current_drawdown_pct(db)
    in_drawdown = current_dd < 0

    if in_drawdown:
        override_ok = payload.override_during_drawdown and len(payload.reason) >= MIN_OVERRIDE_REASON_LENGTH
        if not override_ok:
            raise HTTPException(status_code=409, detail={
                "error": "amendment_blocked_during_drawdown",
                "hint": (
                    f"Current drawdown is {current_dd:.2%}. Policy amendments are blocked while "
                    f"in drawdown. To proceed, set override_during_drawdown=true and provide a "
                    f"reason of at least {MIN_OVERRIDE_REASON_LENGTH} characters."
                ),
                "current_drawdown_pct": current_dd,
            })

    previous = (await db.execute(
        select(PolicyLimit)
        .where(PolicyLimit.limit_type == limit_type, PolicyLimit.effective_to.is_(None))
    )).scalar_one_or_none()

    today = date.today()
    if previous is not None:
        previous.effective_to = today

    new_limit = PolicyLimit(
        id=uuid.uuid4(),
        limit_type=limit_type,
        threshold=payload.threshold,
        unit=payload.unit,
        effective_from=payload.effective_from,
        effective_to=None,
        committed_action=payload.committed_action,
    )
    db.add(new_limit)
    await db.flush()

    is_override = in_drawdown
    amendment = PolicyAmendment(
        id=uuid.uuid4(),
        previous_limit_id=previous.id if previous is not None else None,
        new_limit_id=new_limit.id,
        reason=payload.reason,
        is_override_during_drawdown=is_override,
    )
    db.add(amendment)

    await db.commit()
    await db.refresh(new_limit)
    await db.refresh(amendment)

    return PolicyLimitSetResponse(
        id=new_limit.id,
        limit_type=new_limit.limit_type,
        threshold=new_limit.threshold,
        unit=new_limit.unit,
        effective_from=new_limit.effective_from,
        effective_to=new_limit.effective_to,
        committed_action=new_limit.committed_action,
        created_at=new_limit.created_at,
        amendment_id=amendment.id,
        previous_limit_id=amendment.previous_limit_id,
        reason=amendment.reason,
        is_override_during_drawdown=amendment.is_override_during_drawdown,
    )


@router.get("/document", response_model=list[PolicyDocumentRead])
async def get_document(db: SessionDep):
    rows = (await db.execute(
        select(PolicyDocument).order_by(PolicyDocument.section)
    )).scalars().all()
    return [PolicyDocumentRead.model_validate(r) for r in rows]


@router.patch("/document/{section}", response_model=PolicyDocumentRead)
async def update_document_section(section: PolicySection, payload: PolicyDocumentUpdate, db: SessionDep):
    row = (await db.execute(
        select(PolicyDocument).where(PolicyDocument.section == section)
    )).scalar_one_or_none()

    if row is None:
        row = PolicyDocument(id=uuid.uuid4(), section=section, body=payload.body)
        db.add(row)
    else:
        row.body = payload.body

    await db.commit()
    await db.refresh(row)
    return PolicyDocumentRead.model_validate(row)


@router.get("/breaches", response_model=list[LimitBreachRead])
async def list_live_breaches(db: SessionDep):
    rows = (await db.execute(
        select(LimitBreach)
        .where(LimitBreach.resolved_on.is_(None))
        .order_by(LimitBreach.breached_on.desc())
    )).scalars().all()
    return [LimitBreachRead.model_validate(r) for r in rows]
