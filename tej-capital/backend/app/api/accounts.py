import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, select, update

from app.api.deps import SessionDep
from app.domain.accounts import Account
from app.domain.audit import CorrectionLedger
from app.domain.flows import CashFlow
from app.domain.metrics import MetricSnapshot
from app.domain.nav import NavSnapshot
from app.domain.reconciliations import BrokerReconciliation
from app.domain.trades import Trade
from app.schemas.accounts import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

# Confirmation string required in the query param to purge a demo account.
# Deliberately a phrase, not just "true" — makes a typo-driven purge impossible.
PURGE_CONFIRM = "purge-this-demo-account"


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


@router.post("/{account_id}/purge", status_code=status.HTTP_200_OK)
async def purge_demo_account(
    account_id: uuid.UUID,
    db: SessionDep,
    confirm: str = Query(..., description=f"must equal '{PURGE_CONFIRM}'"),
):
    """Hard-delete a demo account and every row scoped to it.

    Escape hatch to R1 (append-only), gated on TWO conditions so it cannot
    fire against real capital:

      1. Account must have `account_type == 'demo'` (400 otherwise).
      2. `confirm` query param must equal PURGE_CONFIRM exactly (400).

    Cascade order matters because trades / nav / flows have self-referencing
    FKs via `superseded_by`. We null those first, then delete children
    (metric_snapshots, broker_reconciliations, corrections_ledger rows for
    this account's row ids, trades, cash_flows, nav_snapshots), then the
    account itself.
    """
    if confirm != PURGE_CONFIRM:
        raise HTTPException(status_code=400, detail={
            "error": "confirmation_required",
            "hint": f"Pass ?confirm={PURGE_CONFIRM} to acknowledge this is destructive.",
        })

    a = await db.get(Account, account_id)
    if not a:
        raise HTTPException(status_code=404, detail="account not found")

    if a.account_type != "demo":
        raise HTTPException(status_code=403, detail={
            "error": "purge_forbidden_on_non_demo",
            "account_type": a.account_type,
            "hint": "This endpoint only accepts demo accounts. Real accounts are "
                    "append-only (R1). Use POST /archive to hide them from the UI "
                    "without losing history.",
        })

    counts: dict[str, int] = {}

    # 1. Collect row ids that need corrections_ledger cleanup BEFORE deleting.
    trade_ids = [t.id for t in (await db.execute(
        select(Trade).where(Trade.account_id == account_id)
    )).scalars().all()]
    nav_ids = [n.id for n in (await db.execute(
        select(NavSnapshot).where(NavSnapshot.account_id == account_id)
    )).scalars().all()]
    flow_ids = [f.id for f in (await db.execute(
        select(CashFlow).where(CashFlow.account_id == account_id)
    )).scalars().all()]

    # 2. Null self-referential FKs so DELETE doesn't hit constraint violations
    #    when a superseded row is removed before its superseder.
    await db.execute(update(Trade).where(Trade.account_id == account_id).values(superseded_by=None))
    await db.execute(update(NavSnapshot).where(NavSnapshot.account_id == account_id).values(superseded_by=None))
    await db.execute(update(CashFlow).where(CashFlow.account_id == account_id).values(superseded_by=None))

    # 3. Delete corrections_ledger rows referencing this account's rows.
    if trade_ids:
        r = await db.execute(delete(CorrectionLedger).where(
            CorrectionLedger.table_name == "tej_trades",
            CorrectionLedger.row_id.in_(trade_ids),
        ))
        counts["corrections_trades"] = r.rowcount or 0
    if nav_ids:
        r = await db.execute(delete(CorrectionLedger).where(
            CorrectionLedger.table_name == "tej_nav_snapshots",
            CorrectionLedger.row_id.in_(nav_ids),
        ))
        counts["corrections_nav"] = r.rowcount or 0
    if flow_ids:
        r = await db.execute(delete(CorrectionLedger).where(
            CorrectionLedger.table_name == "tej_cash_flows",
            CorrectionLedger.row_id.in_(flow_ids),
        ))
        counts["corrections_flows"] = r.rowcount or 0

    # 4. Delete per-account children of the account.
    for model, key in (
        (MetricSnapshot, "metric_snapshots"),
        (BrokerReconciliation, "broker_reconciliations"),
        (Trade, "trades"),
        (CashFlow, "cash_flows"),
        (NavSnapshot, "nav_snapshots"),
    ):
        r = await db.execute(delete(model).where(model.account_id == account_id))
        counts[key] = r.rowcount or 0

    # 5. The account itself.
    await db.delete(a)

    await db.commit()

    return {
        "account_id": str(account_id),
        "deleted": counts,
        "account_removed": True,
    }
