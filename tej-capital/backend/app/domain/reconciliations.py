import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BrokerReconciliation(Base):
    __tablename__ = "tej_broker_reconciliations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tej_accounts.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    broker_equity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    rebuilt_equity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    delta: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("ok", "discrepancy", "unexplained", name="tej_recon_status", create_type=False), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
