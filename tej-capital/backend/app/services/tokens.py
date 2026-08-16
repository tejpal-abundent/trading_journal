"""Allocator token generation/validation. Tokens gate the read-only,
redacted allocator tearsheet view (`GET /api/allocator/view`)."""
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.allocator import AllocatorToken


def generate_token() -> str:
    return secrets.token_urlsafe(32)


async def validate(db: AsyncSession, token: str) -> AllocatorToken | None:
    """Returns the token row if it exists, isn't revoked, and hasn't expired.
    Returns None otherwise (caller maps that to a 401)."""
    row = (await db.execute(
        select(AllocatorToken).where(AllocatorToken.token == token)
    )).scalar_one_or_none()
    if not row:
        return None
    if row.revoked_at is not None:
        return None
    if row.expires_at <= datetime.now(tz=timezone.utc):
        return None
    return row
