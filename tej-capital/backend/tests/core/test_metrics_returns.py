import pandas as pd
import numpy as np
import pytest
from app.core.metrics import (
    cumulative_twr, cagr, annualised_return, avg_daily_return,
    pct_positive_days, avg_up_day, avg_down_day, best_day, worst_day,
)


def test_returns_metrics_all_none_when_empty_R3():
    empty = pd.Series(dtype="float64")
    assert cumulative_twr(empty) is None
    assert cagr(empty) is None
    assert annualised_return(empty) is None
    assert avg_daily_return(empty) is None
    assert pct_positive_days(empty) is None


def test_cumulative_twr_geometric():
    r = pd.Series([0.01, 0.01, -0.01])
    # (1.01 * 1.01 * 0.99) - 1 = 0.009899
    assert cumulative_twr(r) == pytest.approx(0.009899, abs=1e-6)


def test_pct_positive_days():
    r = pd.Series([0.01, -0.01, 0.02, 0.0, 0.005])
    # 3 up (0.01, 0.02, 0.005), 2 non-up (0, -0.01) — flat is not up
    assert pct_positive_days(r) == pytest.approx(3/5)


def test_best_and_worst_day():
    r = pd.Series([0.03, -0.02, 0.01])
    assert best_day(r) == pytest.approx(0.03)
    assert worst_day(r) == pytest.approx(-0.02)


def test_cagr_matches_hand_computed():
    # 252 daily returns of +0.001 → (1.001)^252 - 1 ≈ 0.286434
    r = pd.Series([0.001] * 252)
    assert cagr(r, trading_days_per_year=252) == pytest.approx(0.286434, abs=1e-5)
