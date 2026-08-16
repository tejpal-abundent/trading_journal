import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CorrectionLedgerCreate(BaseModel):
    table_name: str = Field(min_length=1, max_length=80)
    row_id: uuid.UUID
    superseded_by_row_id: uuid.UUID
    reason: str = Field(min_length=10)


class CorrectionLedgerRead(BaseModel):
    id: uuid.UUID
    table_name: str
    row_id: uuid.UUID
    superseded_by_row_id: uuid.UUID
    reason: str
    corrected_at: datetime
    model_config = {"from_attributes": True}
