from analytics import compute_analytics


def _trade(**overrides):
    base = {
        "id": 1, "pair": "XAU/USD", "direction": "LONG", "timeframe": "4H",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "B",
        "criteria_checked": [], "notes": "",
        "planned_entry": None, "planned_stop": None, "planned_target": None, "planned_rr": None,
        "status": "win", "retroactive": False,
        "entry_price": 100.0, "exit_price": 110.0, "stop_loss": 95.0, "take_profit": 120.0,
        "position_size": 1.0, "account_size": 10000.0,
        "risk_dollars": 5.0, "risk_percent": 0.05,
        "entry_timing": "on_time",
        "emotions_entry": [], "feelings_entry": "",
        "skip_reason": "",
        "partial_exits": [],
        "pnl": 10.0, "pnl_percent": 1.0, "rr_achieved": 2.0,
        "rules_followed": True,
        "mistake_tags": [], "emotions_exit": [], "feelings_exit": "", "lessons": "",
        "chart_url": "",
        "created_at": "2026-04-20T10:00:00", "closed_at": "2026-04-20T14:00:00",
    }
    base.update(overrides)
    return base


def test_basic_win_rate():
    trades = [_trade(status="win", pnl=20), _trade(status="loss", pnl=-10)]
    a = compute_analytics(trades, days=14)
    assert a["total_trades"] == 2
    assert a["wins"] == 1
    assert a["losses"] == 1
    assert a["win_rate"] == 50.0
    assert a["total_pnl"] == 10.0


def test_plan_adherence_excludes_retroactive():
    trades = [
        _trade(status="win", rules_followed=True, retroactive=False, pnl=20),
        _trade(status="loss", rules_followed=False, retroactive=False, pnl=-10),
        _trade(status="win", rules_followed=True, retroactive=True, pnl=15),
    ]
    a = compute_analytics(trades, days=14)["plan_adherence"]
    assert a["rules_followed_pct"] == 50.0
    assert a["rules_followed_win_rate"] == 100.0
    assert a["rules_broken_win_rate"] == 0.0


def test_skip_rate_uses_planned_lifecycle_denominator():
    trades = [
        _trade(status="entered", retroactive=False),
        _trade(status="win", retroactive=False, pnl=10),
        _trade(status="skipped", retroactive=False),
        _trade(status="loss", retroactive=True, pnl=-5),
    ]
    a = compute_analytics(trades, days=14)["plan_adherence"]
    assert a["skip_rate"] == round(1 / 3 * 100, 1)


def test_risk_discipline_threshold():
    trades = [
        _trade(risk_percent=0.5, status="win", pnl=10),
        _trade(risk_percent=2.5, status="loss", pnl=-50),
        _trade(risk_percent=1.0, status="win", pnl=20),
    ]
    rd = compute_analytics(trades, days=14)["risk_discipline"]
    assert rd["over_threshold_count"] == 1
    assert abs(rd["max_risk_pct"] - 2.5) < 0.001


def test_mistake_impact_buckets_none_separately():
    trades = [
        _trade(status="win", pnl=20, mistake_tags=[]),
        _trade(status="win", pnl=10, mistake_tags=[]),
        _trade(status="loss", pnl=-30, mistake_tags=["moved_sl"]),
        _trade(status="loss", pnl=-20, mistake_tags=["moved_sl", "exited_early"]),
    ]
    rows = compute_analytics(trades, days=14)["mistake_impact"]
    by_tag = {r["tag"]: r for r in rows}
    assert by_tag["(none)"]["count"] == 2
    assert by_tag["(none)"]["win_rate"] == 100.0
    assert by_tag["moved_sl"]["count"] == 2
    assert by_tag["exited_early"]["count"] == 1


def test_edge_composite_returns_not_enough_data_under_5():
    trades = [_trade(status="win", pnl=10) for _ in range(3)]
    e = compute_analytics(trades, days=14)["edge_composite"]
    assert e["headline"] == "Not enough data yet"
    assert e["count"] == 0


def test_top_level_win_rate_decorated_with_ci():
    trades = [_trade(status="win", pnl=20), _trade(status="loss", pnl=-10)]
    a = compute_analytics(trades, days=14)
    assert a["win_rate"] == 50.0
    assert a["n"] == 2
    assert isinstance(a["win_rate_ci"], (list, tuple))
    assert len(a["win_rate_ci"]) == 2
    assert a["confidence"] == "Noise"


def test_top_level_win_rate_no_closed_trades():
    trades = [_trade(status="planned")]
    a = compute_analytics(trades, days=14)
    assert a["n"] == 0
    assert a["win_rate_ci"] is None
    assert a["confidence"] == "Noise"


def test_score_analysis_rows_have_ci_and_confidence():
    trades = [
        _trade(status="win", setup_score=90, pnl=20),
        _trade(status="loss", setup_score=88, pnl=-10),
        _trade(status="win", setup_score=75, pnl=15),
    ]
    a = compute_analytics(trades, days=14)["score_analysis"]
    assert "A (85-100)" in a
    assert "n" in a["A (85-100)"]
    assert "win_rate_ci" in a["A (85-100)"]
    assert "confidence" in a["A (85-100)"]


def test_pair_breakdown_has_ci():
    trades = [
        _trade(status="win", pair="XAU/USD", pnl=10),
        _trade(status="loss", pair="XAU/USD", pnl=-5),
        _trade(status="win", pair="EUR/USD", pnl=20),
    ]
    a = compute_analytics(trades, days=14)["pair_breakdown"]
    assert "win_rate_ci" in a["XAU/USD"]
    assert "confidence" in a["XAU/USD"]


def test_direction_stats_has_ci():
    trades = [
        _trade(status="win", direction="LONG", pnl=10),
        _trade(status="loss", direction="LONG", pnl=-5),
    ]
    a = compute_analytics(trades, days=14)["direction_stats"]
    assert "win_rate_ci" in a["LONG"]
    assert a["LONG"]["confidence"] == "Noise"


def test_mistake_impact_rows_have_ci():
    trades = [
        _trade(status="win", pnl=10, mistake_tags=["moved_sl"]),
        _trade(status="loss", pnl=-5, mistake_tags=["moved_sl"]),
    ]
    rows = compute_analytics(trades, days=14)["mistake_impact"]
    for r in rows:
        assert "win_rate_ci" in r
        assert "confidence" in r


def test_timing_impact_buckets_have_ci():
    trades = [
        _trade(status="win", entry_timing="on_time", pnl=10),
        _trade(status="loss", entry_timing="late", pnl=-5),
    ]
    a = compute_analytics(trades, days=14)["timing_impact"]
    assert "win_rate_ci" in a["on_time"]
    assert "confidence" in a["on_time"]


def test_sample_integrity_clean_predicate():
    # 5 closed trades; 3 are clean (rules_followed=True, no mistakes,
    # not retroactive, on_time entry); 2 are not clean.
    trades = [
        _trade(status="win", pnl=20, rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="on_time"),
        _trade(status="win", pnl=15, rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="on_time"),
        _trade(status="loss", pnl=-10, rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="on_time"),
        # not clean: late entry
        _trade(status="loss", pnl=-15, rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="late"),
        # not clean: has mistake
        _trade(status="loss", pnl=-5, rules_followed=True,
               mistake_tags=["moved_sl"], retroactive=False, entry_timing="on_time"),
    ]
    s = compute_analytics(trades, days=14)["sample_integrity"]
    assert s["clean_count"] == 3
    assert s["total_count"] == 5
    assert s["clean_pct"] == 60.0
    assert s["clean_win_rate"] == round(2 / 3 * 100, 1)
    assert s["all_win_rate"] == 40.0
    assert s["integrity_delta"] == round(s["clean_win_rate"] - s["all_win_rate"], 1)


def test_sample_integrity_no_clean_trades():
    trades = [_trade(status="loss", pnl=-10, rules_followed=False, mistake_tags=["moved_sl"])]
    s = compute_analytics(trades, days=14)["sample_integrity"]
    assert s["clean_count"] == 0
    assert s["clean_win_rate"] == 0
    assert s["clean_win_rate_ci"] is None


def test_sample_integrity_excludes_null_rules_followed():
    # rules_followed is None → not clean (per spec)
    trades = [
        _trade(status="win", pnl=10, rules_followed=None, mistake_tags=[],
               retroactive=False, entry_timing="on_time"),
    ]
    s = compute_analytics(trades, days=14)["sample_integrity"]
    assert s["clean_count"] == 0
