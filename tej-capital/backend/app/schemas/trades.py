import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Direction = Literal["long", "short"]
Session = Literal["asia", "london", "london_ny", "new_york", "late_ny"]
ExecGrade = Literal["A", "B", "C", "D"]
MindState = Literal["calm", "rushed", "frustrated", "overconfident", "tilted"]


class TradeCreate(BaseModel):
    account_id: uuid.UUID
    setup_id: uuid.UUID | None = None
    instrument: str = Field(min_length=1, max_length=40)
    direction: Direction
    entry_price: Decimal
    exit_price: Decimal | None = None
    initial_stop: Decimal | None = None
    target_price: Decimal | None = None
    position_size: Decimal
    risk_amount: Decimal | None = None
    gross_pnl: Decimal | None = None
    costs: Decimal = Decimal("0")
    session: Session | None = None
    htf_aligned: bool | None = None
    thesis: str | None = None
    review: str | None = None
    execution_grade: ExecGrade | None = None
    state_of_mind: MindState | None = None
    rule_compliant: bool | None = None
    breach_note: str | None = None
    mae_r: Decimal | None = None
    mfe_r: Decimal | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    one_sentence_takeaway: str | None = None
    external_id: str | None = Field(default=None, max_length=200)


class TradeUpdate(BaseModel):
    exit_price: Decimal | None = None
    initial_stop: Decimal | None = None
    target_price: Decimal | None = None
    risk_amount: Decimal | None = None
    gross_pnl: Decimal | None = None
    costs: Decimal | None = None
    session: Session | None = None
    htf_aligned: bool | None = None
    thesis: str | None = None
    review: str | None = None
    execution_grade: ExecGrade | None = None
    state_of_mind: MindState | None = None
    rule_compliant: bool | None = None
    breach_note: str | None = None
    mae_r: Decimal | None = None
    mfe_r: Decimal | None = None
    closed_at: datetime | None = None
    one_sentence_takeaway: str | None = None


class TradeRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    setup_id: uuid.UUID | None
    instrument: str
    direction: Direction
    entry_price: Decimal
    exit_price: Decimal | None
    initial_stop: Decimal | None
    target_price: Decimal | None
    position_size: Decimal
    risk_amount: Decimal | None
    gross_pnl: Decimal | None
    costs: Decimal
    session: Session | None
    htf_aligned: bool | None
    thesis: str | None
    review: str | None
    execution_grade: ExecGrade | None
    state_of_mind: MindState | None
    rule_compliant: bool | None
    breach_note: str | None
    mae_r: Decimal | None
    mfe_r: Decimal | None
    opened_at: datetime
    closed_at: datetime | None
    one_sentence_takeaway: str | None
    external_id: str | None
    superseded_by: uuid.UUID | None
    superseded_reason: str | None
    entered_at: datetime
    r_multiple: float | None = None
    model_config = {"from_attributes": True}
