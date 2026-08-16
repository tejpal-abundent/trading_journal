"""Return calculations. Pure functions. No I/O.

R2: a cash flow is never treated as profit.
R3: days without a mark are absent from the index — never zero-padded.
"""
from __future__ import annotations
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal
import pandas as pd

FlowTiming = Literal["start_of_day", "end_of_day"]


def daily_twr(nav: pd.Series, flows: pd.Series, timing: FlowTiming = "end_of_day") -> pd.Series:
    if len(nav) < 2:
        return pd.Series(dtype="float64")
    nav = nav.sort_index().astype("float64")
    flows = flows.reindex(nav.index, fill_value=0.0).astype("float64") if len(flows) else pd.Series(0.0, index=nav.index)

    prev = nav.shift(1)
    if timing == "end_of_day":
        # Deposit lands at close — remove it from today's numerator.
        numerator = nav - flows - prev
        denom = prev
    else:  # start_of_day
        # Deposit lands at open — include it in the base capital.
        numerator = nav - prev - flows
        denom = prev + flows

    ret = numerator / denom
    return ret.dropna()


def composite_twr(accounts: dict[uuid.UUID, tuple[pd.Series, pd.Series]]) -> pd.Series:
    """Beginning-of-day weighted composite return."""
    per_account = {}
    weights = {}
    for aid, (nav, flows) in accounts.items():
        r = daily_twr(nav, flows)
        per_account[aid] = r
        weights[aid] = nav.shift(1).reindex(r.index)

    all_dates = sorted(set().union(*(r.index for r in per_account.values())))
    out = {}
    for d in all_dates:
        num, denom = 0.0, 0.0
        for aid, r in per_account.items():
            if d in r.index and d in weights[aid].index and not pd.isna(weights[aid].loc[d]):
                w = float(weights[aid].loc[d])
                num += w * float(r.loc[d])
                denom += w
        if denom > 0:
            out[d] = num / denom
    return pd.Series(out).sort_index()


def reconcile(broker_equity: pd.Series, rebuilt_equity: pd.Series,
              tolerance: Decimal = Decimal("0.01")) -> list[dict]:
    rows = []
    idx = broker_equity.index.intersection(rebuilt_equity.index)
    tol = float(tolerance)
    for d in idx:
        b = float(broker_equity.loc[d])
        r = float(rebuilt_equity.loc[d])
        delta = b - r
        status = "ok" if abs(delta) <= tol else "discrepancy"
        rows.append({"date": d, "broker_equity": b, "rebuilt_equity": r,
                     "delta": delta, "status": status})
    return rows


def detect_anomalies(nav: pd.Series, flows: pd.Series, daily_limit_pct: float = 0.02) -> list[dict]:
    anomalies: list[dict] = []
    if len(nav) < 2:
        return anomalies
    nav = nav.sort_index().astype("float64")
    flows = flows.reindex(nav.index, fill_value=0.0) if len(flows) else pd.Series(0.0, index=nav.index)
    prev = nav.shift(1)
    daily_ret = (nav - flows - prev) / prev
    for d, r in daily_ret.dropna().items():
        if abs(r) > 3 * daily_limit_pct:
            anomalies.append({"date": d, "kind": "return_exceeds_3x_limit", "value": float(r)})
        if abs(flows.loc[d]) > 0 and abs(r) > daily_limit_pct:
            anomalies.append({"date": d, "kind": "deposit_and_large_return_same_day",
                              "flow": float(flows.loc[d]), "return": float(r)})
    return anomalies
