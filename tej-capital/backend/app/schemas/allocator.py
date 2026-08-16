import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AllocatorTokenCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    expires_at: datetime


class AllocatorTokenRead(BaseModel):
    id: uuid.UUID
    token: str
    label: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}
