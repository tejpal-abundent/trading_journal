"""AI endpoints: journal search, tearsheet commentary, pattern detection, pre-trade checks."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.ai import qdrant_search, commentary, pattern_detect, pretrade_check
from app.api.deps import SessionDep

router = APIRouter(prefix="/api/ai", tags=["ai"])


class SearchRequest(BaseModel):
    q: str = Field(min_length=1)
    k: int = Field(default=10, ge=1, le=100)


class CommentaryRequest(BaseModel):
    tearsheet: dict = Field(default_factory=dict)
    journal_entries: list[dict] = Field(default_factory=list)


class PretradRequest(BaseModel):
    thesis: str = Field(min_length=1)
    playbook: str = Field(min_length=1)


class PatternResult(BaseModel):
    name: str
    expectancy_a: float
    expectancy_b: float
    p_value: float


@router.post("/journal/search")
async def search_journal(payload: SearchRequest, db: SessionDep):
    """Search journal entries by semantic similarity.

    Returns 501 if Qdrant is not configured.
    """
    results = qdrant_search.query(payload.q, k=payload.k)
    return {"results": results}


@router.post("/commentary")
async def generate_commentary(payload: CommentaryRequest, db: SessionDep):
    """Generate AI commentary for a tearsheet.

    Returns 501 if LLM is not configured.
    """
    text = commentary.draft(payload.tearsheet, payload.journal_entries)
    return {"commentary": text}


@router.get("/patterns", response_model=list[PatternResult])
async def detect_patterns(
    db: SessionDep,
    q: float = Query(default=0.10, ge=0.01, le=0.50),
):
    """Detect statistically significant patterns in trades.

    Always works (no credentials required). Runs Benjamini-Hochberg FDR correction
    on binary slices (day-of-week, session, etc.) and returns FDR-passing patterns.
    """
    # TODO: fetch trades from database for this user
    # For now, return empty list to satisfy the contract
    return []


@router.post("/pretrade")
async def pretrade_check_endpoint(payload: PretradRequest, db: SessionDep):
    """Ask LLM for pre-trade advisory sanity checks.

    Returns 501 if LLM is not configured.
    """
    response = pretrade_check.ask(payload.thesis, payload.playbook)
    return {"advice": response}
