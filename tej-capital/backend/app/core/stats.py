"""Statistical validity of a Sharpe ratio.

References:
- Bailey & Lopez de Prado (2012), "The Sharpe Ratio Efficient Frontier",
  Journal of Risk 15(2). PSR + MinTRL.
- Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio",
  Journal of Portfolio Management 40(5).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats

from app.core.metrics import sharpe, skewness, excess_kurtosis

MIN_N = 30


def sharpe_t_stat(returns: pd.Series) -> float | None:
    if returns is None or len(returns) < MIN_N:
        return None
    s = sharpe(returns)
    if s is None:
        return None
    return float(s * np.sqrt(len(returns) / 252))


def probabilistic_sharpe_ratio(returns: pd.Series, benchmark_sharpe: float = 0.0) -> float | None:
    if returns is None or len(returns) < MIN_N:
        return None
    n = len(returns)
    s = sharpe(returns)
    if s is None:
        return None
    # Convert annualised → per-observation Sharpe for the formula
    s_obs = s / np.sqrt(252)
    sb_obs = benchmark_sharpe / np.sqrt(252)
    skew = skewness(returns) or 0.0
    ex_kurt = excess_kurtosis(returns) or 0.0
    num = (s_obs - sb_obs) * np.sqrt(n - 1)
    den = np.sqrt(1 - skew * s_obs + ex_kurt / 4.0 * s_obs ** 2)
    z = num / den
    return float(stats.norm.cdf(z))


def min_trl(returns: pd.Series, benchmark_sharpe: float, confidence: float = 0.95) -> int | None:
    if returns is None or len(returns) < MIN_N:
        return None
    s = sharpe(returns)
    if s is None or s == benchmark_sharpe:
        return None
    s_obs = s / np.sqrt(252)
    sb_obs = benchmark_sharpe / np.sqrt(252)
    skew = skewness(returns) or 0.0
    ex_kurt = excess_kurtosis(returns) or 0.0
    z = stats.norm.ppf(confidence)
    # n = 1 + [1 - skew*s + (ex_kurt/4)*s^2] * (z / (s - sb))^2
    numerator = 1.0 - skew * s_obs + (ex_kurt / 4.0) * s_obs ** 2
    if numerator <= 0 or (s_obs - sb_obs) == 0:
        return None
    n = 1 + numerator * (z / (s_obs - sb_obs)) ** 2
    return int(np.ceil(n))


def deflated_sharpe(returns: pd.Series, trials_tested: int, benchmark_sharpe: float = 0.0) -> float | None:
    """DSR: PSR corrected for multiple testing (BLdP 2014)."""
    if returns is None or len(returns) < MIN_N or trials_tested < 1:
        return None
    n_trials = max(1, trials_tested)
    # Expected max Sharpe of n_trials random strategies (BLdP eq. 8)
    emc = 0.5772156649
    z_scale = (1 - emc) * stats.norm.ppf(1 - 1 / n_trials) + emc * stats.norm.ppf(1 - 1 / (n_trials * np.e))
    # Approximate std dev of Sharpe estimator across trials as 1/sqrt(len)
    sigma_sr = 1.0 / np.sqrt(252)  # per-observation approximation
    expected_max_sr = benchmark_sharpe / np.sqrt(252) + sigma_sr * z_scale
    inflated_bench = expected_max_sr * np.sqrt(252)
    return probabilistic_sharpe_ratio(returns, benchmark_sharpe=inflated_bench)


def sharpe_ci(returns: pd.Series, alpha: float = 0.05) -> tuple[float, float] | None:
    if returns is None or len(returns) < MIN_N:
        return None
    n = len(returns)
    s = sharpe(returns)
    if s is None:
        return None
    skew = skewness(returns) or 0.0
    ex_kurt = excess_kurtosis(returns) or 0.0
    s_obs = s / np.sqrt(252)
    var = (1 - skew * s_obs + ex_kurt / 4.0 * s_obs ** 2) / (n - 1)
    se = np.sqrt(max(var, 0.0)) * np.sqrt(252)
    z = stats.norm.ppf(1 - alpha / 2)
    return (float(s - z * se), float(s + z * se))
