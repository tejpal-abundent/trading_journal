"""Tests for compute_rr in risk.py."""
import pytest
from risk import compute_rr


def test_long_win_no_trails():
    r = compute_rr(
        entry=100.0, exit_price=130.0, stop_loss=90.0,
        direction="LONG", status="win", trailed_stops=[],
    )
    assert r["rr_achieved"] == 3.0
    assert r["r_locked_at_penultimate_trail"] is None


def test_long_loss_no_trails():
    r = compute_rr(
        entry=100.0, exit_price=85.0, stop_loss=90.0,
        direction="LONG", status="loss", trailed_stops=[],
    )
    assert r["rr_achieved"] == -1.5
    assert r["r_locked_at_penultimate_trail"] is None


def test_short_win_no_trails():
    r = compute_rr(
        entry=100.0, exit_price=80.0, stop_loss=110.0,
        direction="SHORT", status="win", trailed_stops=[],
    )
    assert r["rr_achieved"] == 2.0
    assert r["r_locked_at_penultimate_trail"] is None


def test_long_win_three_trails_uses_penultimate():
    r = compute_rr(
        entry=100.0, exit_price=135.0, stop_loss=90.0,
        direction="LONG", status="win",
        trailed_stops=[
            {"price": 105.0, "at": "2026-05-30T14:00:00Z"},
            {"price": 115.0, "at": "2026-05-30T15:00:00Z"},
            {"price": 125.0, "at": "2026-05-30T16:00:00Z"},
        ],
    )
    # rr_achieved = (135 - 100) / |100 - 90| = 3.5
    assert r["rr_achieved"] == 3.5
    # locked = (135 - 115) / |100 - 90| = 2.0 (penultimate is index -2 = 115)
    assert r["r_locked_at_penultimate_trail"] == 2.0


def test_short_win_two_trails_uses_penultimate():
    r = compute_rr(
        entry=100.0, exit_price=75.0, stop_loss=110.0,
        direction="SHORT", status="win",
        trailed_stops=[
            {"price": 95.0,  "at": "2026-05-30T14:00:00Z"},
            {"price": 85.0,  "at": "2026-05-30T15:00:00Z"},
        ],
    )
    # rr_achieved = (75 - 100) * -1 / 10 = 2.5
    assert r["rr_achieved"] == 2.5
    # penultimate = 95; (75 - 95) * -1 / 10 = 2.0
    assert r["r_locked_at_penultimate_trail"] == 2.0


def test_win_with_one_trail_omits_locked():
    r = compute_rr(
        entry=100.0, exit_price=120.0, stop_loss=90.0,
        direction="LONG", status="win",
        trailed_stops=[{"price": 105.0, "at": "2026-05-30T14:00:00Z"}],
    )
    assert r["rr_achieved"] == 2.0
    assert r["r_locked_at_penultimate_trail"] is None


def test_loss_with_trails_still_omits_locked():
    r = compute_rr(
        entry=100.0, exit_price=85.0, stop_loss=90.0,
        direction="LONG", status="loss",
        trailed_stops=[
            {"price": 95.0, "at": "..."},
            {"price": 105.0, "at": "..."},
        ],
    )
    assert r["rr_achieved"] == -1.5
    assert r["r_locked_at_penultimate_trail"] is None


def test_entry_equals_stop_raises():
    with pytest.raises(ValueError, match="entry_price equals stop_loss"):
        compute_rr(
            entry=100.0, exit_price=110.0, stop_loss=100.0,
            direction="LONG", status="win", trailed_stops=[],
        )


def test_returns_none_when_inputs_missing():
    r = compute_rr(
        entry=None, exit_price=110.0, stop_loss=90.0,
        direction="LONG", status="win", trailed_stops=[],
    )
    assert r == {"rr_achieved": None, "r_locked_at_penultimate_trail": None}
