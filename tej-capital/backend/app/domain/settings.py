import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Settings(Base):
    __tablename__ = "tej_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="tej_settings_singleton"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    starting_capital: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=Decimal("15000"))
    record_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    risk_free_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0.04"))
    trading_days_per_year: Mapped[int] = mapped_column(Integer, nullable=False, default=252)
    minimum_acceptable_return: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0"))
    benchmark_sharpe: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0"))
    confidence_level: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=Decimal("0.95"))
    strategy_variants_tested: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    daily_target_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0.003"))
    weekly_target_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0.015"))
    monthly_target_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0.0614"))


class Target(Base):
    __tablename__ = "tej_targets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    target_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
