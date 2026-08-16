import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

ReconStatus = Literal["ok", "discrepancy", "unexplained"]


class BrokerReconciliationCreate(BaseModel):
    account_id: uuid.UUID
    as_of_date: date
    broker_equity: Decimal
    rebuilt_equity: Decimal
    delta: Decimal
    status: ReconStatus
    note: str | None = None


class BrokerReconciliationRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    as_of_date: date
    broker_equity: Decimal
    rebuilt_equity: Decimal
    delta: Decimal
    status: ReconStatus
    note: str | None
    model_config = {"from_attributes": True}
