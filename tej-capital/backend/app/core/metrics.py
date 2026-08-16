"""Metric primitives. Pure functions. No I/O.

Every metric returns None when the input is empty (R3 — never zero).
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _empty(r: pd.Series) -> bool:
    return r is None or len(r) == 0


def cumulative_twr(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float((1.0 + returns).prod() - 1.0)


def cagr(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    total = (1.0 + returns).prod()
    years = len(returns) / trading_days_per_year
    if years <= 0:
        return None
    return float(total ** (1.0 / years) - 1.0)


def annualised_return(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    return float(returns.mean() * trading_days_per_year)


def avg_daily_return(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float(returns.mean())


def pct_positive_days(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float((returns > 0).sum() / len(returns))


def avg_up_day(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    ups = returns[returns > 0]
    return float(ups.mean()) if len(ups) else None


def avg_down_day(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    downs = returns[returns < 0]
    return float(downs.mean()) if len(downs) else None


def best_day(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float(returns.max())


def worst_day(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float(returns.min())
