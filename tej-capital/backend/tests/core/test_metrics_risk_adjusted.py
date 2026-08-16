import numpy as np
import pandas as pd
import pytest
from app.core.metrics import (
    sharpe, sortino, calmar, sterling, burke, omega,
    gain_to_pain, tail_ratio, ulcer_performance_index, recovery_factor,
)


def test_all_none_when_empty():
    e = pd.Series(dtype="float64")
    for fn in (sharpe, sortino, calmar, sterling, burke, omega,
               gain_to_pain, tail_ratio, ulcer_performance_index, recovery_factor):
        assert fn(e) is None


def test_sharpe_zero_when_no_excess():
    r = pd.Series([0.0] * 252)
    assert sharpe(r) == 0.0 or sharpe(r) is None  # zero excess and zero vol → either is acceptable


def test_sharpe_known_series():
    # mean 0.001, std ~ 0.01 → Sharpe ≈ (0.001/0.01)*sqrt(252) ≈ 1.587
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.001, 0.01, size=5000))
    s = sharpe(r)
    assert 1.4 < s < 1.75


def test_sortino_greater_than_sharpe_when_upside_dominates():
    r = pd.Series([0.02] * 50 + [-0.005] * 10)
    assert sortino(r) > sharpe(r)


def test_omega_greater_than_one_when_gains_exceed_losses():
    r = pd.Series([0.01, 0.02, -0.005, 0.015, -0.003])
    assert omega(r) > 1.0


def test_tail_ratio_ordering():
    r = pd.Series([0.05] * 5 + [-0.01] * 5)
    # Right tail (0.05) / left tail (0.01) = 5
    assert tail_ratio(r) == pytest.approx(5.0, abs=0.2)
