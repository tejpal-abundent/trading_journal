import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete

from app.db import SessionLocal
from app.domain.habits import DEFAULT_HABITS, HabitDefinition, HabitLog
from app.main import app

# These tests run against the real dev Postgres database (app.db.engine),
# same as tests/api/test_settings.py and test_rhythm.py — habit definitions
# and log rows created here are cleaned up explicitly rather than relying
# on a throwaway test database.


async def _create_definition(ac, key=None, label="Test habit", category="trading", sort_order=999):
    key = key or f"test_{uuid.uuid4().hex[:8]}"
    r = await ac.post("/api/habits/definitions", json={
        "key": key, "label": label, "category": category, "sort_order": sort_order,
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _cleanup_definition(habit_id: str):
    async with SessionLocal() as s:
        await s.execute(delete(HabitLog).where(HabitLog.habit_id == uuid.UUID(habit_id)))
        await s.execute(delete(HabitDefinition).where(HabitDefinition.id == uuid.UUID(habit_id)))
        await s.commit()


async def _seed_log(habit_id: str, entry_date: date, status: bool):
    async with SessionLocal() as s:
        s.add(HabitLog(habit_id=uuid.UUID(habit_id), entry_date=entry_date, status=status))
        await s.commit()


@pytest.mark.asyncio
async def test_seed_definitions_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/habits/definitions")
    assert r.status_code == 200
    body = r.json()
    by_key = {row["key"]: row for row in body}

    expected_keys = {h["key"] for h in DEFAULT_HABITS}
    assert expected_keys.issubset(by_key.keys())
    assert len(DEFAULT_HABITS) == 11

    for h in DEFAULT_HABITS:
        row = by_key[h["key"]]
        assert row["label"] == h["label"]
        assert row["category"] == h["category"]
        assert row["is_active"] is True


@pytest.mark.asyncio
async def test_create_definition_unique_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await _create_definition(ac)
        try:
            dup = await ac.post("/api/habits/definitions", json={
                "key": created["key"], "label": "Duplicate", "category": "trading", "sort_order": 1,
            })
            assert dup.status_code == 409
        finally:
            await _cleanup_definition(created["id"])


@pytest.mark.asyncio
async def test_definition_key_immutable():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await _create_definition(ac)
        try:
            r = await ac.patch(f"/api/habits/definitions/{created['id']}", json={
                "key": "renamed_key", "label": "New label",
            })
            assert r.status_code == 409

            r2 = await ac.patch(f"/api/habits/definitions/{created['id']}", json={
                "category": "personal",
            })
            assert r2.status_code == 409

            # a legitimate rename (no key/category) still works
            ok = await ac.patch(f"/api/habits/definitions/{created['id']}", json={"label": "Renamed fine"})
            assert ok.status_code == 200
            assert ok.json()["label"] == "Renamed fine"
            assert ok.json()["key"] == created["key"]
        finally:
            await _cleanup_definition(created["id"])


@pytest.mark.asyncio
async def test_toggle_habit_upserts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await _create_definition(ac)
        habit_id = created["id"]
        entry_date = date(2020, 1, 15)
        try:
            r1 = await ac.put(f"/api/habits/log/{entry_date.isoformat()}/{habit_id}", json={"status": True})
            assert r1.status_code == 200
            assert r1.json()["status"] is True

            r2 = await ac.put(f"/api/habits/log/{entry_date.isoformat()}/{habit_id}", json={"status": False})
            assert r2.status_code == 200
            assert r2.json()["status"] is False

            month = await ac.get("/api/habits/log", params={"year": 2020, "month": 1})
            assert month.status_code == 200
            entries = month.json()["entries"]
            assert entries[habit_id][entry_date.isoformat()] is False
        finally:
            await _cleanup_definition(habit_id)


@pytest.mark.asyncio
async def test_delete_log_entry_returns_to_unanswered():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await _create_definition(ac)
        habit_id = created["id"]
        entry_date = date(2020, 2, 10)
        try:
            await ac.put(f"/api/habits/log/{entry_date.isoformat()}/{habit_id}", json={"status": True})

            d = await ac.delete(f"/api/habits/log/{entry_date.isoformat()}/{habit_id}")
            assert d.status_code == 204

            month = await ac.get("/api/habits/log", params={"year": 2020, "month": 2})
            entries = month.json()["entries"]
            assert habit_id not in entries or entry_date.isoformat() not in entries.get(habit_id, {})
        finally:
            await _cleanup_definition(habit_id)


@pytest.mark.asyncio
async def test_month_log_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/habits/log", params={"year": 2026, "month": 4})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"days", "entries", "definitions", "stats"}
    assert body["days"][0] == "2026-04-01"
    assert body["days"][-1] == "2026-04-30"
    assert len(body["days"]) == 30
    assert isinstance(body["entries"], dict)
    assert isinstance(body["definitions"], list)
    assert isinstance(body["stats"], dict)
    assert len(body["definitions"]) >= 11


@pytest.mark.asyncio
async def test_streak_computation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await _create_definition(ac)
        habit_id = created["id"]
        today = date.today()
        try:
            for offset in range(5):
                await _seed_log(habit_id, today - timedelta(days=offset), True)

            month = await ac.get("/api/habits/log", params={"year": today.year, "month": today.month})
            stats = month.json()["stats"][habit_id]
            assert stats["current_streak"] == 5
            assert stats["longest_streak"] == 5
        finally:
            await _cleanup_definition(habit_id)


@pytest.mark.asyncio
async def test_streak_breaks_on_unanswered_day():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await _create_definition(ac)
        habit_id = created["id"]
        today = date.today()
        try:
            # today, -1, -2 true; -3 left unanswered (gap); -4..-7 true (longer older run)
            for offset in (0, 1, 2):
                await _seed_log(habit_id, today - timedelta(days=offset), True)
            for offset in (4, 5, 6, 7):
                await _seed_log(habit_id, today - timedelta(days=offset), True)

            month = await ac.get("/api/habits/log", params={"year": today.year, "month": today.month})
            stats = month.json()["stats"][habit_id]
            assert stats["current_streak"] == 3
            assert stats["longest_streak"] == 4
        finally:
            await _cleanup_definition(habit_id)
