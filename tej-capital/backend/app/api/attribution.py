from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from app.api.deps import SessionDep
from app.core import attribution, trades as trades_core
from app.services.snapshot import _load_series

router = APIRouter(prefix="/api/attribution", tags=["attribution"])


@router.get("")
async def get_attribution(
    db: SessionDep,
    by: Literal["setup", "asset", "session", "htf", "dow"] = Query(...),
):
    """Returns list of grouped stats with verdict tags."""
    _returns, trades_df, _nav_count = await _load_series(db, "composite", None)

    if len(trades_df) == 0:
        return []

    return attribution.grouped_stats(trades_df, by=by)


@router.get("/concentration")
async def get_concentration(db: SessionDep):
    """Returns top_n_concentration payload."""
    _returns, trades_df, _nav_count = await _load_series(db, "composite", None)

    if len(trades_df) == 0:
        return {"top_n_share": None, "top_n_ids": []}

    return trades_core.top_n_concentration(trades_df, n=3)


@router.get("/compliance-gap")
async def get_compliance_gap(db: SessionDep):
    """Returns compliance_gap_significance payload."""
    _returns, trades_df, _nav_count = await _load_series(db, "composite", None)

    if len(trades_df) == 0:
        return {
            "compliant_expectancy": None,
            "noncompliant_expectancy": None,
            "p_value": None,
        }

    return trades_core.compliance_gap_significance(trades_df)
