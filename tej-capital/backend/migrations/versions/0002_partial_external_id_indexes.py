"""partial external_id unique indexes on trades and flows

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-16

Corrects a bug flagged during Task 15: `ux_tej_trades_external` and
`ux_tej_flows_external` were plain (non-partial) unique constraints on
(account_id, external_id). A correction (POST /trades/{id}/correct)
supersedes the old row but carries its external_id forward onto the new
row — with a plain unique constraint the old row (still present, just
`superseded_by` set) permanently collides with the new one. CSV import
(Task 21) populates external_id on every imported trade/flow, so this
becomes actively hit as soon as an imported row is corrected.

The fix: scope uniqueness to *current* rows only via a partial index
`WHERE superseded_by IS NULL`, matching the pattern already used for
`ux_tej_nav_current_per_account_day` / `ix_tej_policy_current` in 0001.
This also gives CSV re-import its idempotency: a second import of the
same file inserts nothing new because ON CONFLICT targets this index.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ux_tej_trades_external", "tej_trades", type_="unique")
    op.drop_constraint("ux_tej_flows_external", "tej_cash_flows", type_="unique")

    op.create_index(
        "ux_tej_trades_external",
        "tej_trades",
        ["account_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("superseded_by IS NULL"),
    )
    op.create_index(
        "ux_tej_flows_external",
        "tej_cash_flows",
        ["account_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("superseded_by IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_tej_trades_external", table_name="tej_trades")
    op.drop_index("ux_tej_flows_external", table_name="tej_cash_flows")

    op.create_unique_constraint(
        "ux_tej_trades_external", "tej_trades", ["account_id", "external_id"]
    )
    op.create_unique_constraint(
        "ux_tej_flows_external", "tej_cash_flows", ["account_id", "external_id"]
    )
