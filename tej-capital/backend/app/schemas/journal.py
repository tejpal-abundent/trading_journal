import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class JournalEntryCreate(BaseModel):
    entry_date: date
    body: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class JournalEntryUpdate(BaseModel):
    body: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None


class JournalEntryRead(BaseModel):
    id: uuid.UUID
    entry_date: date
    body: str
    tags: list[str]
    created_at: datetime
    model_config = {"from_attributes": True}
