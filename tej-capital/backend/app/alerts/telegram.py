"""Telegram alerts. Never sends more than one message per (kind, day)."""
from __future__ import annotations
import logging
from datetime import date
from typing import Literal
import httpx

from app.config import get_settings

Kind = Literal["nightly", "immediate", "weekly", "monthly", "data_quality"]
log = logging.getLogger(__name__)

# Per-process dedupe; a real deployment would back this by Postgres or Redis.
_seen_today: set[tuple[str, str]] = set()


async def send_alert(kind: Kind, payload: dict) -> bool:
    s = get_settings()
    if not s.telegram_bot_token or not s.telegram_chat_id:
        log.info("telegram not configured; skipping %s alert", kind)
        return False
    key = (kind, date.today().isoformat())
    if key in _seen_today:
        log.info("telegram already sent for %s today; skipping", kind)
        return False
    text = _format(kind, payload)
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
            json={"chat_id": s.telegram_chat_id, "text": text, "parse_mode": "HTML"},
        )
        r.raise_for_status()
    _seen_today.add(key)
    return True


def _format(kind: Kind, payload: dict) -> str:
    if kind == "nightly":
        return (f"<b>TEJ Nightly · {payload.get('as_of')}</b>\n"
                f"P&L: {payload.get('pnl', '—')}\n"
                f"DD vs kill-switch: {payload.get('dd', '—')}\n"
                f"Breaches: {payload.get('breaches', 0)}\n"
                f"Anomalies: {payload.get('anomalies', 0)}")
    return f"<b>TEJ · {kind}</b>\n{payload}"


async def send_nightly(as_of: str) -> bool:
    return await send_alert("nightly", {"as_of": as_of, "pnl": "—", "dd": "—", "breaches": 0, "anomalies": 0})
