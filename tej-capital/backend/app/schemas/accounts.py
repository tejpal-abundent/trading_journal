import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

AccountType = Literal["live", "prop_funded", "prop_evaluation", "demo", "verified_mirror"]


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    broker: str = Field(min_length=1, max_length=120)
    currency: str = Field(min_length=3, max_length=3)
    account_type: AccountType
    in_composite: bool = True
    exclusion_reason: str | None = None

    @model_validator(mode="after")
    def _exclusion_reason_required_when_excluded(self):
        if not self.in_composite:
            if not self.exclusion_reason or len(self.exclusion_reason.strip()) < 10:
                raise ValueError("exclusion_reason must be at least 10 characters when in_composite is false")
        return self


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    broker: str | None = Field(default=None, min_length=1, max_length=120)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    account_type: AccountType | None = None
    in_composite: bool | None = None
    exclusion_reason: str | None = None
    archived_at: datetime | None = None


class AccountRead(BaseModel):
    id: uuid.UUID
    name: str
    broker: str
    currency: str
    account_type: AccountType
    in_composite: bool
    exclusion_reason: str | None
    created_at: datetime
    archived_at: datetime | None
    model_config = {"from_attributes": True}
