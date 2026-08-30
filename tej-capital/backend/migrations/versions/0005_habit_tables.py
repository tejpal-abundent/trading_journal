"""add habit tracker tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-30

Adds `tej_habit_definitions` (the editable list of yes/no behaviours the
user tracks daily) and `tej_habit_log` (one row per day a habit was
explicitly answered — absence of a row means "not answered", not false).
Seeds the 11 default habits Jim asked for across four categories so the
Habits page has content on first load; the habit list itself is editable
via the API afterwards, no migration required to add/rename/retire one.
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

HABIT_CATEGORY_VALUES = ("trading", "personal", "body", "sleep")

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


def upgrade() -> None:
    habit_category = sa.Enum(*HABIT_CATEGORY_VALUES, name="tej_habit_category")

    op.create_table(
        "tej_habit_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(60), nullable=False, unique=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("category", habit_category, nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tej_habit_log",
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column(
            "habit_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tej_habit_definitions.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("status", sa.Boolean, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("entry_date", "habit_id"),
    )
    op.create_index("ix_tej_habit_log_by_date", "tej_habit_log", ["entry_date"])
    op.create_index("ix_tej_habit_log_by_habit", "tej_habit_log", ["habit_id", "entry_date"])

    habit_definitions_table = sa.table(
        "tej_habit_definitions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", sa.String),
        sa.column("label", sa.String),
        sa.column("category", sa.Enum(name="tej_habit_category")),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(habit_definitions_table, [
        {
            "id": uuid.uuid4(),
            "key": h["key"],
            "label": h["label"],
            "category": h["category"],
            "sort_order": h["sort_order"],
            "is_active": True,
        }
        for h in DEFAULT_HABITS
    ])


def downgrade() -> None:
    op.drop_index("ix_tej_habit_log_by_habit", table_name="tej_habit_log")
    op.drop_index("ix_tej_habit_log_by_date", table_name="tej_habit_log")
    op.drop_table("tej_habit_log")
    op.drop_table("tej_habit_definitions")
    op.execute("DROP TYPE IF EXISTS tej_habit_category")
