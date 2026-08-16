from __future__ import annotations
from typing import Literal
import pandas as pd

from app.core.trades import profit_factor as _pf

Verdict = Literal["not_enough", "retire", "marginal", "working"]
MIN_N = 20
WORKING_THRESHOLD_R = 0.15


def _verdict(n: int, expectancy: float | None) -> Verdict:
    if n < MIN_N or expectancy is None:
        return "not_enough"
    if expectancy > WORKING_THRESHOLD_R:
        return "working"
    if expectancy > 0:
        return "marginal"
    return "retire"


_COLUMN_MAP = {
    "setup": "setup",
    "asset": "instrument",
    "session": "session",
    "htf": "htf_aligned",
    "dow": "_dow",
}


def grouped_stats(trades: pd.DataFrame, by: Literal["setup", "asset", "session", "htf", "dow"]) -> list[dict]:
    if by == "dow":
        trades = trades.copy()
        trades["_dow"] = pd.to_datetime(trades["closed_at"]).dt.day_name()
    col = _COLUMN_MAP[by]
    if col not in trades.columns:
        return []
    total_positive = trades[trades["r_multiple"] > 0]["r_multiple"].sum() or 0.0
    out: list[dict] = []
    for group_val, sub in trades.groupby(col, dropna=True):
        r = sub["r_multiple"].dropna()
        wins = r[r > 0]
        losses = r[r < 0]
        exp = float(r.mean()) if len(r) else None
        row = {
            "group": str(group_val),
            "trade_count": int(len(r)),
            "win_rate": float(len(wins) / len(r)) if len(r) else None,
            "avg_win_r": float(wins.mean()) if len(wins) else None,
            "avg_loss_r": float(losses.mean()) if len(losses) else None,
            "expectancy_r": exp,
            "total_r": float(r.sum()) if len(r) else None,
            "profit_factor": _pf(sub),
            "share_of_total_profit": (
                float(wins.sum() / total_positive) if total_positive else None
            ),
            "verdict": _verdict(len(r), exp),
        }
        out.append(row)
    out.sort(key=lambda x: -(x["total_r"] or 0))
    return out
