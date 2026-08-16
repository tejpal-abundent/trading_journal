import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MetricSnapshot(Base):
    __tablename__ = "tej_metric_snapshots"
    __table_args__ = (
        UniqueConstraint("as_of_date", "scope", "account_id", name="ux_tej_metric_daily"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    scope: Mapped[str] = mapped_column(
        Enum("composite", "per_account", name="tej_metric_scope", create_type=False), nullable=False
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tej_accounts.id"), nullable=True
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ledger_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
