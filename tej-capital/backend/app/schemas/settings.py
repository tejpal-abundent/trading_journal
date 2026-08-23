import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

# Smaller timeframes have worse signal-to-noise, so the default halves the
# allowed per-trade risk on 1m/5m relative to 15m+. Used both as the
# read-time fallback when tej_settings.risk_by_timeframe is NULL and as the
# fallback threshold for any timeframe missing from a stored override map.
DEFAULT_RISK_BY_TIMEFRAME: dict[str, Decimal] = {
    "1m": Decimal("0.0025"), "5m": Decimal("0.0025"),
    "15m": Decimal("0.005"), "30m": Decimal("0.005"),
    "1h": Decimal("0.005"), "4h": Decimal("0.005"),
    "1d": Decimal("0.005"), "1w": Decimal("0.005"),
}


class SettingsCreate(BaseModel):
    starting_capital: Decimal = Decimal("15000")
    record_start_date: date
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    risk_free_rate: Decimal = Decimal("0.04")
    trading_days_per_year: int = 252
    minimum_acceptable_return: Decimal = Decimal("0")
    benchmark_sharpe: Decimal = Decimal("0")
    confidence_level: Decimal = Decimal("0.95")
    strategy_variants_tested: int = 1
    daily_target_pct: Decimal = Decimal("0.003")
    weekly_target_pct: Decimal = Decimal("0.015")
    monthly_target_pct: Decimal = Decimal("0.0614")
    risk_by_timeframe: dict[str, Decimal] | None = None


class SettingsUpdate(BaseModel):
    starting_capital: Decimal | None = None
    record_start_date: date | None = None
    base_currency: str | None = Field(default=None, min_length=3, max_length=3)
    risk_free_rate: Decimal | None = None
    trading_days_per_year: int | None = None
    minimum_acceptable_return: Decimal | None = None
    benchmark_sharpe: Decimal | None = None
    confidence_level: Decimal | None = None
    strategy_variants_tested: int | None = None
    daily_target_pct: Decimal | None = None
    weekly_target_pct: Decimal | None = None
    monthly_target_pct: Decimal | None = None
    risk_by_timeframe: dict[str, Decimal] | None = None

    @field_validator("risk_by_timeframe", mode="after")
    @classmethod
    def _decimals_to_floats(cls, v):
        # JSONB via asyncpg cannot serialize Decimal — floats are honest here
        # anyway (nobody sets risk to 0.00250001).
        if v is None:
            return None
        return {k: float(val) for k, val in v.items()}


class SettingsRead(BaseModel):
    id: int
    starting_capital: Decimal
    record_start_date: date
    base_currency: str
    risk_free_rate: Decimal
    trading_days_per_year: int
    minimum_acceptable_return: Decimal
    benchmark_sharpe: Decimal
    confidence_level: Decimal
    strategy_variants_tested: int
    daily_target_pct: Decimal
    weekly_target_pct: Decimal
    monthly_target_pct: Decimal
    risk_by_timeframe: dict[str, Decimal]
    model_config = {"from_attributes": True}

    @field_validator("risk_by_timeframe", mode="before")
    @classmethod
    def _default_risk_by_timeframe(cls, v):
        return v if v is not None else DEFAULT_RISK_BY_TIMEFRAME


class TargetCreate(BaseModel):
    metric_name: str = Field(min_length=1, max_length=80)
    target_value: Decimal
    unit: str = Field(min_length=1, max_length=20)


class TargetUpdate(BaseModel):
    target_value: Decimal | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=20)


class TargetRead(BaseModel):
    id: uuid.UUID
    metric_name: str
    target_value: Decimal
    unit: str
    model_config = {"from_attributes": True}
