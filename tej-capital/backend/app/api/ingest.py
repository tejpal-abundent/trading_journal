import json
import uuid
from datetime import date, datetime, timezone

import pandas as pd
from fastapi import APIRouter, Form, HTTPException, Query, UploadFile
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.deps import SessionDep
from app.domain.flows import CashFlow
from app.domain.trades import Trade
from app.ingest.csv_import import CsvAdapter

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

# A broker CSV can legitimately contain a trader's entire history, so
# "no since given" means "everything".
DEFAULT_SINCE = date(1900, 1, 1)


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    ts = pd.to_datetime(value).to_pydatetime()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


@router.post("/csv")
async def import_csv(
    account_id: uuid.UUID,
    db: SessionDep,
    file: UploadFile,
    mapping: str = Form(...),
    since: date = Query(default=DEFAULT_SINCE),
):
    """Import a broker-exported CSV of closed trades (and, if the mapping
    includes flow columns, cash flows) into the given account.

    Idempotent: re-posting the same file is a no-op. Insertion targets the
    partial unique index on (account_id, external_id) WHERE superseded_by
    IS NULL (migration 0002) via ON CONFLICT DO NOTHING, so a row already
    present — imported or since corrected — is silently skipped rather
    than raising.

    Imported trades arrive without setup_id/risk_amount and so are picked
    up by the existing enrichment queue (GET /api/trades/enrichment).
    """
    try:
        mapping_dict = json.loads(mapping)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="mapping must be valid JSON")

    csv_bytes = await file.read()
    try:
        adapter = CsvAdapter(csv_bytes, mapping_dict)
        trades = adapter.fetch_closed_trades(since)
        flows = adapter.fetch_flows(since)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"could not parse CSV with given mapping: {e}")

    trades_imported = 0
    trades_skipped = 0
    for t in trades:
        stmt = pg_insert(Trade.__table__).values(
            id=uuid.uuid4(),
            account_id=account_id,
            instrument=t.instrument,
            direction=t.direction,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            position_size=t.position_size,
            gross_pnl=t.gross_pnl,
            costs=t.costs,
            opened_at=_parse_dt(t.opened_at),
            closed_at=_parse_dt(t.closed_at),
            external_id=t.external_id,
        ).on_conflict_do_nothing(
            index_elements=["account_id", "external_id"],
            index_where=text("superseded_by IS NULL"),
        )
        result = await db.execute(stmt)
        if result.rowcount:
            trades_imported += 1
        else:
            trades_skipped += 1

    flows_imported = 0
    flows_skipped = 0
    for f in flows:
        stmt = pg_insert(CashFlow.__table__).values(
            id=uuid.uuid4(),
            account_id=account_id,
            as_of_date=f.as_of_date,
            amount=f.amount,
            flow_type=f.flow_type,
            external_id=f.external_id,
        ).on_conflict_do_nothing(
            index_elements=["account_id", "external_id"],
            index_where=text("superseded_by IS NULL"),
        )
        result = await db.execute(stmt)
        if result.rowcount:
            flows_imported += 1
        else:
            flows_skipped += 1

    await db.commit()

    return {
        "trades_imported": trades_imported,
        "trades_skipped": trades_skipped,
        "flows_imported": flows_imported,
        "flows_skipped": flows_skipped,
    }
