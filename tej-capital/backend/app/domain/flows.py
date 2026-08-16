import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CashFlow(Base):
    __tablename__ = "tej_cash_flows"
    __table_args__ = (
        # Partial: see Trade.__table_args__ for the correction-carries-
        # external_id-forward rationale — migration 0002.
        Index(
            "ux_tej_flows_external", "account_id", "external_id",
            unique=True, postgresql_where=text("superseded_by IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tej_accounts.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    flow_type: Mapped[str] = mapped_column(
        Enum(
            "deposit", "withdrawal", "prop_payout", "platform_fee",
            "transfer_in", "transfer_out", name="tej_flow_type", create_type=False,
        ),
        nullable=False,
    )
    flow_timing: Mapped[str] = mapped_column(
        Enum("start_of_day", "end_of_day", name="tej_flow_timing", create_type=False),
        nullable=False,
        default="end_of_day",
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tej_cash_flows.id"), nullable=True
    )
    superseded_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
