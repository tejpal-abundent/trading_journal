"""Plain-English verdict band. Templates from Product Brief §4.4."""
from __future__ import annotations
from typing import Literal
import pandas as pd

from app.core.metrics import sharpe
from app.core.stats import min_trl


NOT_YET_TEMPLATE = (
    "At your observed consistency you need roughly {days_needed} days of data before "
    "\"my Sharpe beats {threshold}\" survives scrutiny. You have {n_days}. "
    "That's about {years_remaining:.1f} more years. Do not raise capital on these numbers."
)

OK_TEMPLATE = (
    "Your realised Sharpe of {sharpe:.2f} beats the {threshold:.2f} threshold with "
    "sufficient sample size ({n_days} days). The claim survives standard scrutiny."
)


def verdict_band(returns: pd.Series, benchmark_sharpe: float,
                 trading_days_per_year: int = 252) -> dict:
    n_days = len(returns) if returns is not None else 0
    if n_days < 30:
        return {
            "headline": "Not yet meaningful",
            "detail": f"You have {n_days} days of data. Statistics kick in around 30 days.",
            "level": "not_yet_meaningful",
            "n_days": n_days,
            "days_needed": None,
            "years_remaining": None,
        }
    days_needed = min_trl(returns, benchmark_sharpe=benchmark_sharpe, confidence=0.95)
    s = sharpe(returns)
    if days_needed is None or s is None:
        return {
            "headline": "Insufficient signal",
            "detail": "Your Sharpe is too close to the benchmark to test.",
            "level": "caution",
            "n_days": n_days,
            "days_needed": None,
            "years_remaining": None,
        }
    if n_days >= days_needed:
        return {
            "headline": "Statistically meaningful",
            "detail": OK_TEMPLATE.format(sharpe=s, threshold=benchmark_sharpe, n_days=n_days),
            "level": "ok",
            "n_days": n_days,
            "days_needed": days_needed,
            "years_remaining": 0.0,
        }
    remaining = (days_needed - n_days) / trading_days_per_year
    return {
        "headline": "Not yet meaningful",
        "detail": NOT_YET_TEMPLATE.format(
            days_needed=days_needed, threshold=benchmark_sharpe,
            n_days=n_days, years_remaining=remaining,
        ),
        "level": "not_yet_meaningful",
        "n_days": n_days,
        "days_needed": days_needed,
        "years_remaining": remaining,
    }
