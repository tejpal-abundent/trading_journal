"""Tests for expectancy + streak in dashboard payload."""
from datetime import date
from dashboard import compute_dashboard


def _t(id_, pnl, status, closed_at):
    return {"id": id_, "pnl": pnl, "status": status,
            "created_at": closed_at, "closed_at": closed_at}


def test_expectancy_basic():
    trades = [
        _t(1, 100, "win",  "2026-05-30T10:00:00"),
        _t(2, 100, "win",  "2026-05-30T11:00:00"),
        _t(3, -50, "loss", "2026-05-30T12:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
    e = out["expectancy"]
    # win_rate=2/3, loss_rate=1/3, avg_win=100, avg_loss=50
    # EV = (2/3)*100 - (1/3)*50 = 66.67 - 16.67 = 50.0
    assert e["value"] == 50.0
    assert e["wins"] == 2
    assert e["losses"] == 1
    assert e["avg_win"] == 100.0
    assert e["avg_loss"] == 50.0


def test_expectancy_empty():
    out = compute_dashboard([], latest_snapshot_balance=None, today=date(2026, 6, 1))
    assert out["expectancy"]["value"] == 0.0
    assert out["expectancy"]["trades"] == 0
    assert out["expectancy"]["last_trade_delta"] is None


def test_expectancy_last_trade_delta_present():
    trades = [
        _t(1, 100, "win",  "2026-05-30T10:00:00"),
        _t(2, -50, "loss", "2026-05-31T11:00:00"),  # most recent
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
    assert out["expectancy"]["last_trade_delta"] is not None


def test_streak_three_losses():
    trades = [
        _t(1, 100, "win",  "2026-05-28T10:00:00"),
        _t(2, -10, "loss", "2026-05-29T10:00:00"),
        _t(3, -20, "loss", "2026-05-30T10:00:00"),
        _t(4, -30, "loss", "2026-05-31T10:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
    assert out["streak"] == {"kind": "loss", "length": 3}


def test_streak_breakeven_breaks():
    trades = [
        _t(1, 100, "win",       "2026-05-29T10:00:00"),
        _t(2, 100, "win",       "2026-05-30T10:00:00"),
        _t(3,   0, "breakeven", "2026-05-31T10:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
    assert out["streak"] == {"kind": "none", "length": 0}
