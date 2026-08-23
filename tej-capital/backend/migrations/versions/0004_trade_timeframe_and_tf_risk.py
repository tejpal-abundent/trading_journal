"""add trade timeframe and per-timeframe risk limits

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-23

Adds `timeframe` as first-class trade metadata (nullable — historical
trades predate this field and shouldn't fail validation) and a nullable
`risk_by_timeframe` JSONB map on tej_settings so per-timeframe risk caps
are configurable. Rationale: smaller timeframes have worse signal-to-noise,
so the default halves the allowed risk on 1m/5m relative to 15m+
(enforced in app.api.trades._validate_tf_risk, defaults in
app.schemas.settings.DEFAULT_RISK_BY_TIMEFRAME).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TIMEFRAME_VALUES = ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w")


def upgrade() -> None:
    tej_timeframe = sa.Enum(*TIMEFRAME_VALUES, name="tej_timeframe")
    tej_timeframe.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "tej_trades",
        sa.Column("timeframe", tej_timeframe, nullable=True),
    )
    op.add_column(
        "tej_settings",
        sa.Column("risk_by_timeframe", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tej_settings", "risk_by_timeframe")
    op.drop_column("tej_trades", "timeframe")
    op.execute("DROP TYPE IF EXISTS tej_timeframe")
