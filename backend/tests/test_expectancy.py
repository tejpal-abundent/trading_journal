"""Tests for expectancy + streak in dashboard payload."""
from datetime import date
from dashboard import compute_dashboard


def _t(id_, pnl, status, closed_at, risk_dollars=None):
    return {"id": id_, "pnl": pnl, "status": status,
            "created_at": closed_at, "closed_at": closed_at,
            "risk_dollars": risk_dollars}


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


def test_disciplined_expectancy_weights_small_losses():
    # planned risk = $100 on every loss.
    # Loss buckets (as % of planned risk):
    #   $20  → ≤30% → weight 0.25 → effective $5
    #   $40  → (30,50%] → weight 0.5 → effective $20
    #   $60  → (50,70%] → weight 0.75 → effective $45
    #   $90  → >70% → weight 1.0 → effective $90
    trades = [
        _t(1, 200, "win",  "2026-05-30T10:00:00", risk_dollars=100),
        _t(2, 200, "win",  "2026-05-30T11:00:00", risk_dollars=100),
        _t(3, -20, "loss", "2026-05-30T12:00:00", risk_dollars=100),
        _t(4, -40, "loss", "2026-05-30T13:00:00", risk_dollars=100),
        _t(5, -60, "loss", "2026-05-30T14:00:00", risk_dollars=100),
        _t(6, -90, "loss", "2026-05-30T15:00:00", risk_dollars=100),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))

    true_e = out["expectancy"]
    disc_e = out["disciplined_expectancy"]

    # True EV: (2/6)*200 − (4/6)*((20+40+60+90)/4) = 66.67 − (0.6667*52.5) = 66.67 − 35.0 = 31.67
    assert true_e["value"] == 31.67
    # Disciplined EV: (2/6)*200 − (5+20+45+90)/6 = 66.67 − 26.67 = 40.0
    assert disc_e["value"] == 40.0
    assert disc_e["discipline_tax"] == round(40.0 - 31.67, 2)  # 8.33
    assert disc_e["losses"] == 4
    assert disc_e["wins"] == 2


def test_disciplined_expectancy_missing_risk_treated_as_full_loss():
    # Loss with no risk_dollars (legacy trade) keeps weight 1.0 — no discount.
    trades = [
        _t(1, 100, "win",  "2026-05-30T10:00:00", risk_dollars=100),
        _t(2, -10, "loss", "2026-05-30T11:00:00", risk_dollars=None),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
    # Tax = 0 because the loss can't be discipline-discounted
    assert out["disciplined_expectancy"]["discipline_tax"] == 0.0
    assert out["disciplined_expectancy"]["value"] == out["expectancy"]["value"]


def test_disciplined_expectancy_all_wins_no_tax():
    trades = [
        _t(1, 100, "win", "2026-05-30T10:00:00", risk_dollars=100),
        _t(2, 200, "win", "2026-05-30T11:00:00", risk_dollars=100),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
    assert out["disciplined_expectancy"]["discipline_tax"] == 0.0
    assert out["disciplined_expectancy"]["value"] == out["expectancy"]["value"]


def test_streak_breakeven_breaks():
    trades = [
        _t(1, 100, "win",       "2026-05-29T10:00:00"),
        _t(2, 100, "win",       "2026-05-30T10:00:00"),
        _t(3,   0, "breakeven", "2026-05-31T10:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
    assert out["streak"] == {"kind": "none", "length": 0}
