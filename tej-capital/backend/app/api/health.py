from fastapi import APIRouter
from sqlalchemy import text
from app.api.deps import SessionDep
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(db: SessionDep):
    s = get_settings()
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unreachable"
    return {
        "status": "ok",
        "db": db_status,
        "integrations": {
            "telegram": bool(s.telegram_bot_token),
            "qdrant": bool(s.qdrant_url),
            "llm": bool(s.llm_api_key),
            "mt5": bool(s.mt5_login),
            "bybit": bool(s.bybit_api_key),
            "darwinex": bool(s.darwinex_api_key),
        },
    }
