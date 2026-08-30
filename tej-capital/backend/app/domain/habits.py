import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

HABIT_CATEGORY_VALUES = ("trading", "personal", "body", "sleep")

# Single source of truth for the seed data inserted by migration 0005.
# Kept here (not just in the migration) so tests — which build the schema
# from ORM metadata via Base.metadata.create_all rather than running
# alembic — can seed the same 11 habits without drifting from the
# migration's list.
DEFAULT_HABITS = [
    {"key": "followed_rules", "label": "Followed all trading rules today", "category": "trading", "sort_order": 10},
    {"key": "max_2_trades", "label": "Took ≤ 2 trades today", "category": "trading", "sort_order": 20},
    {"key": "no_1pct_loss", "label": "No single loss over 1% of book", "category": "trading", "sort_order": 30},
    {"key": "journaled_trades", "label": "Logged every closed trade", "category": "trading", "sort_order": 40},
    {"key": "daily_mark", "label": "Entered today's closing equity", "category": "trading", "sort_order": 50},
    {"key": "no_revenge", "label": "No revenge trades", "category": "trading", "sort_order": 60},
    {"key": "npf", "label": "NPF", "category": "personal", "sort_order": 10},
    {"key": "gym", "label": "Went to the gym", "category": "body", "sort_order": 10},
    {"key": "tennis", "label": "Played tennis", "category": "body", "sort_order": 20},
    {"key": "wake_before_9", "label": "Woke up before 9 AM", "category": "sleep", "sort_order": 10},
    {"key": "sleep_before_12", "label": "In bed before midnight", "category": "sleep", "sort_order": 20},
]


class HabitDefinition(Base):
    __tablename__ = "tej_habit_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(
        Enum(*HABIT_CATEGORY_VALUES, name="tej_habit_category", create_type=False), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class HabitLog(Base):
    __tablename__ = "tej_habit_log"

    entry_date: Mapped[date] = mapped_column(Date, primary_key=True)
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tej_habit_definitions.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
