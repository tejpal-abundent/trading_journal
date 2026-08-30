import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

HabitCategory = Literal["trading", "personal", "body", "sleep"]


class HabitDefinitionCreate(BaseModel):
    key: str = Field(min_length=1, max_length=60)
    label: str = Field(min_length=1, max_length=120)
    category: HabitCategory
    sort_order: int = 100


class HabitDefinitionUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    sort_order: int | None = None
    is_active: bool | None = None


class HabitDefinitionRead(BaseModel):
    id: uuid.UUID
    key: str
    label: str
    category: HabitCategory
    sort_order: int
    is_active: bool
    model_config = {"from_attributes": True}


class HabitLogRead(BaseModel):
    entry_date: date
    habit_id: uuid.UUID
    status: bool
    updated_at: datetime
    model_config = {"from_attributes": True}


class HabitToggle(BaseModel):
    status: bool


class HabitStat(BaseModel):
    current_streak: int
    longest_streak: int
    completion_pct_this_month: float


class HabitMonthLog(BaseModel):
    days: list[str]
    entries: dict[str, dict[str, bool]]
    definitions: list[HabitDefinitionRead]
    stats: dict[str, HabitStat]
