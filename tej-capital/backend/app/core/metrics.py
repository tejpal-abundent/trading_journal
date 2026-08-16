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


# --- Risk block ---

def annualised_volatility(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    return float(returns.std(ddof=1) * np.sqrt(trading_days_per_year)) if len(returns) > 1 else 0.0


def downside_deviation(returns: pd.Series, mar: float = 0.0,
                       trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    downside = np.minimum(returns - mar, 0.0)
    dd = np.sqrt((downside ** 2).mean())
    return float(dd * np.sqrt(trading_days_per_year))


def _equity_curve(returns: pd.Series) -> pd.Series:
    return (1.0 + returns).cumprod()


def max_drawdown(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    eq = _equity_curve(returns)
    running_peak = eq.cummax()
    dd = eq / running_peak - 1.0
    return float(dd.min())


def current_drawdown(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    eq = _equity_curve(returns)
    return float(eq.iloc[-1] / eq.cummax().iloc[-1] - 1.0)


def longest_drawdown_days(returns: pd.Series) -> int | None:
    if _empty(returns):
        return None
    eq = _equity_curve(returns)
    peak = eq.cummax()
    underwater = eq < peak
    longest, current = 0, 0
    for flag in underwater:
        if flag:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return int(longest)


def current_days_under_water(returns: pd.Series) -> int | None:
    if _empty(returns):
        return None
    eq = _equity_curve(returns)
    peak = eq.cummax()
    underwater = (eq < peak).astype(int)
    count = 0
    for flag in reversed(underwater.tolist()):
        if flag:
            count += 1
        else:
            break
    return int(count)


def ulcer_index(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    eq = _equity_curve(returns)
    dd = (eq / eq.cummax() - 1.0) * 100.0
    return float(np.sqrt((dd ** 2).mean()))


def var_95(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float(np.percentile(returns, 5))


def cvar_95(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    v = np.percentile(returns, 5)
    tail = returns[returns <= v]
    return float(tail.mean()) if len(tail) else float(v)


def skewness(returns: pd.Series) -> float | None:
    if _empty(returns) or len(returns) < 3:
        return None
    return float(returns.skew())


def excess_kurtosis(returns: pd.Series) -> float | None:
    if _empty(returns) or len(returns) < 4:
        return None
    return float(returns.kurtosis())  # pandas returns excess by default


def top_n_drawdowns(returns: pd.Series, n: int = 5) -> list[dict]:
    if _empty(returns):
        return []
    eq = _equity_curve(returns)
    peak = eq.cummax()
    dd = eq / peak - 1.0

    drawdowns: list[dict] = []
    in_dd = False
    peak_date = None
    trough_date = None
    trough_val = 0.0
    for d, v in dd.items():
        if not in_dd and v < 0:
            in_dd = True
            peak_date = d
            trough_date = d
            trough_val = v
        elif in_dd:
            if v < trough_val:
                trough_val = v
                trough_date = d
            if v >= 0:
                drawdowns.append({
                    "depth": float(trough_val),
                    "duration_days": (d - peak_date).days,
                    "peak_date": peak_date,
                    "trough_date": trough_date,
                    "recovery_date": d,
                })
                in_dd = False
                trough_val = 0.0
    if in_dd:
        drawdowns.append({
            "depth": float(trough_val),
            "duration_days": (dd.index[-1] - peak_date).days,
            "peak_date": peak_date,
            "trough_date": trough_date,
            "recovery_date": None,
        })
    drawdowns.sort(key=lambda d: d["depth"])
    return drawdowns[:n]


# --- Risk-adjusted block ---

def sharpe(returns: pd.Series, rf: float = 0.0, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns) or len(returns) < 2:
        return None
    excess = returns - rf / trading_days_per_year
    std = excess.std(ddof=1)
    if std == 0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(trading_days_per_year))


def sortino(returns: pd.Series, mar: float = 0.0, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns) or len(returns) < 2:
        return None
    excess = returns - mar / trading_days_per_year
    dd = downside_deviation(returns, mar=mar, trading_days_per_year=trading_days_per_year)
    if dd is None or dd == 0:
        return None
    return float(excess.mean() * trading_days_per_year / dd)


def calmar(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    mdd = max_drawdown(returns)
    if mdd is None or mdd == 0:
        return None
    c = cagr(returns, trading_days_per_year)
    if c is None:
        return None
    return float(c / abs(mdd))


def sterling(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    """Annualised return / (avg of top-3 drawdowns - 10%)."""
    if _empty(returns):
        return None
    dds = [d["depth"] for d in top_n_drawdowns(returns, n=3)]
    if not dds:
        return None
    avg_dd = np.mean(dds)
    denom = abs(avg_dd) - 0.10
    if denom <= 0:
        return None
    ar = annualised_return(returns, trading_days_per_year)
    return float(ar / denom) if ar is not None else None


def burke(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    """Annualised return / sqrt(sum of squared drawdowns)."""
    if _empty(returns):
        return None
    dds = [d["depth"] for d in top_n_drawdowns(returns, n=10)]
    if not dds:
        return None
    denom = np.sqrt(sum(d ** 2 for d in dds))
    if denom == 0:
        return None
    ar = annualised_return(returns, trading_days_per_year)
    return float(ar / denom) if ar is not None else None


def omega(returns: pd.Series, threshold: float = 0.0) -> float | None:
    if _empty(returns):
        return None
    gains = (returns - threshold).clip(lower=0).sum()
    losses = -(returns - threshold).clip(upper=0).sum()
    if losses == 0:
        return None
    return float(gains / losses)


def gain_to_pain(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    gains = returns.sum()
    pain = -returns[returns < 0].sum()
    if pain == 0:
        return None
    return float(gains / pain)


def tail_ratio(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    right = np.percentile(returns, 95)
    left = np.percentile(returns, 5)
    if left == 0:
        return None
    return float(right / abs(left))


def ulcer_performance_index(returns: pd.Series, rf: float = 0.0,
                            trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    ar = annualised_return(returns, trading_days_per_year)
    u = ulcer_index(returns)
    if u is None or u == 0 or ar is None:
        return None
    return float((ar - rf) / u)


def recovery_factor(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    cum = cumulative_twr(returns)
    mdd = max_drawdown(returns)
    if cum is None or mdd is None or mdd == 0:
        return None
    return float(cum / abs(mdd))
