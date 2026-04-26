import os
os.environ.pop("TURSO_DB_URL", None)

import sys
from fastapi.testclient import TestClient
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
        "confluences": [], "mfe_r": None, "mae_r": None,
        "created_at": "2026-04-20T10:00:00", "closed_at": "2026-04-20T14:00:00",
    }
    base.update(overrides)
    return base


def test_confluence_impact_groups_by_tag():
    trades = [
        _trade(status="win",  pnl=20, confluences=["london_open", "htf_aligned"]),
        _trade(status="win",  pnl=10, confluences=["london_open"]),
        _trade(status="loss", pnl=-30, confluences=["asian_session"]),
        _trade(status="loss", pnl=-20, confluences=["asian_session", "htf_aligned"]),
    ]
    rows = compute_analytics(trades, days=14)["confluence_impact"]
    by_tag = {r["tag"]: r for r in rows}
    assert by_tag["london_open"]["count"] == 2
    assert by_tag["london_open"]["win_rate"] == 100.0
    assert by_tag["asian_session"]["count"] == 2
    assert by_tag["asian_session"]["win_rate"] == 0.0
    assert by_tag["htf_aligned"]["count"] == 2  # one win, one loss
    assert by_tag["htf_aligned"]["win_rate"] == 50.0


def test_confluence_impact_skips_trades_with_no_confluences():
    trades = [
        _trade(status="win", pnl=10, confluences=[]),
        _trade(status="win", pnl=20, confluences=["foo"]),
    ]
    rows = compute_analytics(trades, days=14)["confluence_impact"]
    tags = {r["tag"] for r in rows}
    assert tags == {"foo"}
    assert "(none)" not in tags


def test_mfe_mae_analysis_aggregates_winners_and_losers():
    trades = [
        _trade(status="win",  pnl=20, mfe_r=2.5, mae_r=0.3),
        _trade(status="win",  pnl=10, mfe_r=1.5, mae_r=0.5),
        _trade(status="loss", pnl=-10, mfe_r=0.6, mae_r=1.0),
    ]
    a = compute_analytics(trades, days=14)["mfe_mae_analysis"]
    assert a["count"] > 0
    assert a["avg_mfe_winners"] == 2.0  # (2.5 + 1.5) / 2
    assert a["avg_mae_winners"] == 0.4
    assert a["avg_mfe_losers"]  == 0.6
    assert a["max_mfe_all"] == 2.5


def test_mfe_mae_analysis_returns_zero_count_when_no_data():
    trades = [_trade(status="win", pnl=10)]
    a = compute_analytics(trades, days=14)["mfe_mae_analysis"]
    assert a["count"] == 0


# ---- API round-trip ----

def _client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for m in list(sys.modules):
        if m in ("main", "models", "database", "migrations"):
            sys.modules.pop(m)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import main
    db_path = os.path.join(os.path.dirname(main.__file__), "trading_journal.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    main.startup()
    return TestClient(main.app)


def test_create_plan_with_confluences_and_close_with_mfe_mae(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/trades", json={
        "pair": "EUR/USD", "direction": "LONG", "timeframe": "1H",
        "setup_score": 75, "verdict": "B SETUP",
        "criteria_checked": ["trend", "zone", "signal", "failure"],
        "confluences": ["london_open", "htf_aligned", "30min_reversal"],
    })
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    assert sorted(r.json()["confluences"]) == ["30min_reversal", "htf_aligned", "london_open"]

    c.post(f"/api/trades/{tid}/enter", json={
        "entry_price": 1.10, "stop_loss": 1.09,
        "position_size": 1.0, "account_size": 10000.0,
    })
    r = c.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 1.11,
        "pnl": 10.0, "rr_achieved": 1.0,
        "mfe_r": 1.8, "mae_r": 0.4,
        "rules_followed": True,
    })
    assert r.json()["mfe_r"] == 1.8
    assert r.json()["mae_r"] == 0.4


def test_analytics_confluence_filter_intersection(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    # Two retroactive wins with different confluences
    base = {
        "pair": "GBP/USD", "direction": "LONG", "timeframe": "1H",
        "setup_score": 80, "verdict": "B",
        "criteria_checked": ["trend", "zone", "signal", "failure"],
        "entry_price": 1.20, "stop_loss": 1.19, "exit_price": 1.21,
        "position_size": 1.0, "account_size": 10000.0,
        "status": "win", "pnl": 10.0,
    }
    c.post("/api/trades/retroactive", json={**base, "confluences": ["london", "htf_ok"]})
    c.post("/api/trades/retroactive", json={**base, "confluences": ["asian", "htf_ok"]})
    c.post("/api/trades/retroactive", json={**base, "confluences": ["london"]})

    r = c.get("/api/analytics?days=30&confluences=london,htf_ok")
    assert r.status_code == 200
    body = r.json()
    assert body["confluence_filter"] == ["london", "htf_ok"]
    # Only the first trade matches BOTH tags
    assert body["total_trades"] == 1
    assert body["closed_trades"] == 1
