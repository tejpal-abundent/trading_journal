import pytest
from app.alerts.telegram import send_alert, _seen_today


@pytest.mark.asyncio
async def test_send_alert_noop_when_unconfigured(monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: type("S", (), {
        "telegram_bot_token": None, "telegram_chat_id": None,
    })())
    _seen_today.clear()
    r = await send_alert("nightly", {"pnl": 42})
    assert r is False


@pytest.mark.asyncio
async def test_send_alert_deduped_per_day():
    _seen_today.clear()
    _seen_today.add(("nightly", "2026-08-16"))
    r = await send_alert("nightly", {"pnl": 42})
    assert r is False
