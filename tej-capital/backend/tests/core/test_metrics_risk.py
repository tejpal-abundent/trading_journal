import numpy as np
import pandas as pd
import pytest
from datetime import date, timedelta

from app.core.metrics import (
    annualised_volatility, downside_deviation, max_drawdown, current_drawdown,
    longest_drawdown_days, current_days_under_water, ulcer_index,
    var_95, cvar_95, skewness, excess_kurtosis, top_n_drawdowns,
)


def _idx(n):
    return pd.date_range("2026-01-01", periods=n, freq="D")


def test_all_risk_metrics_none_when_empty_R3():
    e = pd.Series(dtype="float64")
    assert annualised_volatility(e) is None
    assert max_drawdown(e) is None
    assert var_95(e) is None
    assert skewness(e) is None


def test_annualised_vol_from_known_std():
    # Constant 0.01 daily has 0 std → vol 0
    r = pd.Series([0.01] * 100, index=_idx(100))
    assert annualised_volatility(r) == pytest.approx(0.0, abs=1e-9)


def test_max_drawdown_hand_computed():
    # Cumulative: 1.0, 1.10, 1.00, 0.90, 0.99, 1.08
    r = pd.Series([0.10, -1/11, -0.10, 0.10, 1/11 * 0.99], index=_idx(5))
    mdd = max_drawdown(r)
    # Peak 1.10 → trough 0.90 → DD = -0.1818
    assert mdd == pytest.approx(-0.18181818, abs=1e-4)


def test_current_dd_zero_at_new_high():
    r = pd.Series([0.01, 0.01, 0.01], index=_idx(3))
    assert current_drawdown(r) == pytest.approx(0.0, abs=1e-9)


def test_longest_dd_days_counts_correctly():
    # Up, down, down, down, up-past-peak
    r = pd.Series([0.10, -0.05, -0.02, -0.01, 0.20], index=_idx(5))
    # Underwater from day 2 to day 5 (recovery on day 5) → 3 days
    assert longest_drawdown_days(r) == 3


def test_var_and_cvar_95_ordering():
    rng = np.random.default_rng(42)
    r = pd.Series(rng.normal(0.0005, 0.01, size=1000), index=_idx(1000))
    v = var_95(r)
    c = cvar_95(r)
    assert v < 0 and c < 0
    assert c <= v  # CVaR is at least as negative as VaR


def test_skewness_negative_for_left_skewed():
    # Bunch of small ups, one big down
    r = pd.Series([0.001] * 99 + [-0.20], index=_idx(100))
    assert skewness(r) < -0.5


def test_top_n_drawdowns_returns_sorted_by_depth():
    # Design a series with two clear drawdowns
    r = pd.Series([0.10, -0.05, 0.10, -0.10, 0.15, -0.02, 0.05], index=_idx(7))
    dds = top_n_drawdowns(r, n=3)
    depths = [d["depth"] for d in dds]
    assert depths == sorted(depths)  # deepest (most negative) first
    assert all("duration_days" in d for d in dds)
