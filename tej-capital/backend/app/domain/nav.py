import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class NavSnapshot(Base):
    __tablename__ = "tej_nav_snapshots"
    __table_args__ = (
        CheckConstraint("closing_equity >= 0", name="tej_nav_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tej_accounts.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    closing_equity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tej_nav_snapshots.id"), nullable=True
    )
    superseded_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
