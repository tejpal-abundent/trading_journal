import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class NavSnapshotCreate(BaseModel):
    account_id: uuid.UUID
    as_of_date: date
    closing_equity: Decimal = Field(ge=0)
    superseded_reason: str | None = None


class NavSnapshotRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    as_of_date: date
    closing_equity: Decimal
    superseded_by: uuid.UUID | None
    superseded_reason: str | None
    entered_at: datetime
    model_config = {"from_attributes": True}
