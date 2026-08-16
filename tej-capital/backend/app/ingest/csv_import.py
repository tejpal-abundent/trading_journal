from datetime import date
from decimal import Decimal
import pandas as pd
from app.ingest.base import BrokerAdapter, CanonicalTrade, CanonicalFlow


class CsvAdapter(BrokerAdapter):
    """BrokerAdapter implementation backed by a broker-exported CSV file.

    ``mapping`` translates our canonical field names to the column names
    used by the broker's export, e.g.
    ``{"external_id": "OrderID", "instrument": "Symbol", ...}``. Only
    ``external_id``, ``instrument``, ``direction``, ``entry_price``,
    ``position_size`` and ``opened_at`` are required; the rest are
    optional and fall back to ``None`` (economic fields the enrichment
    queue will fill in later — Rule R7).
    """

    name = "csv"

    def __init__(self, csv_bytes: bytes, mapping: dict):
        self.df = pd.read_csv(pd.io.common.BytesIO(csv_bytes))
        self.map = mapping  # {"external_id": "OrderID", "instrument": "Symbol", ...}

    def fetch_equity(self, since: date) -> pd.Series:
        # CSV imports typically don't provide equity — return empty.
        return pd.Series(dtype="float64")

    def fetch_closed_trades(self, since: date) -> list[CanonicalTrade]:
        m = self.map
        out = []
        for _, row in self.df.iterrows():
            opened = pd.to_datetime(row[m["opened_at"]])
            if opened.date() < since:
                continue
            out.append(CanonicalTrade(
                external_id=str(row[m["external_id"]]),
                instrument=str(row[m["instrument"]]),
                direction=str(row[m["direction"]]).lower(),
                entry_price=Decimal(str(row[m["entry_price"]])),
                exit_price=Decimal(str(row[m["exit_price"]])) if m.get("exit_price") else None,
                position_size=Decimal(str(row[m["position_size"]])),
                gross_pnl=Decimal(str(row[m["gross_pnl"]])) if m.get("gross_pnl") else None,
                costs=Decimal(str(row.get(m.get("costs", ""), 0))),
                opened_at=str(opened),
                closed_at=str(pd.to_datetime(row[m["closed_at"]])) if m.get("closed_at") else None,
            ))
        return out

    def fetch_flows(self, since: date) -> list[CanonicalFlow]:
        m = self.map
        if not m.get("flow_external_id"):
            # No flow columns mapped — this CSV export is trades-only.
            return []
        out = []
        for _, row in self.df.iterrows():
            as_of = pd.to_datetime(row[m["flow_as_of_date"]]).date()
            if as_of < since:
                continue
            out.append(CanonicalFlow(
                external_id=str(row[m["flow_external_id"]]),
                as_of_date=as_of,
                amount=Decimal(str(row[m["flow_amount"]])),
                flow_type=str(row[m["flow_type"]]).lower(),
            ))
        return out
