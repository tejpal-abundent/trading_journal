"""Unified audit feed: union of the corrections ledger (R1 economic-field
corrections) and policy amendments (limit changes), for a single
chronological trail of "what changed and why"."""
import uuid
from datetime import date, datetime, time, timezone
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import SessionDep
from app.domain.audit import CorrectionLedger
from app.domain.policy import PolicyAmendment

router = APIRouter(prefix="/api/audit", tags=["audit"])

AuditType = Literal["correction", "amendment"]


class AuditFeedItem(BaseModel):
    id: uuid.UUID
    type: AuditType
    occurred_at: datetime
    reason: str
    details: dict


def _correction_to_item(row: CorrectionLedger) -> AuditFeedItem:
    return AuditFeedItem(
        id=row.id,
        type="correction",
        occurred_at=row.corrected_at,
        reason=row.reason,
        details={
            "table_name": row.table_name,
            "row_id": str(row.row_id),
            "superseded_by_row_id": str(row.superseded_by_row_id),
        },
    )


def _amendment_to_item(row: PolicyAmendment) -> AuditFeedItem:
    return AuditFeedItem(
        id=row.id,
        type="amendment",
        occurred_at=row.created_at,
        reason=row.reason,
        details={
            "previous_limit_id": str(row.previous_limit_id) if row.previous_limit_id else None,
            "new_limit_id": str(row.new_limit_id),
            "is_override_during_drawdown": row.is_override_during_drawdown,
        },
    )


@router.get("", response_model=list[AuditFeedItem])
async def get_audit_feed(
    db: SessionDep,
    since: date | None = Query(default=None),
    type: AuditType | None = Query(default=None),  # noqa: A002 - query param name per spec
):
    since_dt = datetime.combine(since, time.min, tzinfo=timezone.utc) if since is not None else None

    items: list[AuditFeedItem] = []

    if type is None or type == "correction":
        q = select(CorrectionLedger)
        if since_dt is not None:
            q = q.where(CorrectionLedger.corrected_at >= since_dt)
        rows = (await db.execute(q)).scalars().all()
        items.extend(_correction_to_item(r) for r in rows)

    if type is None or type == "amendment":
        q = select(PolicyAmendment)
        if since_dt is not None:
            q = q.where(PolicyAmendment.created_at >= since_dt)
        rows = (await db.execute(q)).scalars().all()
        items.extend(_amendment_to_item(r) for r in rows)

    items.sort(key=lambda i: i.occurred_at, reverse=True)
    return items
