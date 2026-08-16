from typing import Protocol
from datetime import date
from decimal import Decimal
from dataclasses import dataclass
import pandas as pd


@dataclass
class CanonicalTrade:
    external_id: str
    instrument: str
    direction: str
    entry_price: Decimal
    exit_price: Decimal | None
    position_size: Decimal
    gross_pnl: Decimal | None
    costs: Decimal
    opened_at: str
    closed_at: str | None


@dataclass
class CanonicalFlow:
    external_id: str
    as_of_date: date
    amount: Decimal
    flow_type: str


class BrokerAdapter(Protocol):
    name: str
    def fetch_equity(self, since: date) -> pd.Series: ...
    def fetch_closed_trades(self, since: date) -> list[CanonicalTrade]: ...
    def fetch_flows(self, since: date) -> list[CanonicalFlow]: ...
