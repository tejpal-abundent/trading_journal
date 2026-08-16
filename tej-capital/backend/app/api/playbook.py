import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import SessionDep
from app.domain.playbook import PlaybookSetup
from app.schemas.playbook import PlaybookSetupCreate, PlaybookSetupRead

router = APIRouter(prefix="/api/playbook", tags=["playbook"])
MAX_ACTIVE_SETUPS = 5


@router.get("", response_model=list[PlaybookSetupRead])
async def list_setups(db: SessionDep):
    rows = (await db.execute(select(PlaybookSetup).order_by(PlaybookSetup.tag))).scalars().all()
    return [PlaybookSetupRead.model_validate(r) for r in rows]


@router.post("", response_model=PlaybookSetupRead, status_code=201)
async def create_setup(payload: PlaybookSetupCreate, db: SessionDep):
    if payload.is_active:
        active = (await db.execute(
            select(PlaybookSetup).where(PlaybookSetup.is_active == True)  # noqa: E712
        )).scalars().all()
        if len(active) >= MAX_ACTIVE_SETUPS:
            raise HTTPException(status_code=409, detail={
                "error": "too_many_active_setups",
                "hint": f"Product Brief §3 Phase 0: only {MAX_ACTIVE_SETUPS} active setups. "
                        "Retire one first.",
            })
    row = PlaybookSetup(**payload.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return PlaybookSetupRead.model_validate(row)


@router.delete("/{setup_id}", status_code=204)
async def retire_setup(setup_id: uuid.UUID, db: SessionDep):
    row = await db.get(PlaybookSetup, setup_id)
    if not row:
        raise HTTPException(status_code=404, detail="setup not found")
    row.is_active = False
    row.retired_at = datetime.utcnow()
    await db.commit()
