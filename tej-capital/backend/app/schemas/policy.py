import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

LimitType = Literal[
    "risk_per_trade", "concurrent_open_risk", "daily_loss", "weekly_loss", "monthly_loss",
    "drawdown_killswitch", "asset_class_concentration", "risk_sizing_consistency",
    "avg_loser_vs_1r", "rule_compliance_rate",
]
LimitUnit = Literal["pct", "r", "abs"]
PolicySection = Literal[
    "mandate", "method", "time_horizon", "position_sizing", "correlation",
    "stop_discipline", "news_policy", "leverage", "valuation", "custody",
    "amendment_procedure", "review_cadence",
]


class PolicyLimitCreate(BaseModel):
    limit_type: LimitType
    threshold: Decimal
    unit: LimitUnit
    effective_from: date
    effective_to: date | None = None
    committed_action: str = Field(min_length=1)


class PolicyLimitRead(BaseModel):
    id: uuid.UUID
    limit_type: LimitType
    threshold: Decimal
    unit: LimitUnit
    effective_from: date
    effective_to: date | None
    committed_action: str
    created_at: datetime
    model_config = {"from_attributes": True}


class PolicyAmendmentCreate(BaseModel):
    previous_limit_id: uuid.UUID | None = None
    new_limit_id: uuid.UUID
    reason: str = Field(min_length=10)
    is_override_during_drawdown: bool = False


class PolicyAmendmentRead(BaseModel):
    id: uuid.UUID
    previous_limit_id: uuid.UUID | None
    new_limit_id: uuid.UUID
    reason: str
    is_override_during_drawdown: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class LimitBreachCreate(BaseModel):
    limit_id: uuid.UUID
    breached_on: date
    observed_value: Decimal
    threshold_value: Decimal
    note: str | None = None
    resolved_on: date | None = None


class LimitBreachRead(BaseModel):
    id: uuid.UUID
    limit_id: uuid.UUID
    breached_on: date
    observed_value: Decimal
    threshold_value: Decimal
    note: str | None
    resolved_on: date | None
    model_config = {"from_attributes": True}


class PolicyDocumentCreate(BaseModel):
    section: PolicySection
    body: str = ""


class PolicyDocumentUpdate(BaseModel):
    body: str


class PolicyDocumentRead(BaseModel):
    id: uuid.UUID
    section: PolicySection
    body: str
    updated_at: datetime
    model_config = {"from_attributes": True}
