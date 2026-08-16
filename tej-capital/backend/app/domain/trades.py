import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Trade(Base):
    __tablename__ = "tej_trades"
    __table_args__ = (
        UniqueConstraint("account_id", "external_id", name="ux_tej_trades_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tej_accounts.id"), nullable=False)
    setup_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tej_playbook_setups.id"), nullable=True
    )
    instrument: Mapped[str] = mapped_column(String(40), nullable=False)
    direction: Mapped[str] = mapped_column(
        Enum("long", "short", name="tej_direction", create_type=False), nullable=False
    )
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    initial_stop: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    position_size: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    risk_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    gross_pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    costs: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    session: Mapped[str | None] = mapped_column(
        Enum(
            "asia", "london", "london_ny", "new_york", "late_ny",
            name="tej_session", create_type=False,
        ),
        nullable=True,
    )
    htf_aligned: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    review: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_grade: Mapped[str | None] = mapped_column(
        Enum("A", "B", "C", "D", name="tej_exec_grade", create_type=False), nullable=True
    )
    state_of_mind: Mapped[str | None] = mapped_column(
        Enum(
            "calm", "rushed", "frustrated", "overconfident", "tilted",
            name="tej_mind_state", create_type=False,
        ),
        nullable=True,
    )
    rule_compliant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    breach_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    mae_r: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    mfe_r: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    one_sentence_takeaway: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tej_trades.id"), nullable=True
    )
    superseded_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def r_multiple(self) -> float | None:
        if self.risk_amount is None or self.risk_amount == 0:
            return None
        pnl = (self.gross_pnl or 0) - (self.costs or 0)
        return float(pnl) / float(self.risk_amount)
