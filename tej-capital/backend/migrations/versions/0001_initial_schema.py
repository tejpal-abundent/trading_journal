"""initial tej_capital schema

Revision ID: 0001
Revises:
Create Date: 2026-08-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

NUMERIC_MONEY = sa.Numeric(20, 8)


def upgrade() -> None:
    # Enums
    account_type = sa.Enum("live", "prop_funded", "prop_evaluation", "demo", "verified_mirror",
                           name="tej_account_type")
    flow_type = sa.Enum("deposit", "withdrawal", "prop_payout", "platform_fee",
                        "transfer_in", "transfer_out", name="tej_flow_type")
    flow_timing = sa.Enum("start_of_day", "end_of_day", name="tej_flow_timing")
    direction = sa.Enum("long", "short", name="tej_direction")
    session_enum = sa.Enum("asia", "london", "london_ny", "new_york", "late_ny", name="tej_session")
    exec_grade = sa.Enum("A", "B", "C", "D", name="tej_exec_grade")
    mind_state = sa.Enum("calm", "rushed", "frustrated", "overconfident", "tilted", name="tej_mind_state")
    limit_type = sa.Enum(
        "risk_per_trade", "concurrent_open_risk", "daily_loss", "weekly_loss", "monthly_loss",
        "drawdown_killswitch", "asset_class_concentration", "risk_sizing_consistency",
        "avg_loser_vs_1r", "rule_compliance_rate", name="tej_limit_type",
    )
    limit_unit = sa.Enum("pct", "r", "abs", name="tej_limit_unit")
    policy_section = sa.Enum(
        "mandate", "method", "time_horizon", "position_sizing", "correlation",
        "stop_discipline", "news_policy", "leverage", "valuation", "custody",
        "amendment_procedure", "review_cadence", name="tej_policy_section",
    )
    recon_status = sa.Enum("ok", "discrepancy", "unexplained", name="tej_recon_status")
    metric_scope = sa.Enum("composite", "per_account", name="tej_metric_scope")

    op.create_table(
        "tej_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("broker", sa.String(120), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("account_type", account_type, nullable=False),
        sa.Column("in_composite", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("exclusion_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "in_composite = true OR (exclusion_reason IS NOT NULL AND char_length(exclusion_reason) >= 10)",
            name="tej_accounts_exclusion_reason_required",
        ),
    )

    op.create_table(
        "tej_nav_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_accounts.id"), nullable=False),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("closing_equity", NUMERIC_MONEY, nullable=False),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_nav_snapshots.id"), nullable=True),
        sa.Column("superseded_reason", sa.Text, nullable=True),
        sa.Column("entered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("closing_equity >= 0", name="tej_nav_positive"),
    )
    op.create_index(
        "ux_tej_nav_current_per_account_day",
        "tej_nav_snapshots",
        ["account_id", "as_of_date"],
        unique=True,
        postgresql_where=sa.text("superseded_by IS NULL"),
    )

    op.create_table(
        "tej_cash_flows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_accounts.id"), nullable=False),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("amount", NUMERIC_MONEY, nullable=False),
        sa.Column("flow_type", flow_type, nullable=False),
        sa.Column("flow_timing", flow_timing, nullable=False, server_default="end_of_day"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_cash_flows.id"), nullable=True),
        sa.Column("superseded_reason", sa.Text, nullable=True),
        sa.Column("entered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("account_id", "external_id", name="ux_tej_flows_external"),
    )

    op.create_table(
        "tej_playbook_setups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tag", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "tej_trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_accounts.id"), nullable=False),
        sa.Column("setup_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_playbook_setups.id"), nullable=True),
        sa.Column("instrument", sa.String(40), nullable=False),
        sa.Column("direction", direction, nullable=False),
        sa.Column("entry_price", NUMERIC_MONEY, nullable=False),
        sa.Column("exit_price", NUMERIC_MONEY, nullable=True),
        sa.Column("initial_stop", NUMERIC_MONEY, nullable=True),
        sa.Column("target_price", NUMERIC_MONEY, nullable=True),
        sa.Column("position_size", NUMERIC_MONEY, nullable=False),
        sa.Column("risk_amount", NUMERIC_MONEY, nullable=True),
        sa.Column("gross_pnl", NUMERIC_MONEY, nullable=True),
        sa.Column("costs", NUMERIC_MONEY, nullable=False, server_default="0"),
        sa.Column("session", session_enum, nullable=True),
        sa.Column("htf_aligned", sa.Boolean, nullable=True),
        sa.Column("thesis", sa.Text, nullable=True),
        sa.Column("review", sa.Text, nullable=True),
        sa.Column("execution_grade", exec_grade, nullable=True),
        sa.Column("state_of_mind", mind_state, nullable=True),
        sa.Column("rule_compliant", sa.Boolean, nullable=True),
        sa.Column("breach_note", sa.Text, nullable=True),
        sa.Column("mae_r", sa.Numeric(10, 4), nullable=True),
        sa.Column("mfe_r", sa.Numeric(10, 4), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("one_sentence_takeaway", sa.Text, nullable=True),
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_trades.id"), nullable=True),
        sa.Column("superseded_reason", sa.Text, nullable=True),
        sa.Column("entered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("account_id", "external_id", name="ux_tej_trades_external"),
    )

    op.create_table(
        "tej_journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String(40)), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tej_policy_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("limit_type", limit_type, nullable=False),
        sa.Column("threshold", sa.Numeric(20, 8), nullable=False),
        sa.Column("unit", limit_unit, nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("committed_action", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_tej_policy_current",
        "tej_policy_limits",
        ["limit_type"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
    )

    op.create_table(
        "tej_policy_amendments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("previous_limit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_policy_limits.id"), nullable=True),
        sa.Column("new_limit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_policy_limits.id"), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("is_override_during_drawdown", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(reason) >= 10", name="tej_amendment_reason_min"),
    )

    op.create_table(
        "tej_limit_breaches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("limit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_policy_limits.id"), nullable=False),
        sa.Column("breached_on", sa.Date, nullable=False),
        sa.Column("observed_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("threshold_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("resolved_on", sa.Date, nullable=True),
    )

    op.create_table(
        "tej_policy_document",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("section", policy_section, nullable=False, unique=True),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tej_corrections_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("table_name", sa.String(80), nullable=False),
        sa.Column("row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("superseded_by_row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(reason) >= 10", name="tej_correction_reason_min"),
    )

    op.create_table(
        "tej_metric_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("scope", metric_scope, nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_accounts.id"), nullable=True),
        sa.Column("metrics", postgresql.JSONB, nullable=False),
        sa.Column("ledger_hash", sa.String(64), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("as_of_date", "scope", "account_id", name="ux_tej_metric_daily"),
    )

    op.create_table(
        "tej_broker_reconciliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_accounts.id"), nullable=False),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("broker_equity", NUMERIC_MONEY, nullable=False),
        sa.Column("rebuilt_equity", NUMERIC_MONEY, nullable=False),
        sa.Column("delta", NUMERIC_MONEY, nullable=False),
        sa.Column("status", recon_status, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
    )

    op.create_table(
        "tej_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("starting_capital", NUMERIC_MONEY, nullable=False, server_default="15000"),
        sa.Column("record_start_date", sa.Date, nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("risk_free_rate", sa.Numeric(6, 4), nullable=False, server_default="0.04"),
        sa.Column("trading_days_per_year", sa.Integer, nullable=False, server_default="252"),
        sa.Column("minimum_acceptable_return", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("benchmark_sharpe", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("confidence_level", sa.Numeric(4, 3), nullable=False, server_default="0.95"),
        sa.Column("strategy_variants_tested", sa.Integer, nullable=False, server_default="1"),
        sa.CheckConstraint("id = 1", name="tej_settings_singleton"),
    )

    op.create_table(
        "tej_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("metric_name", sa.String(80), nullable=False, unique=True),
        sa.Column("target_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
    )

    op.create_table(
        "tej_allocator_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Timescale hypertable — no-op if the extension isn't installed, or if the
    # backend/constraints don't support hypertable conversion (e.g. TimescaleDB
    # requires every unique/PK constraint on the table to include the
    # partitioning column; tej_nav_snapshots.id is a standalone PK). Wrapped in
    # a SAVEPOINT so a failure here doesn't roll back the table creations above.
    bind = op.get_bind()
    try:
        with bind.begin_nested():
            op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
            op.execute(
                "SELECT create_hypertable('tej_nav_snapshots', 'as_of_date', "
                "if_not_exists => TRUE, migrate_data => TRUE)"
            )
    except Exception:
        pass


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tej_allocator_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_targets CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_broker_reconciliations CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_metric_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_corrections_ledger CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_policy_document CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_limit_breaches CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_policy_amendments CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_policy_limits CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_journal_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_trades CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_playbook_setups CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_cash_flows CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_nav_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_accounts CASCADE")
    for enum in ("tej_recon_status", "tej_metric_scope", "tej_policy_section",
                 "tej_limit_unit", "tej_limit_type", "tej_mind_state",
                 "tej_exec_grade", "tej_session", "tej_direction",
                 "tej_flow_timing", "tej_flow_type", "tej_account_type"):
        op.execute(f"DROP TYPE IF EXISTS {enum}")
