import pytest
from risk import compute_risk


def test_compute_risk_long_trade():
    r = compute_risk(entry=100.0, stop=95.0, position_size=10, account_size=10000)
    assert r["risk_dollars"] == 50.0
    assert r["risk_percent"] == 0.5


def test_compute_risk_short_trade_uses_abs():
    r = compute_risk(entry=100.0, stop=105.0, position_size=10, account_size=10000)
    assert r["risk_dollars"] == 50.0
    assert r["risk_percent"] == 0.5


def test_compute_risk_returns_nulls_when_input_missing():
    r = compute_risk(entry=100.0, stop=None, position_size=10, account_size=10000)
    assert r == {"risk_dollars": None, "risk_percent": None}


def test_compute_risk_handles_zero_account():
    r = compute_risk(entry=100.0, stop=95.0, position_size=10, account_size=0)
    assert r["risk_dollars"] == 50.0
    assert r["risk_percent"] is None


def test_compute_risk_rounds_to_4_decimals():
    r = compute_risk(entry=100.123456, stop=95.0, position_size=1, account_size=10000)
    assert r["risk_dollars"] == 5.1235
    assert r["risk_percent"] == 0.0512
