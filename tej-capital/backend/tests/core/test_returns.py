import uuid
from decimal import Decimal
from datetime import date
import pandas as pd
import pytest

from app.core.returns import daily_twr, composite_twr, reconcile, detect_anomalies


def _s(items):
    return pd.Series(dict(items))


def test_twr_no_flows_matches_simple_return():
    nav = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 10100.0), (date(2026, 1, 3), 10201.0)])
    flows = pd.Series(dtype="float64")
    r = daily_twr(nav, flows)
    # Day 2: 100/10000 = 1%. Day 3: 101/10100 = 1%.
    assert r.iloc[0] == pytest.approx(0.01, rel=1e-6)
    assert r.iloc[1] == pytest.approx(0.01, rel=1e-6)


def test_twr_invariant_to_deposits_R2():
    """R2: a deposit is not profit — TWR must be unchanged whether we deposit or not."""
    nav_no_flow = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 10100.0)])
    r_no_flow = daily_twr(nav_no_flow, pd.Series(dtype="float64"))

    nav_with_flow = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 15100.0)])
    flows = _s([(date(2026, 1, 2), 5000.0)])  # 5k deposit
    r_with_flow = daily_twr(nav_with_flow, flows, timing="end_of_day")

    assert r_with_flow.iloc[0] == pytest.approx(r_no_flow.iloc[0], rel=1e-6)


def test_missing_days_not_zero_padded_R3():
    nav = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 5), 10100.0)])
    r = daily_twr(nav, pd.Series(dtype="float64"))
    assert len(r) == 1  # one return day, not four
    assert r.index[0] == date(2026, 1, 5)


def test_composite_weighted_by_beginning_of_day():
    a = uuid.UUID(int=1)
    b = uuid.UUID(int=2)
    accounts = {
        a: (_s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 10200.0)]), pd.Series(dtype="float64")),
        b: (_s([(date(2026, 1, 1), 500.0), (date(2026, 1, 2), 550.0)]), pd.Series(dtype="float64")),
    }
    r = composite_twr(accounts)
    # Big account: +2%. Small account: +10%. Weighted by BoD: (10000*0.02 + 500*0.10)/10500 = 0.02381
    assert r.iloc[0] == pytest.approx(0.02381, abs=1e-4)


def test_reconcile_flags_delta_above_tolerance():
    broker = _s([(date(2026, 1, 1), 10000.0)])
    rebuilt = _s([(date(2026, 1, 1), 9950.0)])
    result = reconcile(broker, rebuilt, tolerance=Decimal("1.00"))
    assert len(result) == 1
    assert result[0]["status"] == "discrepancy"
    assert abs(result[0]["delta"]) == pytest.approx(50.0)


def test_anomaly_large_return_flagged():
    nav = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 10800.0)])  # +8% day
    anomalies = detect_anomalies(nav, pd.Series(dtype="float64"), daily_limit_pct=0.02)
    kinds = [a["kind"] for a in anomalies]
    assert "return_exceeds_3x_limit" in kinds


def test_anomaly_large_deposit_and_large_return_same_day():
    nav = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 15800.0)])
    flows = _s([(date(2026, 1, 2), 5000.0)])
    anomalies = detect_anomalies(nav, flows, daily_limit_pct=0.02)
    kinds = [a["kind"] for a in anomalies]
    assert "deposit_and_large_return_same_day" in kinds
