import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

MetricScope = Literal["composite", "per_account"]


class MetricSnapshotCreate(BaseModel):
    as_of_date: date
    scope: MetricScope
    account_id: uuid.UUID | None = None
    metrics: dict[str, Any]
    ledger_hash: str


class MetricSnapshotRead(BaseModel):
    id: uuid.UUID
    as_of_date: date
    scope: MetricScope
    account_id: uuid.UUID | None
    metrics: dict[str, Any]
    ledger_hash: str
    computed_at: datetime
    model_config = {"from_attributes": True}
