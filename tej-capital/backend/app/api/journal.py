import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select

from app.api.deps import SessionDep
from app.domain.journal import JournalEntry

router = APIRouter(prefix="/api/journal", tags=["journal"])


class JournalEntryCreate(BaseModel):
    entry_date: date
    body: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class JournalEntryUpdate(BaseModel):
    entry_date: date | None = None
    body: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None


class JournalEntryRead(BaseModel):
    id: uuid.UUID
    entry_date: date
    body: str
    tags: list[str]

    model_config = {"from_attributes": True}


@router.post("", status_code=201, response_model=JournalEntryRead)
async def create_journal_entry(payload: JournalEntryCreate, db: SessionDep):
    row = JournalEntry(
        id=uuid.uuid4(),
        entry_date=payload.entry_date,
        body=payload.body,
        tags=payload.tags,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return JournalEntryRead.model_validate(row)


@router.get("", response_model=list[JournalEntryRead])
async def list_journal_entries(
    db: SessionDep,
    since: date | None = Query(default=None),
    tag: str | None = Query(default=None),
):
    stmt = select(JournalEntry)

    conditions = []
    if since is not None:
        conditions.append(JournalEntry.entry_date >= since)
    if tag is not None:
        conditions.append(JournalEntry.tags.contains([tag]))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    rows = (await db.execute(stmt.order_by(JournalEntry.entry_date.desc()))).scalars().all()
    return [JournalEntryRead.model_validate(r) for r in rows]


@router.patch("/{entry_id}", response_model=JournalEntryRead)
async def update_journal_entry(entry_id: uuid.UUID, payload: JournalEntryUpdate, db: SessionDep):
    row = (await db.execute(
        select(JournalEntry).where(JournalEntry.id == entry_id)
    )).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail={
            "error": "entry_not_found",
            "hint": "No journal entry with that ID exists.",
        })

    if payload.entry_date is not None:
        row.entry_date = payload.entry_date
    if payload.body is not None:
        row.body = payload.body
    if payload.tags is not None:
        row.tags = payload.tags

    await db.commit()
    await db.refresh(row)
    return JournalEntryRead.model_validate(row)


@router.delete("/{entry_id}", status_code=204)
async def delete_journal_entry(entry_id: uuid.UUID, db: SessionDep):
    """Hard-delete a journal entry. Journal entries are the user's private
    notes and not part of the append-only trading record (R1), so a plain
    DELETE is fine — no correction ledger, no supersede."""
    row = (await db.execute(
        select(JournalEntry).where(JournalEntry.id == entry_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail={
            "error": "entry_not_found",
            "hint": "No journal entry with that ID exists.",
        })
    await db.delete(row)
    await db.commit()
