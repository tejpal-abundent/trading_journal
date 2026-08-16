import pandas as pd
import pytest
from app.core.trades import (
    expectancy_r, payoff_ratio, profit_factor, top_n_concentration,
    compliance_gap_significance, streaks, mae_mfe_stats,
)


def _trades(rows):
    return pd.DataFrame(rows)


def test_expectancy_r_skips_nulls():
    t = _trades([
        {"r_multiple": 1.5, "risk_amount": 100, "rule_compliant": True, "mae_r": -0.3, "mfe_r": 1.5, "gross_pnl": 150, "costs": 5},
        {"r_multiple": None, "risk_amount": None, "rule_compliant": True, "mae_r": None, "mfe_r": None, "gross_pnl": 50, "costs": 0},
        {"r_multiple": -1.0, "risk_amount": 100, "rule_compliant": True, "mae_r": -1.0, "mfe_r": 0.2, "gross_pnl": -100, "costs": 5},
    ])
    # (1.5 + -1.0) / 2 = 0.25
    assert expectancy_r(t) == pytest.approx(0.25)


def test_payoff_ratio_avg_win_over_avg_loss():
    t = _trades([
        {"r_multiple": 2.0}, {"r_multiple": 1.0}, {"r_multiple": -0.5}, {"r_multiple": -1.5},
    ])
    # avg_win = 1.5, avg_loss = -1.0, payoff = 1.5
    assert payoff_ratio(t) == pytest.approx(1.5)


def test_top_3_concentration_share():
    t = _trades([
        {"id": i, "r_multiple": r} for i, r in enumerate([5.0, 3.0, 2.0, 0.5, -0.5])
    ])
    result = top_n_concentration(t, n=3)
    # top 3 sum to 10 out of total gross = 10; concentration = 1.0
    # But total profit = 10 + 0.5 = 10.5 (losers not subtracted for numerator).
    # We define: sum(top_n R) / sum(positive R).
    # positive sum = 10.5, top-3 positive = 10 → 0.952
    assert result["top_n_share"] == pytest.approx(0.952, abs=0.01)


def test_compliance_gap_significance():
    compliant = [1.0] * 20 + [-0.5] * 5
    noncompliant = [-1.0] * 5 + [-0.2] * 3
    t = pd.concat([
        _trades([{"r_multiple": r, "rule_compliant": True} for r in compliant]),
        _trades([{"r_multiple": r, "rule_compliant": False} for r in noncompliant]),
    ], ignore_index=True)
    result = compliance_gap_significance(t)
    assert result["compliant_expectancy"] > 0
    assert result["noncompliant_expectancy"] < 0
    assert 0.0 <= result["p_value"] <= 1.0


def test_streaks():
    t = _trades([{"r_multiple": r} for r in [1, 1, 1, -1, -1, 1, -1, -1, -1, -1, 1]])
    s = streaks(t)
    assert s["longest_win_streak"] == 3
    assert s["longest_loss_streak"] == 4
