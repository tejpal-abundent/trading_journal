"""Correction helper. Enforces R1 (append-only): every correction inserts a
new row and stamps `superseded_by` on the old one, plus writes a
`tej_corrections_ledger` row in the same transaction.
"""
from __future__ import annotations

import uuid

from sqlalchemy import literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import CorrectionLedger

MIN_REASON = 10

# Columns that carry a server_default (DB fills these in) and should not be
# copied from the transient `new_row` Python object into the raw INSERT.
_SERVER_DEFAULTED_COLUMNS = {"entered_at"}


class InvalidReason(Exception):
    pass


async def apply_correction(db: AsyncSession, *, table_name: str, old_row, new_row, reason: str):
    """Supersede ``old_row`` with ``new_row`` and record the correction.

    Both rows live in a table with a partial unique index on
    ``(account_id, as_of_date) WHERE superseded_by IS NULL`` (R1: only one
    "current" row per account/day). That index is checked immediately,
    per-statement — not deferred to end of transaction. Meanwhile
    ``superseded_by`` is a FOREIGN KEY back into the same table, so
    ``old_row.superseded_by = new_row.id`` requires new_row to already
    exist.

    Running the UPDATE (old -> superseded) and INSERT (new row) as two
    separate statements deadlocks against these two constraints no matter
    the order:
      - UPDATE then INSERT: fails the FK check (new_row doesn't exist yet).
      - INSERT then UPDATE: fails the unique index (old_row and new_row both
        briefly have superseded_by IS NULL for the same account/day).

    Postgres FK constraint triggers check at *end of statement* even when
    NOT DEFERRABLE INITIALLY IMMEDIATE (the default). So combining both
    writes into a single SQL statement — an UPDATE ... RETURNING CTE feeding
    an INSERT ... SELECT — makes the FK check happen only after the INSERT
    within that same statement has already created new_row, while the
    unique index sees old_row's slot vacated (by the UPDATE) before the
    INSERT's row is evaluated, since the INSERT's SELECT is data-dependent
    on the UPDATE's CTE output and therefore runs after it.

    Does not commit — caller controls the transaction boundary so this can
    be combined with other writes atomically. Returns the persisted
    ``new_row`` (freshly loaded from the identity map / DB).
    """
    if not reason or len(reason.strip()) < MIN_REASON:
        raise InvalidReason(f"reason must be at least {MIN_REASON} characters")

    table = new_row.__table__
    insert_cols = [c.name for c in table.columns if c.name not in _SERVER_DEFAULTED_COLUMNS]
    values = {name: getattr(new_row, name) for name in insert_cols}

    deactivated = (
        table.update()
        .where(table.c.id == old_row.id)
        .values(superseded_by=new_row.id, superseded_reason=reason)
        .returning(table.c.id)
        .cte("deactivated")
    )
    insert_stmt = table.insert().from_select(
        list(values.keys()),
        select(*[
            literal(v, type_=table.c[k].type).label(k) for k, v in values.items()
        ]).select_from(deactivated),
    )
    await db.execute(insert_stmt)

    db.add(CorrectionLedger(
        id=uuid.uuid4(),
        table_name=table_name,
        row_id=old_row.id,
        superseded_by_row_id=new_row.id,
        reason=reason,
    ))
    await db.flush()

    # old_row's Python-side state is now stale (its superseded_by/reason
    # were changed by raw SQL, bypassing the ORM); refresh so any later use
    # of that instance in this session reflects the DB.
    await db.refresh(old_row)

    # new_row was never added to the session (it was written via raw SQL),
    # so it isn't in the identity map yet — fetch it so callers can use it
    # like any other persistent ORM instance (e.g. db.refresh after commit).
    return await db.get(type(new_row), new_row.id)
