import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

FlowType = Literal[
    "deposit", "withdrawal", "prop_payout", "platform_fee", "transfer_in", "transfer_out"
]
FlowTiming = Literal["start_of_day", "end_of_day"]


class CashFlowCreate(BaseModel):
    account_id: uuid.UUID
    as_of_date: date
    amount: Decimal
    flow_type: FlowType
    flow_timing: FlowTiming = "end_of_day"
    note: str | None = None
    external_id: str | None = Field(default=None, max_length=200)


class CashFlowRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    as_of_date: date
    amount: Decimal
    flow_type: FlowType
    flow_timing: FlowTiming
    note: str | None
    external_id: str | None
    superseded_by: uuid.UUID | None
    superseded_reason: str | None
    entered_at: datetime
    model_config = {"from_attributes": True}
