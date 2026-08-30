import calendar
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import SessionDep
from app.domain.habits import HabitDefinition, HabitLog
from app.schemas.habits import (
    HabitDefinitionCreate,
    HabitDefinitionRead,
    HabitDefinitionUpdate,
    HabitLogRead,
    HabitMonthLog,
    HabitStat,
    HabitToggle,
)

router = APIRouter(prefix="/api/habits", tags=["habits"])


def _compute_streaks(true_dates: set[date], today: date) -> tuple[int, int]:
    """current_streak walks back from today while status=true; an
    unanswered (or explicitly false) day breaks it. longest_streak is the
    longest run of calendar-consecutive true dates anywhere in history.
    """
    if not true_dates:
        return 0, 0

    current = 0
    cursor = today
    while cursor in true_dates:
        current += 1
        cursor -= timedelta(days=1)

    ordered = sorted(true_dates)
    longest = run = 1
    for prev, nxt in zip(ordered, ordered[1:]):
        if (nxt - prev).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)
    longest = max(longest, current)

    return current, longest


@router.get("/definitions", response_model=list[HabitDefinitionRead])
async def list_definitions(db: SessionDep):
    rows = (await db.execute(
        select(HabitDefinition)
        .where(HabitDefinition.is_active == True)  # noqa: E712
        .order_by(HabitDefinition.category, HabitDefinition.sort_order)
    )).scalars().all()
    return [HabitDefinitionRead.model_validate(r) for r in rows]


@router.post("/definitions", response_model=HabitDefinitionRead, status_code=201)
async def create_definition(payload: HabitDefinitionCreate, db: SessionDep):
    existing = (await db.execute(
        select(HabitDefinition).where(HabitDefinition.key == payload.key)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail={
            "error": "duplicate_key",
            "hint": f"A habit with key '{payload.key}' already exists.",
        })
    row = HabitDefinition(**payload.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return HabitDefinitionRead.model_validate(row)


@router.patch("/definitions/{habit_id}", response_model=HabitDefinitionRead)
async def update_definition(habit_id: uuid.UUID, payload: dict, db: SessionDep):
    if "key" in payload or "category" in payload:
        raise HTTPException(status_code=409, detail={
            "error": "immutable_field",
            "hint": "key and category cannot be changed after a habit is created.",
        })
    update = HabitDefinitionUpdate.model_validate(payload)

    row = await db.get(HabitDefinition, habit_id)
    if not row:
        raise HTTPException(status_code=404, detail="habit not found")

    data = update.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(row, field, value)

    await db.commit()
    await db.refresh(row)
    return HabitDefinitionRead.model_validate(row)


@router.delete("/definitions/{habit_id}", status_code=204)
async def delete_definition(habit_id: uuid.UUID, db: SessionDep):
    row = await db.get(HabitDefinition, habit_id)
    if not row:
        raise HTTPException(status_code=404, detail="habit not found")
    await db.delete(row)
    await db.commit()


@router.get("/log", response_model=HabitMonthLog)
async def get_month_log(year: int, month: int, db: SessionDep):
    if not (1 <= month <= 12):
        raise HTTPException(status_code=422, detail="month must be between 1 and 12")

    definitions = (await db.execute(
        select(HabitDefinition)
        .where(HabitDefinition.is_active == True)  # noqa: E712
        .order_by(HabitDefinition.category, HabitDefinition.sort_order)
    )).scalars().all()

    days_in_month = calendar.monthrange(year, month)[1]
    first = date(year, month, 1)
    last = date(year, month, days_in_month)
    days = [date(year, month, d).isoformat() for d in range(1, days_in_month + 1)]

    month_logs = (await db.execute(
        select(HabitLog).where(HabitLog.entry_date >= first, HabitLog.entry_date <= last)
    )).scalars().all()

    entries: dict[str, dict[str, bool]] = {}
    month_true_counts: dict[uuid.UUID, int] = {}
    for log in month_logs:
        hid = str(log.habit_id)
        entries.setdefault(hid, {})[log.entry_date.isoformat()] = log.status
        if log.status:
            month_true_counts[log.habit_id] = month_true_counts.get(log.habit_id, 0) + 1

    today = date.today()
    elapsed_end = min(last, today)
    elapsed_days = (elapsed_end - first).days + 1 if elapsed_end >= first else 0

    stats: dict[str, HabitStat] = {}
    for definition in definitions:
        all_true = (await db.execute(
            select(HabitLog.entry_date).where(
                HabitLog.habit_id == definition.id, HabitLog.status == True  # noqa: E712
            )
        )).scalars().all()
        current_streak, longest_streak = _compute_streaks(set(all_true), today)

        true_this_month = month_true_counts.get(definition.id, 0)
        completion_pct = round(true_this_month / elapsed_days * 100, 1) if elapsed_days > 0 else 0.0

        stats[str(definition.id)] = HabitStat(
            current_streak=current_streak,
            longest_streak=longest_streak,
            completion_pct_this_month=completion_pct,
        )

    return HabitMonthLog(
        days=days,
        entries=entries,
        definitions=[HabitDefinitionRead.model_validate(d) for d in definitions],
        stats=stats,
    )


@router.put("/log/{entry_date}/{habit_id}", response_model=HabitLogRead)
async def upsert_log(entry_date: date, habit_id: uuid.UUID, payload: HabitToggle, db: SessionDep):
    definition = await db.get(HabitDefinition, habit_id)
    if not definition:
        raise HTTPException(status_code=404, detail="habit not found")

    row = await db.get(HabitLog, {"entry_date": entry_date, "habit_id": habit_id})
    if row:
        row.status = payload.status
    else:
        row = HabitLog(entry_date=entry_date, habit_id=habit_id, status=payload.status)
        db.add(row)

    await db.commit()
    await db.refresh(row)
    return HabitLogRead.model_validate(row)


@router.delete("/log/{entry_date}/{habit_id}", status_code=204)
async def delete_log(entry_date: date, habit_id: uuid.UUID, db: SessionDep):
    row = await db.get(HabitLog, {"entry_date": entry_date, "habit_id": habit_id})
    if row:
        await db.delete(row)
        await db.commit()
