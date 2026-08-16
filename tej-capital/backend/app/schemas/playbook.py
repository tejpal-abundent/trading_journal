import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PlaybookSetupCreate(BaseModel):
    tag: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    is_active: bool = True


class PlaybookSetupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    is_active: bool | None = None
    retired_at: datetime | None = None


class PlaybookSetupRead(BaseModel):
    id: uuid.UUID
    tag: str
    name: str
    description: str
    is_active: bool
    retired_at: datetime | None
    model_config = {"from_attributes": True}
