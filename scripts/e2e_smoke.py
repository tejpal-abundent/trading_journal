"""End-to-end smoke test for trading-journal v2 API.

Usage:
    python scripts/e2e_smoke.py http://localhost:8111
    python scripts/e2e_smoke.py https://trading-journal-1-8ork.onrender.com
"""
import sys
import requests

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8111"


def call(method, path, **kwargs):
    r = requests.request(method, f"{BASE}{path}", **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


def main():
    h = requests.get(f"{BASE}/").json()
    assert h["status"] == "ok"
    print("✓ Health check")

    strategies = call("GET", "/api/strategies")
    assert any(s["name"] == "Zone Failure" for s in strategies), strategies
    print(f"✓ Strategies: {[s['name'] for s in strategies]}")

    plan = call("POST", "/api/trades", json={
        "pair": "SMOKE/USD", "direction": "LONG", "timeframe": "4H",
        "strategy": "Zone Failure", "setup_score": 90, "verdict": "A+",
        "criteria_checked": ["trend", "zone", "signal", "failure"],
        "planned_entry": 100.0, "planned_stop": 95.0, "planned_target": 110.0, "planned_rr": 2.0,
        "notes": "Smoke test plan",
    })
    tid = plan["id"]
    assert plan["status"] == "planned"
    print(f"✓ Plan created (id={tid})")

    entered = call("POST", f"/api/trades/{tid}/enter", json={
        "entry_price": 100.5, "stop_loss": 95.0,
        "position_size": 1.0, "account_size": 10000.0,
        "entry_timing": "on_time", "emotions_entry": ["confident"],
    })
    assert entered["status"] == "entered"
    assert abs(entered["risk_dollars"] - 5.5) < 0.001
    print(f"✓ Entered (risk ${entered['risk_dollars']})")

    closed = call("POST", f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 110.0,
        "pnl": 9.5, "rr_achieved": 1.7,
        "rules_followed": True,
        "mistake_tags": [], "emotions_exit": ["calm"],
        "lessons": "Smoke test passed",
    })
    assert closed["status"] == "win"
    print("✓ Closed as WIN")

    a = call("GET", "/api/analytics?days=1")
    assert a["closed_trades"] >= 1
    print(f"✓ Analytics: {a['closed_trades']} closed, {a['total_pnl']} total P/L")

    call("DELETE", f"/api/trades/{tid}")
    print("✓ Cleanup")

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
