"""Tests for the pure compute_dashboard function."""
from datetime import datetime, date
from dashboard import compute_dashboard


def _t(id_, pnl, status, created_at, closed_at):
    """Minimal trade dict for tests."""
    return {
        "id": id_,
        "pnl": pnl,
        "status": status,
        "created_at": created_at,
        "closed_at": closed_at,
    }


def test_empty_input():
    out = compute_dashboard([], latest_snapshot_balance=None, today=date(2026, 6, 1))
    assert out["this_month"]["pnl"] == 0
    assert out["this_month"]["trades"] == 0
    assert out["this_week"]["trades"] == 0
    assert out["ytd"]["pnl"] == 0
    assert out["open_trades"]["count"] == 0
    assert out["equity_curve"] == []
    assert len(out["monthly"]) == 12
    assert len(out["weekly"]) == 4
    assert len(out["daily_heatmap"]) == 90


def test_monthly_close_date_attribution():
    trades = [
        _t(1, 100, "win", "2026-05-01T10:00:00", "2026-05-01T15:00:00"),
        _t(2, -50, "loss", "2026-05-15T10:00:00", "2026-05-15T15:00:00"),
        _t(3, 200, "win", "2026-06-01T10:00:00", "2026-06-01T15:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=0, today=date(2026, 6, 5))
    by_month = {m["label"]: m for m in out["monthly"]}
    assert by_month["May 2026"]["pnl_close_date"] == 50  # 100 - 50
    assert by_month["May 2026"]["trades"] == 2
    assert by_month["Jun 2026"]["pnl_close_date"] == 200
    assert by_month["Jun 2026"]["trades"] == 1


def test_monthly_split_attribution():
    # Trade opened May 28, closed Jun 3 (7 days total: 4 in May, 3 in Jun), pnl 700
    trades = [
        _t(1, 700, "win", "2026-05-28T10:00:00", "2026-06-03T15:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=0, today=date(2026, 6, 5))
    by_month = {m["label"]: m for m in out["monthly"]}
    assert by_month["May 2026"]["pnl_split"] == round(700 * 4 / 7, 2)
    assert by_month["Jun 2026"]["pnl_split"] == round(700 * 3 / 7, 2)
    # Close-date attribution puts all 700 in June
    assert by_month["May 2026"]["pnl_close_date"] == 0
    assert by_month["Jun 2026"]["pnl_close_date"] == 700


def test_open_trades_count():
    trades = [
        _t(1, None, "entered", "2026-05-30T10:00:00", None),
        _t(2, None, "entered", "2026-05-31T10:00:00", None),
        _t(3, 100,  "win",     "2026-05-01T10:00:00", "2026-05-01T15:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
    assert out["open_trades"]["count"] == 2


def test_equity_curve_with_baseline():
    trades = [
        _t(1, 100, "win",  "2026-01-04T10:00:00", "2026-01-04T15:00:00"),
        _t(2, -50, "loss", "2026-01-07T10:00:00", "2026-01-07T15:00:00"),
        _t(3, 200, "win",  "2026-01-10T10:00:00", "2026-01-10T15:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=1000.0, today=date(2026, 1, 15))
    curve = out["equity_curve"]
    assert len(curve) == 3
    assert curve[0]["cumulative_pnl"] == 1100
    assert curve[1]["cumulative_pnl"] == 1050
    assert curve[2]["cumulative_pnl"] == 1250


def test_equity_curve_no_baseline_starts_zero():
    trades = [
        _t(1, 100, "win", "2026-01-04T10:00:00", "2026-01-04T15:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 1, 15))
    assert out["equity_curve"][0]["cumulative_pnl"] == 100


def test_daily_heatmap_includes_zero_days():
    trades = [
        _t(1, 50, "win", "2026-05-30T10:00:00", "2026-05-30T15:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
    heat = {d["date"]: d for d in out["daily_heatmap"]}
    assert heat["2026-05-30"]["pnl"] == 50
    assert heat["2026-05-30"]["trades"] == 1
    # Day before with no activity
    assert heat["2026-05-29"]["pnl"] == 0
    assert heat["2026-05-29"]["trades"] == 0


def test_excludes_planned_and_skipped_from_pnl():
    trades = [
        _t(1, 100, "win",     "2026-05-30T10:00:00", "2026-05-30T15:00:00"),
        _t(2, 999, "planned", "2026-05-30T10:00:00", None),
        _t(3, 999, "skipped", "2026-05-30T10:00:00", "2026-05-30T15:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 5, 31))
    assert out["this_month"]["pnl"] == 100
    assert out["this_month"]["trades"] == 1


def test_ytd_aggregation():
    trades = [
        _t(1, 100, "win",  "2026-01-15T10:00:00", "2026-01-15T15:00:00"),
        _t(2, -50, "loss", "2026-03-15T10:00:00", "2026-03-15T15:00:00"),
        _t(3, 200, "win",  "2026-05-15T10:00:00", "2026-05-15T15:00:00"),
        # Last year — excluded
        _t(4, 999, "win",  "2025-12-15T10:00:00", "2025-12-15T15:00:00"),
    ]
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
    assert out["ytd"]["pnl"] == 250
    assert out["ytd"]["trades"] == 3
    assert out["ytd"]["win_rate"] == round(2/3, 2)
