"""add daily/weekly/monthly rhythm targets to tej_settings

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-23

Adds three pacing-target columns backing the new Rhythm page: daily,
weekly, and monthly target return percentages. Defaults reflect the
user's throttle-model exploration: 0.30% daily (1.5% / 5 trading days),
1.5% weekly, and (1.015)^4 - 1 ~= 6.14% monthly.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tej_settings",
        sa.Column("daily_target_pct", sa.Numeric(6, 4), nullable=False, server_default="0.003"),
    )
    op.add_column(
        "tej_settings",
        sa.Column("weekly_target_pct", sa.Numeric(6, 4), nullable=False, server_default="0.015"),
    )
    op.add_column(
        "tej_settings",
        sa.Column("monthly_target_pct", sa.Numeric(6, 4), nullable=False, server_default="0.0614"),
    )


def downgrade() -> None:
    op.drop_column("tej_settings", "monthly_target_pct")
    op.drop_column("tej_settings", "weekly_target_pct")
    op.drop_column("tej_settings", "daily_target_pct")
