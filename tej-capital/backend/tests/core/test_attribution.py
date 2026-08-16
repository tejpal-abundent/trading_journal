import pandas as pd
import pytest
from app.core.attribution import grouped_stats


def test_verdict_not_enough_under_20_trades():
    t = pd.DataFrame([{"setup": "A", "r_multiple": 0.5}] * 10)
    rows = grouped_stats(t, by="setup")
    assert rows[0]["verdict"] == "not_enough"


def test_verdict_working_when_expectancy_above_015():
    t = pd.DataFrame([{"setup": "A", "r_multiple": 0.5}] * 25)
    rows = grouped_stats(t, by="setup")
    assert rows[0]["verdict"] == "working"


def test_verdict_retire_when_expectancy_negative():
    t = pd.DataFrame([{"setup": "A", "r_multiple": -0.2}] * 25)
    rows = grouped_stats(t, by="setup")
    assert rows[0]["verdict"] == "retire"


def test_verdict_marginal_between_zero_and_015():
    t = pd.DataFrame([{"setup": "A", "r_multiple": 0.05}] * 25)
    rows = grouped_stats(t, by="setup")
    assert rows[0]["verdict"] == "marginal"


def test_multiple_groups_sorted_by_total_r_desc():
    rows_data = [{"setup": "A", "r_multiple": 1.0}] * 25 + [{"setup": "B", "r_multiple": 0.2}] * 25
    t = pd.DataFrame(rows_data)
    rows = grouped_stats(t, by="setup")
    assert rows[0]["group"] == "A"
    assert rows[1]["group"] == "B"
