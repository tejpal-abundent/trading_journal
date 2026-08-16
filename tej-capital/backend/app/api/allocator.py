"""Token-gated, read-only allocator view. `GET /view` deliberately never
returns journal content or per-trade/per-account emotional or balance
fields — allocators get the composite tearsheet only. Enforced here (not
left to the frontend) via an explicit redaction pass over the tearsheet
payload."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import SessionDep
from app.domain.allocator import AllocatorToken
from app.schemas.allocator import AllocatorTokenCreate, AllocatorTokenRead
from app.services import tokens
from app.services.snapshot import compute_tearsheet

router = APIRouter(prefix="/api/allocator", tags=["allocator"])

# Any key (at any nesting depth) matching these names is stripped from the
# allocator-facing payload. This is defense-in-depth: compute_tearsheet's
# output today never carries journal content, per-trade state_of_mind /
# one_sentence_takeaway, or per-account balances, but we don't rely on that
# staying true — the redaction is enforced here regardless of shape.
_REDACTED_KEYS = {
    "journal", "journal_entries", "state_of_mind", "one_sentence_takeaway",
    "account_balances", "account_balance", "accounts", "balance",
}


def _redact(obj):
    if isinstance(obj, dict):
        return {k: _redact(v) for k, v in obj.items() if k not in _REDACTED_KEYS}
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


@router.post("/tokens", response_model=AllocatorTokenRead, status_code=201)
async def create_token(payload: AllocatorTokenCreate, db: SessionDep):
    row = AllocatorToken(
        id=uuid.uuid4(),
        token=tokens.generate_token(),
        label=payload.label,
        expires_at=payload.expires_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return AllocatorTokenRead.model_validate(row)


@router.delete("/tokens/{token_id}", status_code=204)
async def revoke_token(token_id: uuid.UUID, db: SessionDep):
    row = await db.get(AllocatorToken, token_id)
    if not row:
        raise HTTPException(status_code=404, detail={
            "error": "token_not_found",
            "hint": "No allocator token with that ID exists.",
        })
    row.revoked_at = datetime.now(tz=timezone.utc)
    await db.commit()


@router.get("/view")
async def get_allocator_view(db: SessionDep, token: str = Query(...)):
    tok = await tokens.validate(db, token)
    if tok is None:
        raise HTTPException(status_code=401, detail={
            "error": "invalid_token",
            "hint": "Token is missing, unknown, expired, or has been revoked.",
        })

    tearsheet = await compute_tearsheet(db, "composite", None)
    redacted = _redact(tearsheet)

    return {
        "label": tok.label,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        **redacted,
    }
