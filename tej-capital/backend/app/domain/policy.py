import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PolicyLimit(Base):
    __tablename__ = "tej_policy_limits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    limit_type: Mapped[str] = mapped_column(
        Enum(
            "risk_per_trade", "concurrent_open_risk", "daily_loss", "weekly_loss", "monthly_loss",
            "drawdown_killswitch", "asset_class_concentration", "risk_sizing_consistency",
            "avg_loser_vs_1r", "rule_compliance_rate", name="tej_limit_type", create_type=False,
        ),
        nullable=False,
    )
    threshold: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unit: Mapped[str] = mapped_column(
        Enum("pct", "r", "abs", name="tej_limit_unit", create_type=False), nullable=False
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    committed_action: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PolicyAmendment(Base):
    __tablename__ = "tej_policy_amendments"
    __table_args__ = (
        CheckConstraint("char_length(reason) >= 10", name="tej_amendment_reason_min"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    previous_limit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tej_policy_limits.id"), nullable=True
    )
    new_limit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tej_policy_limits.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    is_override_during_drawdown: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LimitBreach(Base):
    __tablename__ = "tej_limit_breaches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    limit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tej_policy_limits.id"), nullable=False
    )
    breached_on: Mapped[date] = mapped_column(Date, nullable=False)
    observed_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class PolicyDocument(Base):
    __tablename__ = "tej_policy_document"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section: Mapped[str] = mapped_column(
        Enum(
            "mandate", "method", "time_horizon", "position_sizing", "correlation",
            "stop_discipline", "news_policy", "leverage", "valuation", "custody",
            "amendment_procedure", "review_cadence", name="tej_policy_section", create_type=False,
        ),
        nullable=False,
        unique=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
