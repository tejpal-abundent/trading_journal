import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.domain.accounts import Account
from app.schemas.accounts import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AccountRead)
async def create_account(payload: AccountCreate, db: SessionDep):
    a = Account(**payload.model_dump())
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return AccountRead.model_validate(a)


@router.get("", response_model=list[AccountRead])
async def list_accounts(db: SessionDep):
    rows = (await db.execute(select(Account).order_by(Account.created_at))).scalars().all()
    return [AccountRead.model_validate(r) for r in rows]


@router.patch("/{account_id}", response_model=AccountRead)
async def update_account(account_id: uuid.UUID, payload: AccountUpdate, db: SessionDep):
    a = await db.get(Account, account_id)
    if not a:
        raise HTTPException(status_code=404, detail="account not found")

    updates = payload.model_dump(exclude_unset=True)

    if "in_composite" in updates and updates["in_composite"] != a.in_composite:
        raise HTTPException(status_code=409, detail={
            "error": "composite_membership_immutable",
            "hint": "R4: composite membership is declared once at account creation and "
                    "cannot be changed afterward. Archive this account and create a new "
                    "one if the composite decision needs to change.",
        })

    for k in ("name", "broker", "currency", "account_type", "exclusion_reason"):
        if k in updates:
            setattr(a, k, updates[k])

    await db.commit()
    await db.refresh(a)
    return AccountRead.model_validate(a)


@router.post("/{account_id}/archive", response_model=AccountRead)
async def archive_account(account_id: uuid.UUID, db: SessionDep):
    a = await db.get(Account, account_id)
    if not a:
        raise HTTPException(status_code=404, detail="account not found")
    a.archived_at = datetime.utcnow()
    await db.commit()
    await db.refresh(a)
    return AccountRead.model_validate(a)
