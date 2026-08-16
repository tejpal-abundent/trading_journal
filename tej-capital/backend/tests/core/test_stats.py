import numpy as np
import pandas as pd
import pytest
from app.core.stats import (
    sharpe_t_stat, probabilistic_sharpe_ratio, min_trl, deflated_sharpe, sharpe_ci,
)


def _r(n, seed=0, mu=0.001, sigma=0.01):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mu, sigma, size=n))


def test_all_none_when_short_sample():
    r = pd.Series([0.01] * 10)
    assert sharpe_t_stat(r) is None
    assert probabilistic_sharpe_ratio(r) is None
    assert deflated_sharpe(r, trials_tested=1) is None


def test_psr_monotone_in_sample_size():
    small = probabilistic_sharpe_ratio(_r(60, seed=1), benchmark_sharpe=0.0)
    large = probabilistic_sharpe_ratio(_r(2000, seed=1), benchmark_sharpe=0.0)
    assert large > small


def test_psr_bounded_zero_one():
    p = probabilistic_sharpe_ratio(_r(500), benchmark_sharpe=0.0)
    assert 0.0 <= p <= 1.0


def test_min_trl_returns_positive_integer():
    n = min_trl(_r(500), benchmark_sharpe=0.5, confidence=0.95)
    assert isinstance(n, int) and n > 0


def test_deflated_sharpe_lower_than_psr_when_many_trials():
    r = _r(500, seed=2)
    psr = probabilistic_sharpe_ratio(r, benchmark_sharpe=0.0)
    dsr_many = deflated_sharpe(r, trials_tested=200, benchmark_sharpe=0.0)
    assert dsr_many < psr


def test_sharpe_ci_contains_point_estimate():
    r = _r(1000)
    lo, hi = sharpe_ci(r)
    from app.core.metrics import sharpe
    s = sharpe(r)
    assert lo <= s <= hi
