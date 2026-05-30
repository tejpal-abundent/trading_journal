# Trade Editing, Trailed Stops, Embedded Charts, and Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the six features in `docs/superpowers/specs/2026-05-30-trade-editing-trails-dashboard-design.md`: drop the Plan workflow, make every trade field editable, embed TradingView snapshots + live widget, track trailed stop losses with -1th-trail R-multiple, replace the trade list with a right-side rail, and add a new dashboard at `/`.

**Architecture:** Pure-additive backend (two new columns, one new module `dashboard.py`, two new trail endpoints, one new dashboard endpoint, modifications to PATCH and POST `/api/trades`). Frontend gets a layout shell with right rail + new dashboard, new `TradeDetailPage` (replacing the modal), and supporting components for trails / chart embed. Old planning/list components get deleted at the end.

**Tech Stack:** Backend: FastAPI, SQLAlchemy (SQLite & Turso parity), pytest. Frontend: React 18 + TypeScript + Vite + React Router. No new dependencies on either side except `recharts` for chart visualizations (added in Task 18).

---

## File Structure

**Backend** (`backend/`):
- Modify: `models.py` — add `trailed_stops`, `updated_at` columns to `Trade`
- Modify: `migrations.py` — add `ALTER TABLE` for the two new columns + named migration for `updated_at` backfill
- Modify: `main.py` — new/modified endpoints; remove `/enter` and `/skip`
- Modify: `risk.py` — add `compute_rr` function
- Create: `dashboard.py` — `compute_dashboard(trades, latest_snapshot_balance) -> dict`
- Create: `tests/test_compute_rr.py`
- Create: `tests/test_trails.py`
- Create: `tests/test_dashboard_module.py`
- Create: `tests/test_dashboard_endpoint.py`
- Create: `tests/test_edit_endpoint.py`
- Create: `tests/test_new_trade_endpoint.py`

**Frontend** (`frontend/src/`):
- Modify: `api.ts` — new types, new methods, remove old plan/enter/skip
- Modify: `main.tsx` — new route map + layout shell with right rail
- Modify: `index.css` — minor additions for new layout (rail, dashboard grid)
- Create: `lib/tradingview.ts`
- Create: `lib/dashboard.ts`
- Create: `components/ChartEmbed.tsx`
- Create: `components/EditableField.tsx`
- Create: `components/TrailedStopsTable.tsx`
- Create: `components/CloseTradePanel.tsx`
- Create: `components/TradeDetailPage.tsx`
- Create: `components/NewTradePage.tsx`
- Create: `components/TradeRail.tsx`
- Create: `components/Dashboard.tsx`
- Create: `components/KPICard.tsx`
- Create: `components/MonthlyBars.tsx`
- Create: `components/WeeklyBars.tsx`
- Create: `components/DailyHeatmap.tsx`
- Create: `components/EquityCurve.tsx`
- Delete: `components/PlanForm.tsx`
- Delete: `components/SkipTradeForm.tsx`
- Delete: `components/TradeList.tsx`
- Delete: `components/TradeDetail.tsx`
- Delete: `components/EnterTradeForm.tsx`
- Delete: `components/CloseTradeForm.tsx`

---

## Conventions used in this plan

- **Backend tests** run with `pytest backend/tests/test_<file>.py -v` from the project root (after `cd backend && source venv/bin/activate`).
- **Frontend verification** = `npm run build` from `frontend/` (this runs `tsc && vite build` per `package.json:8`) plus a manual browser check listed at the end. No vitest is configured; we don't add it.
- **TDD order** for every backend change: write failing test → run it → minimal impl → run again → commit.
- **Commits** end every task. Use the message shown in the task; this is a single-user repo, conventional-commit style consistent with recent history.
- **Frontend HTTP**: the project uses a `request<T>(path, opts)` helper from `frontend/src/api.ts` (around line 1). Where this plan shows raw `fetch(...)` calls inside components or new api methods, prefer routing them through `request<T>` for consistency. The fetch shape shown is functionally equivalent — the project pattern is just `request<Trade>(`/trades/${id}/trails`, { method: 'POST', body: JSON.stringify({ price, note }) })`.

---

## Phase A: Backend foundation

### Task 1: Add `trailed_stops` and `updated_at` columns

**Files:**
- Modify: `backend/models.py` (after line 51)
- Modify: `backend/migrations.py` (add to `V2_ALTERS`)
- Modify: `backend/main.py` — extend `_trade_to_dict` and `_parse_trade` to include the new fields

- [ ] **Step 1: Add columns to the SQLAlchemy model**

In `backend/models.py`, between line 51 (`mae_r = Column(Float, nullable=True)`) and line 53 (`created_at = ...`), add:

```python
    trailed_stops = Column(String(4000), default="[]")
    updated_at = Column(DateTime, nullable=True)
```

- [ ] **Step 2: Add the ALTER statements to the migration**

In `backend/migrations.py`, at the end of the `V2_ALTERS` list (after line 42, the `mae_r` line), add:

```python
    "ALTER TABLE trades ADD COLUMN trailed_stops TEXT DEFAULT '[]'",
    "ALTER TABLE trades ADD COLUMN updated_at TEXT",
```

- [ ] **Step 3: Backfill `updated_at` for existing rows (named one-time migration)**

In `backend/migrations.py`, inside `run_migrations` after the `v2_status_backfill` block (after line 121), add:

```python
    # 6. One-time: backfill updated_at = created_at where null
    already = fetch_one_fn("SELECT name FROM _migrations WHERE name = ?", ["v3_updated_at_backfill"])
    if not already:
        execute_fn("UPDATE trades SET updated_at = created_at WHERE updated_at IS NULL")
        execute_fn("INSERT INTO _migrations (name) VALUES (?)", ["v3_updated_at_backfill"])
```

- [ ] **Step 4: Surface the new fields in `_trade_to_dict` and `_parse_trade`**

In `backend/main.py`, in `_trade_to_dict` (line 129-160), add inside the returned dict (before `"created_at"`):

```python
            "trailed_stops": t.trailed_stops or "[]",
            "updated_at": str(t.updated_at) if t.updated_at else None,
```

In `_parse_trade` (line 269-326), add right after the `pe = row.get("partial_exits", "[]")` block:

```python
    ts = row.get("trailed_stops", "[]")
    if isinstance(ts, str):
        try: ts = json.loads(ts)
        except: ts = []
```

And add inside the returned dict (before `"created_at"`):

```python
        "trailed_stops": ts,
        "updated_at": row.get("updated_at"),
```

- [ ] **Step 5: Restart the dev server and verify migration applies cleanly**

```bash
cd backend
source venv/bin/activate
python -c "from migrations import run_migrations; from sqlalchemy import create_engine, text; e = create_engine('sqlite:///trading_journal.db'); \
def _e(s,a=None):\n    with e.begin() as c:\n        c.execute(text(s.replace('?', ':p') if a else s), {f'p':a[0]} if a and len(a)==1 else {})\n; \
import sys; sys.exit(0)"
```

(Quick smoke — the actual migration runs via `app.on_event('startup')`. Easier: just run the API once.)

```bash
python -m uvicorn main:app --reload --port 8765
```

In another terminal:
```bash
sqlite3 backend/trading_journal.db "PRAGMA table_info(trades);" | grep -E "trailed_stops|updated_at"
```
Expected: both columns listed.

Stop the dev server (Ctrl-C).

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/migrations.py backend/main.py
git commit -m "feat(schema): add trailed_stops and updated_at to trades table"
```

---

### Task 2: Implement `compute_rr` in `risk.py` (TDD)

**Files:**
- Create: `backend/tests/test_compute_rr.py`
- Modify: `backend/risk.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_compute_rr.py`:

```python
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
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
cd backend
source venv/bin/activate
pytest tests/test_compute_rr.py -v
```
Expected: `ImportError: cannot import name 'compute_rr' from 'risk'`.

- [ ] **Step 3: Implement `compute_rr`**

Append to `backend/risk.py`:

```python


def compute_rr(
    entry: Optional[float],
    exit_price: Optional[float],
    stop_loss: Optional[float],
    direction: Optional[str],
    status: Optional[str],
    trailed_stops: Optional[list],
) -> dict:
    """Compute classic R achieved + R locked at penultimate trail.

    Returns both as None if any required input is missing.
    Raises ValueError if entry_price == stop_loss (R distance would be zero).
    """
    if entry is None or exit_price is None or stop_loss is None or direction is None:
        return {"rr_achieved": None, "r_locked_at_penultimate_trail": None}

    if entry == stop_loss:
        raise ValueError("entry_price equals stop_loss; R distance is zero")

    dir_sign = 1 if direction.upper() == "LONG" else -1
    r_distance = abs(entry - stop_loss)

    rr_achieved = round((exit_price - entry) * dir_sign / r_distance, 2)

    r_locked = None
    if status == "win" and trailed_stops and len(trailed_stops) >= 2:
        penultimate = trailed_stops[-2].get("price")
        if penultimate is not None:
            r_locked = round((exit_price - penultimate) * dir_sign / r_distance, 2)

    return {"rr_achieved": rr_achieved, "r_locked_at_penultimate_trail": r_locked}
```

- [ ] **Step 4: Run tests, confirm they pass**

```bash
pytest tests/test_compute_rr.py -v
```
Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/risk.py backend/tests/test_compute_rr.py
git commit -m "feat(risk): add compute_rr with penultimate-trail locked-R"
```

---

### Task 3: Wire `compute_rr` into PATCH and close endpoints; bump `updated_at`

**Files:**
- Modify: `backend/main.py` — `update_trade` and `close_trade` handlers
- Create: `backend/tests/test_edit_endpoint.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_edit_endpoint.py`:

```python
"""Tests for PATCH /api/trades/{id} and POST /api/trades/{id}/close.

Uses FastAPI TestClient against an in-memory SQLite (the dev DB).
Assumes tests can be run sequentially without isolation; we use unique pair
strings to avoid bleed between tests.
"""
import json
import time
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def _create_open_trade(client, pair="BTCUSDT"):
    """Use POST /api/trades to create an open trade. (After Task 8 this is the only path.)
    Until Task 8, this fixture is replaced by retroactive POST below.
    """
    # Until Task 8 ships, use retroactive endpoint with status='entered' workaround.
    # Once Task 8 ships, replace this body with the new POST /api/trades shape.
    r = client.post("/api/trades", json={
        "pair": pair, "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": []
    })
    # The POST endpoint currently creates 'planned'; manually mark entered for now.
    # (After Task 8, the create call already returns 'entered' and this PATCH goes away.)
    tid = r.json()["id"]
    client.patch(f"/api/trades/{tid}", json={
        "status": "entered",
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    return tid


def test_patch_bumps_updated_at(client):
    tid = _create_open_trade(client, pair="EDIT1")
    before = client.get(f"/api/trades/{tid}").json()["updated_at"]
    time.sleep(1.1)  # ensure ISO timestamp differs
    client.patch(f"/api/trades/{tid}", json={"notes": "hello"})
    after = client.get(f"/api/trades/{tid}").json()["updated_at"]
    assert after is not None
    assert after != before


def test_patch_recalcs_rr_when_exit_changes(client):
    tid = _create_open_trade(client, pair="EDIT2")
    # Close it
    client.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 130.0,
    })
    before_rr = client.get(f"/api/trades/{tid}").json()["rr_achieved"]
    assert before_rr == 3.0  # (130-100)/|100-90|

    # Edit the exit price via PATCH
    client.patch(f"/api/trades/{tid}", json={"exit_price": 120.0})
    after_rr = client.get(f"/api/trades/{tid}").json()["rr_achieved"]
    assert after_rr == 2.0  # (120-100)/10


def test_patch_preserves_manual_pnl_override(client):
    tid = _create_open_trade(client, pair="EDIT3")
    client.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 130.0, "pnl": 12345.0,
    })
    assert client.get(f"/api/trades/{tid}").json()["pnl"] == 12345.0

    # PATCH that does NOT include pnl must keep the override
    client.patch(f"/api/trades/{tid}", json={"notes": "still 12345"})
    assert client.get(f"/api/trades/{tid}").json()["pnl"] == 12345.0


def test_patch_trailed_stops_sorted_by_at(client):
    tid = _create_open_trade(client, pair="EDIT4")
    client.patch(f"/api/trades/{tid}", json={
        "trailed_stops": [
            {"price": 120.0, "at": "2026-05-30T16:00:00Z"},
            {"price": 105.0, "at": "2026-05-30T14:00:00Z"},
            {"price": 115.0, "at": "2026-05-30T15:00:00Z"},
        ]
    })
    ts = client.get(f"/api/trades/{tid}").json()["trailed_stops"]
    assert [s["price"] for s in ts] == [105.0, 115.0, 120.0]


def test_close_recalcs_locked_r_with_trails(client):
    tid = _create_open_trade(client, pair="EDIT5")
    client.patch(f"/api/trades/{tid}", json={
        "trailed_stops": [
            {"price": 105.0, "at": "2026-05-30T14:00:00Z"},
            {"price": 115.0, "at": "2026-05-30T15:00:00Z"},
            {"price": 125.0, "at": "2026-05-30T16:00:00Z"},
        ]
    })
    client.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 135.0,
    })
    t = client.get(f"/api/trades/{tid}").json()
    assert t["rr_achieved"] == 3.5
    assert t["r_locked_at_penultimate_trail"] == 2.0
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
pytest backend/tests/test_edit_endpoint.py -v
```
Expected: failures on `updated_at` field not bumping, `r_locked_at_penultimate_trail` not present in response, trailed_stops sorting not enforced.

- [ ] **Step 3: Modify `update_trade` to bump `updated_at`, sort trails, recalc RR**

In `backend/main.py`, replace the body of `update_trade` (lines 558-595) with:

```python
@app.patch("/api/trades/{trade_id}")
def update_trade(trade_id: int, data: TradeUpdate):
    import traceback
    from risk import compute_risk, compute_rr
    try:
        existing = db_get_trade(trade_id)
        if not existing:
            raise HTTPException(404, "Trade not found")

        update_data = data.model_dump(exclude_unset=True)

        for key in ("emotions_entry", "emotions_exit", "mistake_tags", "confluences"):
            if key in update_data:
                update_data[key] = _tags_to_db(update_data[key] or [])
        if "partial_exits" in update_data:
            update_data["partial_exits"] = json.dumps(update_data["partial_exits"] or [])
        if "trailed_stops" in update_data:
            ts = update_data["trailed_stops"] or []
            ts_sorted = sorted(ts, key=lambda s: s.get("at", ""))
            update_data["trailed_stops"] = json.dumps(ts_sorted)
        if "rules_followed" in update_data and update_data["rules_followed"] is not None:
            update_data["rules_followed"] = int(update_data["rules_followed"])

        if update_data.get("status") in ("win", "loss", "breakeven", "skipped"):
            update_data["closed_at"] = datetime.utcnow()

        risk_keys = {"entry_price", "stop_loss", "position_size", "account_size"}
        if risk_keys & set(update_data.keys()):
            merged = {**(_parse_trade(existing) or {}), **update_data}
            risk = compute_risk(merged.get("entry_price"), merged.get("stop_loss"),
                                merged.get("position_size"), merged.get("account_size"))
            update_data["risk_dollars"] = risk["risk_dollars"]
            update_data["risk_percent"] = risk["risk_percent"]

        # Recompute RR if any RR-affecting field changed AND the trade is closed
        merged = {**(_parse_trade(existing) or {}), **update_data}
        # Use the merged trailed_stops (parsed) for compute_rr
        merged_ts = update_data.get("trailed_stops")
        if isinstance(merged_ts, str):
            try: merged_ts = json.loads(merged_ts)
            except: merged_ts = []
        elif merged_ts is None:
            merged_ts = merged.get("trailed_stops") or []
            if isinstance(merged_ts, str):
                try: merged_ts = json.loads(merged_ts)
                except: merged_ts = []
        rr_keys = {"entry_price", "exit_price", "stop_loss", "trailed_stops"}
        if (rr_keys & set(update_data.keys())) and merged.get("status") in ("win", "loss", "breakeven"):
            rr = compute_rr(
                entry=merged.get("entry_price"),
                exit_price=merged.get("exit_price"),
                stop_loss=merged.get("stop_loss"),
                direction=merged.get("direction"),
                status=merged.get("status"),
                trailed_stops=merged_ts,
            )
            update_data["rr_achieved"] = rr["rr_achieved"]
            # Note: r_locked_at_penultimate_trail is not stored — derived on response (see Step 4)

        update_data["updated_at"] = datetime.utcnow()

        row = db_update_trade(trade_id, update_data)
        return _parse_trade(row)
    except HTTPException:
        raise
    except Exception as e:
        print(f"UPDATE ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(500, str(e))
```

- [ ] **Step 4: Surface `r_locked_at_penultimate_trail` on every trade response**

In `backend/main.py`, in `_parse_trade` (returns dict), add right after `"rr_achieved": _f("rr_achieved"),`:

```python
        # Derived on read; not stored
        "r_locked_at_penultimate_trail": (lambda: None)(),  # placeholder, overwritten below
```

Then, just before `return {...}`, compute it:

```python
    # Compute r_locked_at_penultimate_trail derived from current trade state
    from risk import compute_rr as _compute_rr
    try:
        rr = _compute_rr(
            entry=_f("entry_price"),
            exit_price=_f("exit_price"),
            stop_loss=_f("stop_loss"),
            direction=row.get("direction"),
            status=row.get("status"),
            trailed_stops=ts if isinstance(ts, list) else [],
        )
        _r_locked = rr["r_locked_at_penultimate_trail"]
    except Exception:
        _r_locked = None
```

And in the dict, replace the placeholder line with:

```python
        "r_locked_at_penultimate_trail": _r_locked,
```

- [ ] **Step 5: Modify `close_trade` to recompute `rr_achieved` canonically**

In `backend/main.py`, in `close_trade` (lines 639-664), replace the function body with:

```python
@app.post("/api/trades/{trade_id}/close")
def close_trade(trade_id: int, data: TradeClose):
    from risk import compute_rr
    if data.status not in ("win", "loss", "breakeven"):
        raise HTTPException(400, "status must be win | loss | breakeven")
    existing = db_get_trade(trade_id)
    if not existing:
        raise HTTPException(404, "Trade not found")

    parsed = _parse_trade(existing)

    # Canonical RR recompute on close
    rr_achieved = data.rr_achieved
    try:
        rr = compute_rr(
            entry=parsed.get("entry_price"),
            exit_price=data.exit_price,
            stop_loss=parsed.get("stop_loss"),
            direction=parsed.get("direction"),
            status=data.status,
            trailed_stops=parsed.get("trailed_stops") or [],
        )
        if rr["rr_achieved"] is not None:
            rr_achieved = rr["rr_achieved"]
    except ValueError:
        pass  # entry == stop, leave RR alone

    update = {
        "status": data.status,
        "exit_price": data.exit_price,
        "pnl": data.pnl,
        "pnl_percent": data.pnl_percent,
        "rr_achieved": rr_achieved,
        "rules_followed": (None if data.rules_followed is None else int(data.rules_followed)),
        "mistake_tags": _tags_to_db(data.mistake_tags or []),
        "emotions_exit": _tags_to_db(data.emotions_exit or []),
        "feelings_exit": data.feelings_exit or "",
        "lessons": data.lessons or "",
        "chart_url": data.chart_url or "",
        "partial_exits": json.dumps(data.partial_exits or []),
        "mfe_r": data.mfe_r,
        "mae_r": data.mae_r,
        "closed_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    row = db_update_trade(trade_id, update)
    return _parse_trade(row)
```

- [ ] **Step 6: Add `trailed_stops` and `updated_at` to `TradeUpdate` Pydantic model**

In `backend/main.py`, in `TradeUpdate` (lines 418-447), add at the end:

```python
    trailed_stops: Optional[list[dict]] = None
```

(`updated_at` is server-only, no need to accept from clients.)

- [ ] **Step 7: Run tests**

```bash
pytest backend/tests/test_edit_endpoint.py -v
```
Expected: all 5 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/main.py backend/tests/test_edit_endpoint.py
git commit -m "feat(api): bump updated_at and recompute RR on PATCH + close"
```

---

### Task 4: Add `POST /api/trades/{id}/trails` endpoint (TDD)

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_trails.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_trails.py`:

```python
"""Tests for trail mutation endpoints."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def _make_entered_trade(client, pair="TRAILS1"):
    r = client.post("/api/trades", json={
        "pair": pair, "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": []
    })
    tid = r.json()["id"]
    client.patch(f"/api/trades/{tid}", json={
        "status": "entered",
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    return tid


def test_post_trail_appends(client):
    tid = _make_entered_trade(client, pair="TRAILS_A")
    r = client.post(f"/api/trades/{tid}/trails", json={"price": 95.0})
    assert r.status_code == 200
    ts = r.json()["trailed_stops"]
    assert len(ts) == 1
    assert ts[0]["price"] == 95.0
    assert "at" in ts[0]


def test_post_trail_keeps_chronological_order(client):
    tid = _make_entered_trade(client, pair="TRAILS_B")
    client.post(f"/api/trades/{tid}/trails", json={"price": 95.0})
    client.post(f"/api/trades/{tid}/trails", json={"price": 105.0})
    client.post(f"/api/trades/{tid}/trails", json={"price": 110.0, "note": "swing high"})
    ts = client.get(f"/api/trades/{tid}").json()["trailed_stops"]
    assert [s["price"] for s in ts] == [95.0, 105.0, 110.0]
    assert ts[2]["note"] == "swing high"


def test_post_trail_rejects_non_entered_trade(client):
    tid = _make_entered_trade(client, pair="TRAILS_C")
    client.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 120.0,
    })
    r = client.post(f"/api/trades/{tid}/trails", json={"price": 115.0})
    assert r.status_code == 400


def test_post_trail_404_on_missing(client):
    r = client.post("/api/trades/999999/trails", json={"price": 100.0})
    assert r.status_code == 404


def test_delete_trail_by_index(client):
    tid = _make_entered_trade(client, pair="TRAILS_D")
    client.post(f"/api/trades/{tid}/trails", json={"price": 95.0})
    client.post(f"/api/trades/{tid}/trails", json={"price": 105.0})
    r = client.delete(f"/api/trades/{tid}/trails/0")
    assert r.status_code == 200
    ts = r.json()["trailed_stops"]
    assert len(ts) == 1
    assert ts[0]["price"] == 105.0


def test_delete_trail_out_of_range(client):
    tid = _make_entered_trade(client, pair="TRAILS_E")
    client.post(f"/api/trades/{tid}/trails", json={"price": 95.0})
    r = client.delete(f"/api/trades/{tid}/trails/5")
    assert r.status_code == 400
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
pytest backend/tests/test_trails.py -v
```
Expected: 404s on all routes (endpoints don't exist).

- [ ] **Step 3: Add the Pydantic model and endpoints**

In `backend/main.py`, after the `TradeUpdate` class definition (around line 447), add:

```python
class TrailAppend(BaseModel):
    price: float
    note: Optional[str] = None
```

After the `close_trade` handler (around line 664), add:

```python
@app.post("/api/trades/{trade_id}/trails")
def append_trail(trade_id: int, data: TrailAppend):
    existing = db_get_trade(trade_id)
    if not existing:
        raise HTTPException(404, "Trade not found")
    parsed = _parse_trade(existing)
    if parsed.get("status") != "entered":
        raise HTTPException(400, "Trails can only be added to entered trades")
    current = parsed.get("trailed_stops") or []
    new_trail = {
        "price": data.price,
        "at": datetime.utcnow().isoformat() + "Z",
    }
    if data.note:
        new_trail["note"] = data.note
    current.append(new_trail)
    current.sort(key=lambda s: s.get("at", ""))
    row = db_update_trade(trade_id, {
        "trailed_stops": json.dumps(current),
        "updated_at": datetime.utcnow(),
    })
    return _parse_trade(row)


@app.delete("/api/trades/{trade_id}/trails/{index}")
def delete_trail(trade_id: int, index: int):
    existing = db_get_trade(trade_id)
    if not existing:
        raise HTTPException(404, "Trade not found")
    parsed = _parse_trade(existing)
    current = parsed.get("trailed_stops") or []
    if index < 0 or index >= len(current):
        raise HTTPException(400, f"Trail index {index} out of range (0..{len(current)-1})")
    del current[index]
    row = db_update_trade(trade_id, {
        "trailed_stops": json.dumps(current),
        "updated_at": datetime.utcnow(),
    })
    return _parse_trade(row)
```

- [ ] **Step 4: Run tests, confirm they pass**

```bash
pytest backend/tests/test_trails.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_trails.py
git commit -m "feat(api): add POST/DELETE trail endpoints"
```

---

### Task 5: Build `dashboard.py` module (`compute_dashboard`) — TDD

**Files:**
- Create: `backend/dashboard.py`
- Create: `backend/tests/test_dashboard_module.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_dashboard_module.py`:

```python
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
    out = compute_dashboard(trades, latest_snapshot_balance=None, today=date(2026, 6, 1))
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
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
pytest backend/tests/test_dashboard_module.py -v
```
Expected: `ModuleNotFoundError: No module named 'dashboard'`.

- [ ] **Step 3: Implement `compute_dashboard`**

Create `backend/dashboard.py`:

```python
"""Pure dashboard aggregation. No DB, no I/O."""
from datetime import datetime, date, timedelta
from calendar import monthrange
from typing import Optional


CLOSED_STATUSES = ("win", "loss", "breakeven")


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    # Accept ISO strings; trim sub-second precision/Z
    s2 = s.replace("Z", "").split(".")[0]
    try:
        return datetime.fromisoformat(s2).date()
    except Exception:
        return None


def _label_month(d: date) -> str:
    return d.strftime("%b %Y")


def _label_week(d: date) -> str:
    return f"Week of {d.strftime('%Y-%m-%d')}"


def _week_start(d: date) -> date:
    """Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def _months_back(today: date, n: int) -> list[date]:
    """List the first-of-month dates for the past n months (oldest first), inclusive of current."""
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def _days_in_month(d: date) -> int:
    return monthrange(d.year, d.month)[1]


def _split_trade_across_months(opened: date, closed: date, pnl: float) -> dict[tuple[int, int], float]:
    """Return {(year, month): pnl_share} for the trade, weighted by days held."""
    if opened > closed:
        opened, closed = closed, opened
    days_held = (closed - opened).days + 1
    out: dict[tuple[int, int], float] = {}
    cur = opened
    while cur <= closed:
        month_end = date(cur.year, cur.month, _days_in_month(cur))
        slice_end = min(month_end, closed)
        days_in_slice = (slice_end - cur).days + 1
        key = (cur.year, cur.month)
        out[key] = out.get(key, 0) + pnl * days_in_slice / days_held
        cur = slice_end + timedelta(days=1)
    return {k: round(v, 2) for k, v in out.items()}


def compute_dashboard(
    trades: list[dict],
    latest_snapshot_balance: Optional[float] = None,
    today: Optional[date] = None,
) -> dict:
    """Return the dashboard payload (see spec §4.1)."""
    if today is None:
        today = date.today()

    closed = [t for t in trades if t.get("status") in CLOSED_STATUSES]
    open_count = sum(1 for t in trades if t.get("status") == "entered")

    # --- monthly ---
    month_starts = _months_back(today, 12)
    monthly_close: dict[tuple[int, int], dict] = {
        (d.year, d.month): {"label": _label_month(d), "year": d.year, "month": d.month,
                            "pnl_close_date": 0, "pnl_split": 0,
                            "trades": 0, "wins": 0}
        for d in month_starts
    }
    for t in closed:
        cd = _parse_date(t.get("closed_at"))
        if cd is None:
            continue
        key = (cd.year, cd.month)
        if key in monthly_close:
            monthly_close[key]["pnl_close_date"] += t.get("pnl") or 0
            monthly_close[key]["trades"] += 1
            if t.get("status") == "win":
                monthly_close[key]["wins"] += 1
        # split attribution
        od = _parse_date(t.get("created_at"))
        if od is not None and (t.get("pnl") or 0) != 0:
            for (yr, mn), share in _split_trade_across_months(od, cd, t["pnl"]).items():
                if (yr, mn) in monthly_close:
                    monthly_close[(yr, mn)]["pnl_split"] += share

    monthly_list = []
    for d in month_starts:
        m = monthly_close[(d.year, d.month)]
        win_rate = round(m["wins"] / m["trades"], 2) if m["trades"] > 0 else 0
        monthly_list.append({
            "label": m["label"], "year": m["year"], "month": m["month"],
            "pnl_close_date": round(m["pnl_close_date"], 2),
            "pnl_split": round(m["pnl_split"], 2),
            "trades": m["trades"], "win_rate": win_rate,
        })

    # --- weekly (4 most recent ISO weeks) ---
    weekly_buckets: dict[date, dict] = {}
    for i in range(4):
        start = _week_start(today) - timedelta(weeks=i)
        iso_year, iso_week, _ = start.isocalendar()
        weekly_buckets[start] = {"label": _label_week(start), "iso_year": iso_year,
                                  "iso_week": iso_week, "pnl": 0, "trades": 0, "wins": 0}
    for t in closed:
        cd = _parse_date(t.get("closed_at"))
        if cd is None:
            continue
        ws = _week_start(cd)
        if ws in weekly_buckets:
            weekly_buckets[ws]["pnl"] += t.get("pnl") or 0
            weekly_buckets[ws]["trades"] += 1
            if t.get("status") == "win":
                weekly_buckets[ws]["wins"] += 1

    weekly_list = []
    for ws in sorted(weekly_buckets.keys()):
        w = weekly_buckets[ws]
        win_rate = round(w["wins"] / w["trades"], 2) if w["trades"] > 0 else 0
        weekly_list.append({
            "label": w["label"], "iso_year": w["iso_year"], "iso_week": w["iso_week"],
            "pnl": round(w["pnl"], 2), "trades": w["trades"], "win_rate": win_rate,
        })

    # --- daily_heatmap (trailing 90 days) ---
    heat: dict[str, dict] = {}
    for i in range(90):
        d = today - timedelta(days=89 - i)
        heat[d.isoformat()] = {"date": d.isoformat(), "pnl": 0, "trades": 0}
    for t in closed:
        cd = _parse_date(t.get("closed_at"))
        if cd is None:
            continue
        key = cd.isoformat()
        if key in heat:
            heat[key]["pnl"] += t.get("pnl") or 0
            heat[key]["trades"] += 1
    daily_heatmap = [{"date": k, "pnl": round(v["pnl"], 2), "trades": v["trades"]}
                     for k, v in sorted(heat.items())]

    # --- equity_curve (one point per closed trade, ordered) ---
    baseline = latest_snapshot_balance if latest_snapshot_balance is not None else 0
    closed_sorted = sorted(
        [t for t in closed if t.get("closed_at")],
        key=lambda t: t["closed_at"],
    )
    equity_curve = []
    running = baseline
    for t in closed_sorted:
        running += t.get("pnl") or 0
        equity_curve.append({
            "date": (_parse_date(t["closed_at"]) or date.today()).isoformat(),
            "cumulative_pnl": round(running, 2),
            "trade_id": t["id"],
        })

    # --- this_week / this_month / ytd ---
    this_week_start = _week_start(today)
    this_week = {"label": _label_week(this_week_start), "pnl": 0, "trades": 0, "wins": 0}
    this_month = {"label": _label_month(today), "pnl": 0, "trades": 0, "wins": 0}
    ytd = {"label": f"YTD {today.year}", "pnl": 0, "trades": 0, "wins": 0}

    for t in closed:
        cd = _parse_date(t.get("closed_at"))
        if cd is None:
            continue
        pnl = t.get("pnl") or 0
        is_win = t.get("status") == "win"
        if cd >= this_week_start and cd <= today:
            this_week["pnl"] += pnl; this_week["trades"] += 1; this_week["wins"] += int(is_win)
        if cd.year == today.year and cd.month == today.month:
            this_month["pnl"] += pnl; this_month["trades"] += 1; this_month["wins"] += int(is_win)
        if cd.year == today.year:
            ytd["pnl"] += pnl; ytd["trades"] += 1; ytd["wins"] += int(is_win)

    def _finalize(b):
        return {"label": b["label"], "pnl": round(b["pnl"], 2), "trades": b["trades"],
                "win_rate": round(b["wins"] / b["trades"], 2) if b["trades"] > 0 else 0}

    return {
        "this_week":  _finalize(this_week),
        "this_month": _finalize(this_month),
        "ytd":        _finalize(ytd),
        "open_trades": {"count": open_count},
        "monthly": monthly_list,
        "weekly": weekly_list,
        "daily_heatmap": daily_heatmap,
        "equity_curve": equity_curve,
    }
```

- [ ] **Step 4: Run tests, confirm they pass**

```bash
pytest backend/tests/test_dashboard_module.py -v
```
Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/dashboard.py backend/tests/test_dashboard_module.py
git commit -m "feat(dashboard): add compute_dashboard module"
```

---

### Task 6: Wire `GET /api/dashboard` endpoint

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_dashboard_endpoint.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_dashboard_endpoint.py`:

```python
"""Smoke test for GET /api/dashboard."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_dashboard_endpoint_returns_full_shape(client):
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    j = r.json()
    for key in ("this_week", "this_month", "ytd", "open_trades",
                "monthly", "weekly", "daily_heatmap", "equity_curve"):
        assert key in j, f"missing key: {key}"
    assert len(j["monthly"]) == 12
    assert len(j["weekly"]) == 4
    assert len(j["daily_heatmap"]) == 90
```

- [ ] **Step 2: Run test, confirm 404**

```bash
pytest backend/tests/test_dashboard_endpoint.py -v
```
Expected: 404 — endpoint does not exist.

- [ ] **Step 3: Add the endpoint**

In `backend/main.py`, after the analytics endpoint (around line 720), add:

```python
@app.get("/api/dashboard")
def get_dashboard():
    from dashboard import compute_dashboard

    # Load all trades (the dashboard windows the data itself)
    rows = db_list_trades(None, 100000)
    trades = [_parse_trade(r) for r in rows]

    # Latest snapshot balance for equity baseline
    if USE_TURSO:
        snap = fetch_one("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")
    else:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            row = conn.execute(_text("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")).mappings().first()
            snap = dict(row) if row else None

    baseline = float(snap["balance"]) if snap else None
    return compute_dashboard(trades, latest_snapshot_balance=baseline)
```

- [ ] **Step 4: Run test, confirm it passes**

```bash
pytest backend/tests/test_dashboard_endpoint.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_dashboard_endpoint.py
git commit -m "feat(api): add GET /api/dashboard endpoint"
```

---

### Task 7: Modify `POST /api/trades` to create `entered` directly; remove `/enter` and `/skip`

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_new_trade_endpoint.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_new_trade_endpoint.py`:

```python
"""Tests for the new POST /api/trades creation flow."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_post_trades_creates_entered_with_risk(client):
    r = client.post("/api/trades", json={
        "pair": "NEW1", "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    assert r.status_code == 200
    t = r.json()
    assert t["status"] == "entered"
    assert t["entry_price"] == 100.0
    assert t["risk_dollars"] == 10.0
    assert t["risk_percent"] == 1.0


def test_post_trades_rejects_without_required_fields(client):
    r = client.post("/api/trades", json={
        "pair": "NEW2", "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        # Missing entry_price, stop_loss, position_size, account_size
    })
    assert r.status_code == 422


def test_enter_endpoint_removed(client):
    # Create an entered trade then try to call /enter on it — should 404
    create = client.post("/api/trades", json={
        "pair": "NEW3", "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    tid = create.json()["id"]
    r = client.post(f"/api/trades/{tid}/enter", json={
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    assert r.status_code == 404  # route removed


def test_skip_endpoint_removed(client):
    create = client.post("/api/trades", json={
        "pair": "NEW4", "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    tid = create.json()["id"]
    r = client.post(f"/api/trades/{tid}/skip", json={"skip_reason": "x"})
    assert r.status_code == 404
```

- [ ] **Step 2: Run tests, confirm failures**

```bash
pytest backend/tests/test_new_trade_endpoint.py -v
```
Expected: failure — current POST takes plan-shaped input and creates `planned`, and /enter and /skip still exist.

- [ ] **Step 3: Replace the `TradeCreatePlan` model with `TradeEnterCreate`**

In `backend/main.py`, replace `class TradeCreatePlan` (lines 331-344) with:

```python
class TradeEnterCreate(BaseModel):
    pair: str
    direction: str
    timeframe: str
    strategy: str = "Zone Failure"
    setup_score: int
    verdict: str
    criteria_checked: list[str]
    notes: str = ""
    confluences: list[str] = []
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    position_size: float
    account_size: float
    entry_timing: Optional[str] = None
    emotions_entry: list[str] = []
    feelings_entry: str = ""
    chart_url: str = ""
```

- [ ] **Step 4: Rewrite the `create_trade` handler**

In `backend/main.py`, replace `create_trade` (lines 534-541) with:

```python
@app.post("/api/trades")
def create_trade(trade: TradeEnterCreate):
    from risk import compute_risk
    data = trade.model_dump()
    risk = compute_risk(data["entry_price"], data["stop_loss"],
                        data["position_size"], data["account_size"])
    db_payload = {
        "pair": data["pair"], "direction": data["direction"], "timeframe": data["timeframe"],
        "strategy": data["strategy"], "setup_score": data["setup_score"], "verdict": data["verdict"],
        "criteria_checked": json.dumps(data["criteria_checked"]),
        "notes": data["notes"],
        "confluences": _tags_to_db(data.get("confluences") or []),
        "status": "entered",
        "entry_price": data["entry_price"],
        "stop_loss": data["stop_loss"],
        "take_profit": data.get("take_profit"),
        "position_size": data["position_size"],
        "account_size": data["account_size"],
        "risk_dollars": risk["risk_dollars"],
        "risk_percent": risk["risk_percent"],
        "entry_timing": data.get("entry_timing"),
        "emotions_entry": _tags_to_db(data.get("emotions_entry") or []),
        "feelings_entry": data.get("feelings_entry", ""),
        "chart_url": data.get("chart_url", ""),
        "updated_at": datetime.utcnow(),
    }
    row = db_create_trade(db_payload)
    return _parse_trade(row)
```

- [ ] **Step 5: Remove the `enter_trade` and `skip_trade` handlers**

In `backend/main.py`, delete the entire `enter_trade` handler (around lines 598-621) and the entire `skip_trade` handler (around lines 624-636), including their `class TradeEnter` (around lines 347-355) and `class TradeSkip` (around lines 358-360) Pydantic models.

- [ ] **Step 6: Run tests, confirm they pass**

```bash
pytest backend/tests/test_new_trade_endpoint.py -v
```
Expected: all 4 tests PASS.

Also re-run existing tests that hit `_create_open_trade` helpers (`test_edit_endpoint.py`, `test_trails.py`):

```bash
pytest backend/tests/test_edit_endpoint.py backend/tests/test_trails.py -v
```
The helpers need updating to match the new POST shape — update them to pass `entry_price`, `stop_loss`, `position_size`, `account_size` directly to POST and remove the follow-up PATCH that marked entered.

Replace the `_create_open_trade` body in `test_edit_endpoint.py`:

```python
def _create_open_trade(client, pair="BTCUSDT"):
    r = client.post("/api/trades", json={
        "pair": pair, "direction": "LONG", "timeframe": "15m",
        "strategy": "Zone Failure", "setup_score": 80, "verdict": "A",
        "criteria_checked": [], "confluences": [],
        "entry_price": 100.0, "stop_loss": 90.0,
        "position_size": 1.0, "account_size": 1000.0,
    })
    return r.json()["id"]
```

Same change for `_make_entered_trade` in `test_trails.py`. Re-run:

```bash
pytest backend/tests/test_edit_endpoint.py backend/tests/test_trails.py -v
```
Expected: PASS.

- [ ] **Step 7: Run the full backend suite**

```bash
pytest backend/tests/ -v
```
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/main.py backend/tests/test_new_trade_endpoint.py backend/tests/test_edit_endpoint.py backend/tests/test_trails.py
git commit -m "feat(api): POST /api/trades now creates 'entered'; remove /enter and /skip"
```

---

## Phase B: Frontend foundation

### Task 8: Update `api.ts` types and methods

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Read the current file to understand the shape**

```bash
head -120 frontend/src/api.ts
```

(Just to get oriented — exact line numbers vary.)

- [ ] **Step 2: Replace types/methods**

In `frontend/src/api.ts`:

1. **Add new types** near the top:

```typescript
export interface TrailedStop {
  price: number;
  at: string;       // ISO timestamp
  note?: string;
}

export interface DashboardKpi {
  label: string;
  pnl: number;
  trades: number;
  win_rate: number;
}

export interface DashboardMonthly {
  label: string; year: number; month: number;
  pnl_close_date: number; pnl_split: number;
  trades: number; win_rate: number;
}

export interface DashboardWeekly {
  label: string; iso_year: number; iso_week: number;
  pnl: number; trades: number; win_rate: number;
}

export interface DashboardHeatCell { date: string; pnl: number; trades: number; }
export interface DashboardEquityPoint { date: string; cumulative_pnl: number; trade_id: number; }

export interface Dashboard {
  this_week: DashboardKpi;
  this_month: DashboardKpi;
  ytd: DashboardKpi;
  open_trades: { count: number };
  monthly: DashboardMonthly[];
  weekly: DashboardWeekly[];
  daily_heatmap: DashboardHeatCell[];
  equity_curve: DashboardEquityPoint[];
}
```

2. **Extend the `Trade` interface** to include `trailed_stops`, `updated_at`, and `r_locked_at_penultimate_trail`:

```typescript
// (inside the existing Trade interface — add these fields)
trailed_stops: TrailedStop[];
updated_at: string | null;
r_locked_at_penultimate_trail: number | null;
```

3. **Remove obsolete methods** from the `api` object: `enterTrade`, `skipTrade`, `createPlanTrade` (if separately defined). Also drop any types like `TradeCreatePlan`, `TradeEnterPayload`, `TradeSkipPayload`.

4. **Update `createTrade`** signature to accept the new payload shape:

```typescript
// Replace the old createTrade method
async createTrade(payload: {
  pair: string; direction: "LONG" | "SHORT"; timeframe: string;
  strategy: string; setup_score: number; verdict: string;
  criteria_checked: string[]; confluences: string[];
  entry_price: number; stop_loss: number;
  take_profit?: number | null;
  position_size: number; account_size: number;
  notes?: string;
  entry_timing?: string | null;
  emotions_entry?: string[]; feelings_entry?: string;
  chart_url?: string;
}): Promise<Trade> {
  const r = await fetch(`${API}/api/trades`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
},
```

5. **Add new dashboard and trail methods** at the end of the `api` object:

```typescript
async getDashboard(): Promise<Dashboard> {
  const r = await fetch(`${API}/api/dashboard`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
},

async addTrail(tradeId: number, price: number, note?: string): Promise<Trade> {
  const r = await fetch(`${API}/api/trades/${tradeId}/trails`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ price, note }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
},

async deleteTrail(tradeId: number, index: number): Promise<Trade> {
  const r = await fetch(`${API}/api/trades/${tradeId}/trails/${index}`, {
    method: "DELETE",
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
},
```

6. **Verify `updateTrade` exists and accepts `trailed_stops`**: extend its `Partial<Trade>` type or its payload to allow `trailed_stops: TrailedStop[]`.

- [ ] **Step 3: Type-check the project**

```bash
cd frontend
npm run build
```

Build will FAIL because old components still reference removed methods (`enterTrade`, `skipTrade`). That's expected — we'll fix them by deleting those components in Task 26. For now, **comment out the bodies of `PlanForm.tsx`, `EnterTradeForm.tsx`, `SkipTradeForm.tsx`, `CloseTradeForm.tsx`** to satisfy the typechecker until they're deleted in Task 26:

```typescript
// At the top of each of those four files, replace the entire file body with:
export default function _Disabled() { return null; }
```

Re-run `npm run build`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api.ts frontend/src/components/PlanForm.tsx frontend/src/components/EnterTradeForm.tsx frontend/src/components/SkipTradeForm.tsx frontend/src/components/CloseTradeForm.tsx
git commit -m "feat(api): add dashboard + trail types and methods; stub obsolete components"
```

---

### Task 9: Build `lib/tradingview.ts`

**Files:**
- Create: `frontend/src/lib/tradingview.ts`

- [ ] **Step 1: Create the file**

Create `frontend/src/lib/tradingview.ts`:

```typescript
/**
 * Pure helpers for TradingView URL/symbol parsing.
 * No DOM access. No side effects.
 */

/**
 * Convert a tradingview.com/x/HASH/ URL into the canonical PNG snapshot URL.
 * Returns null if the URL doesn't match the snapshot pattern.
 *
 * Examples that match:
 *   https://www.tradingview.com/x/abc123/
 *   https://www.tradingview.com/x/abc123
 *   tradingview.com/x/abc123?foo=bar
 */
export function parseTradingViewSnapshot(url: string): string | null {
  if (!url) return null;
  const m = url.match(/tradingview\.com\/x\/([A-Za-z0-9]+)/);
  return m ? `https://s3.tradingview.com/snapshots/x/${m[1]}.png` : null;
}

/**
 * Map the journal's timeframe codes to TradingView interval strings.
 * Unknown codes fall back to daily ("D").
 */
export function timeframeToInterval(tf: string): string {
  const map: Record<string, string> = {
    "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "2h": "120", "4h": "240", "6h": "360",
    "1d": "D", "3d": "3D", "1w": "W", "1M": "M",
  };
  return map[tf] ?? "D";
}

/**
 * Best-effort exchange-prefix the symbol for the TradingView widget.
 * If the pair already contains a colon (e.g. "BINANCE:BTCUSDT"), return as-is.
 * Otherwise assume crypto and prefix with BINANCE:.
 */
export function exchangePrefixedSymbol(pair: string): string {
  if (pair.includes(":")) return pair;
  return `BINANCE:${pair}`;
}
```

- [ ] **Step 2: Sanity-check in browser console**

(No vitest — manual check.) After the next `npm run build` (later tasks will do this), open dev tools and:

```js
import("/src/lib/tradingview.ts").then(m => {
  console.assert(m.parseTradingViewSnapshot("https://www.tradingview.com/x/abc123/") === "https://s3.tradingview.com/snapshots/x/abc123.png");
  console.assert(m.parseTradingViewSnapshot("https://google.com") === null);
  console.assert(m.timeframeToInterval("15m") === "15");
  console.assert(m.timeframeToInterval("zzz") === "D");
  console.assert(m.exchangePrefixedSymbol("BTCUSDT") === "BINANCE:BTCUSDT");
  console.assert(m.exchangePrefixedSymbol("NASDAQ:AAPL") === "NASDAQ:AAPL");
});
```

(This is a one-shot sanity check; not part of CI.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/tradingview.ts
git commit -m "feat(frontend): add tradingview URL/symbol helpers"
```

---

### Task 10: Build `lib/dashboard.ts`

**Files:**
- Create: `frontend/src/lib/dashboard.ts`

- [ ] **Step 1: Create the file**

Create `frontend/src/lib/dashboard.ts`:

```typescript
/**
 * Frontend-only helpers for the dashboard. The heavy math lives server-side
 * in backend/dashboard.py; this is just formatting & color helpers.
 */

export function formatCurrency(n: number): string {
  const abs = Math.abs(n);
  const formatted = abs.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: abs >= 100 ? 0 : 2,
  });
  return n < 0 ? `-$${formatted}` : `$${formatted}`;
}

export function formatPercent(n: number): string {
  return `${Math.round(n * 100)}%`;
}

/**
 * Heatmap cell color from a P&L value. Returns a CSS color from the project's
 * existing CSS-variable palette (--green, --red), with opacity scaled by magnitude.
 * Zero/missing days get a neutral gray (--bg2).
 */
export function heatColor(pnl: number, maxAbs: number): string {
  if (pnl === 0 || maxAbs === 0) return "var(--bg2)";
  const intensity = Math.min(1, Math.abs(pnl) / maxAbs);
  // Use rgba via CSS color-mix would be cleaner but not universal — use opacity layering
  // by wrapping in inline-style elsewhere. Here we just return the base color and let the
  // consumer apply opacity = intensity.
  return pnl > 0 ? "var(--green)" : "var(--red)";
}

export function maxAbsOf<T>(items: T[], fn: (t: T) => number): number {
  return items.reduce((m, t) => Math.max(m, Math.abs(fn(t))), 0);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/dashboard.ts
git commit -m "feat(frontend): add dashboard formatting helpers"
```

---

### Task 11: Build `ChartEmbed.tsx`

**Files:**
- Create: `frontend/src/components/ChartEmbed.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/ChartEmbed.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import { parseTradingViewSnapshot, timeframeToInterval, exchangePrefixedSymbol } from "../lib/tradingview";

interface Props {
  snapshotUrl: string;
  symbol: string;       // e.g. "BTCUSDT"
  timeframe: string;    // e.g. "15m"
}

export default function ChartEmbed({ snapshotUrl, symbol, timeframe }: Props) {
  const snapshotPng = parseTradingViewSnapshot(snapshotUrl || "");
  const [imgFailed, setImgFailed] = useState(false);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {snapshotPng && !imgFailed && (
        <div className="card" style={{ padding: 8 }}>
          <div className="text-xs text-2" style={{ marginBottom: 6 }}>Your snapshot at trade time</div>
          <a href={snapshotUrl} target="_blank" rel="noreferrer">
            <img
              src={snapshotPng}
              alt="TradingView snapshot"
              style={{ width: "100%", borderRadius: 4, display: "block" }}
              onError={() => setImgFailed(true)}
            />
          </a>
        </div>
      )}
      {snapshotUrl && (!snapshotPng || imgFailed) && (
        <a href={snapshotUrl} target="_blank" rel="noreferrer" className="text-sm">
          📈 Open chart ↗
        </a>
      )}
      <div className="card" style={{ padding: 8 }}>
        <div className="text-xs text-2" style={{ marginBottom: 6 }}>Live now</div>
        <LiveWidget symbol={symbol} timeframe={timeframe} />
      </div>
    </div>
  );
}

function LiveWidget({ symbol, timeframe }: { symbol: string; timeframe: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    // Clear any previous widget (component re-render)
    containerRef.current.innerHTML = "";
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: exchangePrefixedSymbol(symbol),
      interval: timeframeToInterval(timeframe),
      timezone: "Etc/UTC",
      theme: "dark",
      style: "1",
      locale: "en",
      hide_side_toolbar: false,
      allow_symbol_change: false,
      withdateranges: true,
      save_image: false,
    });
    containerRef.current.appendChild(script);
  }, [symbol, timeframe]);

  return (
    <div
      ref={containerRef}
      className="tradingview-widget-container"
      style={{ width: "100%", height: 400 }}
    />
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend
npm run build
```
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ChartEmbed.tsx
git commit -m "feat(ui): add ChartEmbed (snapshot image + live TradingView widget)"
```

---

### Task 12: Build `EditableField.tsx`

**Files:**
- Create: `frontend/src/components/EditableField.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/EditableField.tsx`:

```tsx
import { ChangeEvent } from "react";

interface Props {
  label: string;
  value: string | number | null | undefined;
  type?: "text" | "number" | "textarea";
  editing: boolean;
  onChange: (v: string) => void;
  width?: number | string;
  placeholder?: string;
}

/**
 * A simple label + (read-only display OR input) widget. Used heavily in
 * TradeDetailPage's edit mode to keep the markup uniform.
 */
export default function EditableField({
  label, value, type = "text", editing, onChange, width, placeholder,
}: Props) {
  const display = value === null || value === undefined || value === "" ? "—" : String(value);

  if (!editing) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <span className="text-xs text-2">{label}</span>
        <span className="text-sm">{display}</span>
      </div>
    );
  }

  const onInput = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(e.target.value);

  if (type === "textarea") {
    return (
      <label style={{ display: "flex", flexDirection: "column", gap: 2, width }}>
        <span className="text-xs text-2">{label}</span>
        <textarea
          className="input"
          value={value === null || value === undefined ? "" : String(value)}
          onChange={onInput}
          placeholder={placeholder}
          rows={3}
        />
      </label>
    );
  }

  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 2, width }}>
      <span className="text-xs text-2">{label}</span>
      <input
        className="input"
        type={type}
        value={value === null || value === undefined ? "" : String(value)}
        onChange={onInput}
        placeholder={placeholder}
      />
    </label>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/EditableField.tsx
git commit -m "feat(ui): add EditableField helper component"
```

---

## Phase C: Trade detail page

### Task 13: Build `TrailedStopsTable.tsx`

**Files:**
- Create: `frontend/src/components/TrailedStopsTable.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/TrailedStopsTable.tsx`:

```tsx
import { useState } from "react";
import { Trade, TrailedStop, api } from "../api";

interface Props {
  trade: Trade;
  onChange: (t: Trade) => void;
}

export default function TrailedStopsTable({ trade, onChange }: Props) {
  const [newPrice, setNewPrice] = useState("");
  const [newNote, setNewNote] = useState("");
  const [busy, setBusy] = useState(false);

  const trails = trade.trailed_stops || [];
  const penultimateIdx = trade.status === "win" && trails.length >= 2 ? trails.length - 2 : -1;

  const add = async () => {
    const price = parseFloat(newPrice);
    if (Number.isNaN(price)) return;
    setBusy(true);
    try {
      const updated = await api.addTrail(trade.id, price, newNote || undefined);
      onChange(updated);
      setNewPrice(""); setNewNote("");
    } finally { setBusy(false); }
  };

  const remove = async (idx: number) => {
    if (!confirm("Remove this trail?")) return;
    setBusy(true);
    try {
      const updated = await api.deleteTrail(trade.id, idx);
      onChange(updated);
    } finally { setBusy(false); }
  };

  return (
    <div className="card">
      <div className="flex between center" style={{ marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Trailed stops ({trails.length})</h3>
      </div>

      {trails.length === 0 ? (
        <div className="text-2 text-xs" style={{ marginBottom: 8 }}>No trails yet.</div>
      ) : (
        <table style={{ width: "100%", fontSize: 14, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left" }}>
              <th style={{ padding: "4px 8px" }}>#</th>
              <th style={{ padding: "4px 8px" }}>Price</th>
              <th style={{ padding: "4px 8px" }}>Time</th>
              <th style={{ padding: "4px 8px" }}>Note</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {trails.map((s: TrailedStop, idx: number) => {
              const isPenultimate = idx === penultimateIdx;
              return (
                <tr key={idx} style={{
                  background: isPenultimate ? "var(--yellow-bg, #fef3c7)" : "transparent",
                }}>
                  <td style={{ padding: "4px 8px" }}>{idx + 1}</td>
                  <td style={{ padding: "4px 8px" }}>{s.price}</td>
                  <td style={{ padding: "4px 8px" }} className="text-2 text-xs">
                    {new Date(s.at).toLocaleString()}
                  </td>
                  <td style={{ padding: "4px 8px" }}>{s.note ?? ""}</td>
                  <td style={{ padding: "4px 8px", textAlign: "right" }}>
                    <button className="btn btn-sm btn-ghost" disabled={busy} onClick={() => remove(idx)}>×</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {trade.status === "entered" && (
        <div className="flex gap-2 center" style={{ marginTop: 8 }}>
          <input
            className="input"
            type="number"
            placeholder="price"
            value={newPrice}
            onChange={e => setNewPrice(e.target.value)}
            style={{ width: 120 }}
          />
          <input
            className="input"
            type="text"
            placeholder="note (optional)"
            value={newNote}
            onChange={e => setNewNote(e.target.value)}
            style={{ flex: 1 }}
          />
          <button className="btn btn-sm btn-primary" disabled={busy || !newPrice} onClick={add}>
            + Add trail
          </button>
        </div>
      )}

      {penultimateIdx >= 0 && trade.r_locked_at_penultimate_trail != null && (
        <div className="text-xs text-2" style={{ marginTop: 8 }}>
          The highlighted row is the -1th trail. R locked here: <b>{trade.r_locked_at_penultimate_trail}R</b>.
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npm run build
```
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TrailedStopsTable.tsx
git commit -m "feat(ui): add TrailedStopsTable component"
```

---

### Task 14: Build `CloseTradePanel.tsx`

**Files:**
- Create: `frontend/src/components/CloseTradePanel.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/CloseTradePanel.tsx`:

```tsx
import { useState } from "react";
import { api, Trade } from "../api";

interface Props {
  trade: Trade;
  onClosed: (t: Trade) => void;
  onCancel: () => void;
}

type Status = "win" | "loss" | "breakeven";

export default function CloseTradePanel({ trade, onClosed, onCancel }: Props) {
  const [status, setStatus] = useState<Status>("win");
  const [exitPrice, setExitPrice] = useState("");
  const [pnl, setPnl] = useState("");
  const [mistakeTags, setMistakeTags] = useState("");
  const [emotionsExit, setEmotionsExit] = useState("");
  const [feelingsExit, setFeelingsExit] = useState("");
  const [lessons, setLessons] = useState("");
  const [rulesFollowed, setRulesFollowed] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const exit = parseFloat(exitPrice);
    if (Number.isNaN(exit)) { alert("exit_price required"); return; }
    setBusy(true);
    try {
      const r = await fetch(`/api/trades/${trade.id}/close`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status,
          exit_price: exit,
          pnl: pnl === "" ? null : parseFloat(pnl),
          rules_followed: rulesFollowed,
          mistake_tags: mistakeTags.split(",").map(s => s.trim()).filter(Boolean),
          emotions_exit: emotionsExit.split(",").map(s => s.trim()).filter(Boolean),
          feelings_exit: feelingsExit,
          lessons,
          chart_url: trade.chart_url || "",
          partial_exits: [],
        }),
      });
      const updated = await r.json();
      onClosed(updated);
    } finally { setBusy(false); }
  };

  return (
    <div className="card" style={{ borderLeft: "3px solid var(--blue)" }}>
      <h3 style={{ marginTop: 0 }}>Close trade</h3>
      <div className="flex gap-2 wrap" style={{ marginBottom: 8 }}>
        {(["win", "loss", "breakeven"] as Status[]).map(s => (
          <button key={s} className={`btn btn-sm ${status === s ? "btn-primary" : "btn-ghost"}`} onClick={() => setStatus(s)}>{s}</button>
        ))}
      </div>
      <div className="flex gap-2 wrap" style={{ marginBottom: 8 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span className="text-xs text-2">Exit price *</span>
          <input className="input" type="number" value={exitPrice} onChange={e => setExitPrice(e.target.value)} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span className="text-xs text-2">P&L (optional override)</span>
          <input className="input" type="number" value={pnl} onChange={e => setPnl(e.target.value)} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span className="text-xs text-2">Plan followed?</span>
          <div className="flex gap-1">
            {[true, false, null].map((v, i) => (
              <button key={i} className={`btn btn-sm ${rulesFollowed === v ? "btn-primary" : "btn-ghost"}`} onClick={() => setRulesFollowed(v)}>
                {v === true ? "Yes" : v === false ? "No" : "—"}
              </button>
            ))}
          </div>
        </label>
      </div>
      <label style={{ display: "block", marginBottom: 8 }}>
        <span className="text-xs text-2">Mistake tags (comma-separated)</span>
        <input className="input" type="text" value={mistakeTags} onChange={e => setMistakeTags(e.target.value)} style={{ width: "100%" }} />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        <span className="text-xs text-2">Emotions at exit (comma-separated)</span>
        <input className="input" type="text" value={emotionsExit} onChange={e => setEmotionsExit(e.target.value)} style={{ width: "100%" }} />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        <span className="text-xs text-2">Feelings at exit</span>
        <textarea className="input" rows={2} value={feelingsExit} onChange={e => setFeelingsExit(e.target.value)} style={{ width: "100%" }} />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        <span className="text-xs text-2">Lessons</span>
        <textarea className="input" rows={3} value={lessons} onChange={e => setLessons(e.target.value)} style={{ width: "100%" }} />
      </label>
      <div className="flex gap-2" style={{ marginTop: 8 }}>
        <button className="btn btn-primary" disabled={busy} onClick={submit}>Close trade</button>
        <button className="btn btn-ghost" disabled={busy} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npm run build
```
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CloseTradePanel.tsx
git commit -m "feat(ui): add CloseTradePanel inline form"
```

---

### Task 15: Build `TradeDetailPage.tsx` (view + edit modes)

**Files:**
- Create: `frontend/src/components/TradeDetailPage.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/TradeDetailPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, Trade } from "../api";
import ChartEmbed from "./ChartEmbed";
import TrailedStopsTable from "./TrailedStopsTable";
import CloseTradePanel from "./CloseTradePanel";
import EditableField from "./EditableField";

export default function TradeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [trade, setTrade] = useState<Trade | null>(null);
  const [editing, setEditing] = useState(false);
  const [closing, setClosing] = useState(false);
  const [draft, setDraft] = useState<Partial<Trade>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.getTrade(Number(id))
      .then(t => { if (!cancelled) { setTrade(t); setDraft(t); } })
      .catch(() => { if (!cancelled) navigate("/"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id, navigate]);

  if (loading) return <div className="text-2 text-sm">Loading…</div>;
  if (!trade) return null;

  const startEdit = () => { setDraft(trade); setEditing(true); };
  const cancelEdit = () => { setDraft(trade); setEditing(false); };
  const save = async () => {
    setBusy(true);
    try {
      const updated = await api.updateTrade(trade.id, draft);
      setTrade(updated);
      setDraft(updated);
      setEditing(false);
    } finally { setBusy(false); }
  };
  const remove = async () => {
    if (!confirm("Delete this trade permanently?")) return;
    await api.deleteTrade(trade.id);
    navigate("/");
  };

  const F = (label: string, key: keyof Trade, type: "text" | "number" | "textarea" = "text") => (
    <EditableField
      label={label}
      value={(editing ? draft[key] : trade[key]) as any}
      type={type}
      editing={editing}
      onChange={v => setDraft(d => ({ ...d, [key]: type === "number" ? (v === "" ? null : parseFloat(v)) : v }))}
    />
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div className="flex between center wrap">
        <div className="flex gap-2 center wrap">
          <button className="btn btn-ghost btn-sm" onClick={() => navigate("/")}>← Back</button>
          <span className="font-500">{trade.pair}</span>
          <span className={`tag ${trade.direction === "LONG" ? "tag-green" : "tag-red"}`}>{trade.direction}</span>
          <span className="tag tag-blue">{trade.timeframe}</span>
          <span className="tag tag-blue">{trade.strategy}</span>
          <span className={`tag ${
            trade.status === "win" ? "tag-green" :
            trade.status === "loss" ? "tag-red" :
            trade.status === "breakeven" ? "tag-yellow" : "tag-blue"
          }`}>{trade.status.toUpperCase()}</span>
        </div>
        <div className="flex gap-2">
          {editing ? (
            <>
              <button className="btn btn-primary btn-sm" disabled={busy} onClick={save}>Save</button>
              <button className="btn btn-ghost btn-sm" disabled={busy} onClick={cancelEdit}>Cancel</button>
            </>
          ) : (
            <>
              <button className="btn btn-ghost btn-sm" onClick={startEdit}>Edit</button>
              {trade.status === "entered" && !closing && (
                <button className="btn btn-primary btn-sm" onClick={() => setClosing(true)}>Close trade</button>
              )}
              <button className="btn btn-ghost btn-sm" style={{ color: "var(--red)" }} onClick={remove}>Delete</button>
            </>
          )}
        </div>
      </div>

      {/* Chart */}
      <ChartEmbed snapshotUrl={trade.chart_url || ""} symbol={trade.pair} timeframe={trade.timeframe} />

      {/* Numbers strip */}
      <div className="card">
        <div className="flex gap-4 wrap">
          {F("Entry", "entry_price", "number")}
          {F("Exit", "exit_price", "number")}
          {F("Original SL", "stop_loss", "number")}
          {F("TP", "take_profit", "number")}
          {F("Size", "position_size", "number")}
          {F("Account", "account_size", "number")}
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span className="text-xs text-2">Risk $</span>
            <span className="text-sm">{trade.risk_dollars ?? "—"}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span className="text-xs text-2">Risk %</span>
            <span className="text-sm">{trade.risk_percent ?? "—"}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span className="text-xs text-2">R achieved</span>
            <span className="text-sm">{trade.rr_achieved ?? "—"}</span>
          </div>
          {trade.r_locked_at_penultimate_trail != null && (
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span className="text-xs text-2">R locked (-1th trail)</span>
              <span className="text-sm">{trade.r_locked_at_penultimate_trail}</span>
            </div>
          )}
          {F("P&L", "pnl", "number")}
        </div>
      </div>

      {/* Trailed stops */}
      <TrailedStopsTable trade={trade} onChange={setTrade} />

      {/* Close panel (only when status is entered AND user clicked Close) */}
      {closing && trade.status === "entered" && (
        <CloseTradePanel trade={trade} onClosed={t => { setTrade(t); setClosing(false); }} onCancel={() => setClosing(false)} />
      )}

      {/* Plan/process */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Plan / Process</h3>
        <div className="flex gap-4 wrap">
          {F("Setup score", "setup_score", "number")}
          {F("Verdict", "verdict")}
        </div>
        {F("Notes", "notes", "textarea")}
        <div style={{ marginTop: 8 }}>
          <div className="text-xs text-2">Confluences</div>
          <div className="chip-row">
            {(trade.confluences || []).map(c => <span key={c} className="chip selected">{c.replace(/_/g, " ")}</span>)}
          </div>
        </div>
      </div>

      {/* Outcome */}
      {(["win", "loss", "breakeven"] as const).includes(trade.status as any) && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Outcome</h3>
          {F("Lessons", "lessons", "textarea")}
          {F("Feelings at exit", "feelings_exit", "textarea")}
          <div style={{ marginTop: 8 }}>
            <div className="text-xs text-2">Mistake tags</div>
            <div className="chip-row">
              {(trade.mistake_tags || []).map(c => <span key={c} className="chip selected">{c.replace(/_/g, " ")}</span>)}
            </div>
          </div>
        </div>
      )}

      {trade.updated_at && trade.updated_at !== trade.created_at && (
        <div className="text-xs text-2">Last edited: {new Date(trade.updated_at).toLocaleString()}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npm run build
```
Expected: PASS (assuming `api.getTrade`, `api.updateTrade`, `api.deleteTrade` exist; they should from current `api.ts`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TradeDetailPage.tsx
git commit -m "feat(ui): add TradeDetailPage with view + edit modes"
```

---

## Phase D: Dashboard

### Task 16: Install Recharts

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install recharts**

```bash
cd frontend
npm install recharts
```

- [ ] **Step 2: Verify it's listed**

```bash
grep recharts package.json
```
Expected: `"recharts": "^X.X.X"` line present in dependencies.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "build(deps): add recharts for dashboard charts"
```

---

### Task 17: Build `KPICard.tsx`

**Files:**
- Create: `frontend/src/components/KPICard.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/KPICard.tsx`:

```tsx
import { formatCurrency, formatPercent } from "../lib/dashboard";

interface Props {
  label: string;
  primary: number;
  trades: number;
  winRate: number;
  unit?: "$" | "count";
}

export default function KPICard({ label, primary, trades, winRate, unit = "$" }: Props) {
  const color = unit === "$" ? (primary > 0 ? "var(--green)" : primary < 0 ? "var(--red)" : "var(--text2)") : "var(--text)";
  const value = unit === "$" ? formatCurrency(primary) : primary.toString();
  return (
    <div className="card" style={{ minWidth: 160 }}>
      <div className="text-xs text-2">{label}</div>
      <div className="font-500" style={{ fontSize: 28, color, marginTop: 4 }}>{value}</div>
      {unit === "$" && (
        <div className="text-xs text-2" style={{ marginTop: 4 }}>
          {trades} trade{trades === 1 ? "" : "s"} · {formatPercent(winRate)} win
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/KPICard.tsx
git commit -m "feat(ui): add KPICard component"
```

---

### Task 18: Build `MonthlyBars.tsx`

**Files:**
- Create: `frontend/src/components/MonthlyBars.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/MonthlyBars.tsx`:

```tsx
import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { DashboardMonthly } from "../api";
import { formatCurrency } from "../lib/dashboard";

interface Props {
  data: DashboardMonthly[];
}

export default function MonthlyBars({ data }: Props) {
  const [mode, setMode] = useState<"close" | "split">("close");
  const key = mode === "close" ? "pnl_close_date" : "pnl_split";

  return (
    <div className="card">
      <div className="flex between center" style={{ marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Monthly P&L</h3>
        <div className="flex gap-1">
          <button
            className={`btn btn-sm ${mode === "close" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setMode("close")}
          >Close date</button>
          <button
            className={`btn btn-sm ${mode === "split" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setMode("split")}
          >Split by days</button>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(n) => formatCurrency(n)} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(v: number) => formatCurrency(v)}
            contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
          />
          <Bar dataKey={key}>
            {data.map((d, i) => (
              <Cell key={i} fill={(d as any)[key] >= 0 ? "var(--green)" : "var(--red)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/MonthlyBars.tsx
git commit -m "feat(ui): add MonthlyBars chart with close/split toggle"
```

---

### Task 19: Build `WeeklyBars.tsx`

**Files:**
- Create: `frontend/src/components/WeeklyBars.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/WeeklyBars.tsx`:

```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { DashboardWeekly } from "../api";
import { formatCurrency } from "../lib/dashboard";

export default function WeeklyBars({ data }: { data: DashboardWeekly[] }) {
  return (
    <div className="card">
      <h3 style={{ margin: 0, marginBottom: 8 }}>Weekly P&L (last 4)</h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data}>
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(n) => formatCurrency(n)} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(v: number) => formatCurrency(v)}
            contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
          />
          <Bar dataKey="pnl">
            {data.map((d, i) => (
              <Cell key={i} fill={d.pnl >= 0 ? "var(--green)" : "var(--red)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/WeeklyBars.tsx
git commit -m "feat(ui): add WeeklyBars chart"
```

---

### Task 20: Build `DailyHeatmap.tsx`

**Files:**
- Create: `frontend/src/components/DailyHeatmap.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/DailyHeatmap.tsx`:

```tsx
import { DashboardHeatCell } from "../api";
import { formatCurrency, maxAbsOf } from "../lib/dashboard";

export default function DailyHeatmap({ data }: { data: DashboardHeatCell[] }) {
  const maxAbs = maxAbsOf(data, d => d.pnl);
  // Render as 13 columns (weeks) × 7 rows (days). 90 days ≈ 13 weeks.
  const weeks: DashboardHeatCell[][] = [];
  for (let i = 0; i < data.length; i += 7) weeks.push(data.slice(i, i + 7));

  const colorFor = (pnl: number) => {
    if (pnl === 0 || maxAbs === 0) return "var(--bg2)";
    const intensity = Math.min(1, Math.abs(pnl) / maxAbs);
    const base = pnl > 0 ? "var(--green)" : "var(--red)";
    return base;
  };
  const opacityFor = (pnl: number) => {
    if (pnl === 0 || maxAbs === 0) return 1;
    return 0.3 + 0.7 * Math.min(1, Math.abs(pnl) / maxAbs);
  };

  return (
    <div className="card">
      <h3 style={{ margin: 0, marginBottom: 8 }}>Daily activity (90d)</h3>
      <div style={{ display: "flex", gap: 3 }}>
        {weeks.map((week, wi) => (
          <div key={wi} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {week.map((d) => (
              <div
                key={d.date}
                title={`${d.date}: ${formatCurrency(d.pnl)} · ${d.trades} trade${d.trades === 1 ? "" : "s"}`}
                style={{
                  width: 16, height: 16, borderRadius: 3,
                  background: colorFor(d.pnl),
                  opacity: opacityFor(d.pnl),
                }}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/DailyHeatmap.tsx
git commit -m "feat(ui): add DailyHeatmap 90-day calendar"
```

---

### Task 21: Build `EquityCurve.tsx`

**Files:**
- Create: `frontend/src/components/EquityCurve.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/EquityCurve.tsx`:

```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { DashboardEquityPoint } from "../api";
import { formatCurrency } from "../lib/dashboard";

export default function EquityCurve({ data }: { data: DashboardEquityPoint[] }) {
  if (data.length === 0) {
    return (
      <div className="card">
        <h3 style={{ margin: 0, marginBottom: 8 }}>Equity curve</h3>
        <div className="text-2 text-sm">No closed trades yet.</div>
      </div>
    );
  }
  return (
    <div className="card">
      <h3 style={{ margin: 0, marginBottom: 8 }}>Equity curve</h3>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(n) => formatCurrency(n)} tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
          <Tooltip
            formatter={(v: number) => formatCurrency(v)}
            contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
          />
          <Line type="monotone" dataKey="cumulative_pnl" stroke="var(--blue)" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/EquityCurve.tsx
git commit -m "feat(ui): add EquityCurve line chart"
```

---

### Task 22: Compose `Dashboard.tsx`

**Files:**
- Create: `frontend/src/components/Dashboard.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/Dashboard.tsx`:

```tsx
import { useEffect, useState } from "react";
import { api, Dashboard } from "../api";
import KPICard from "./KPICard";
import MonthlyBars from "./MonthlyBars";
import WeeklyBars from "./WeeklyBars";
import DailyHeatmap from "./DailyHeatmap";
import EquityCurve from "./EquityCurve";

export default function DashboardPage() {
  const [d, setD] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDashboard().then(setD).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-2 text-sm">Loading dashboard…</div>;
  if (!d) return <div className="text-2 text-sm">Dashboard unavailable.</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="flex gap-2 wrap">
        <KPICard label={d.this_week.label}  primary={d.this_week.pnl}  trades={d.this_week.trades}  winRate={d.this_week.win_rate} />
        <KPICard label={d.this_month.label} primary={d.this_month.pnl} trades={d.this_month.trades} winRate={d.this_month.win_rate} />
        <KPICard label={d.ytd.label}        primary={d.ytd.pnl}        trades={d.ytd.trades}        winRate={d.ytd.win_rate} />
        <KPICard label="Open trades" primary={d.open_trades.count} trades={0} winRate={0} unit="count" />
      </div>
      <EquityCurve data={d.equity_curve} />
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
        <MonthlyBars data={d.monthly} />
        <WeeklyBars data={d.weekly} />
      </div>
      <DailyHeatmap data={d.daily_heatmap} />
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npm run build
```
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Dashboard.tsx
git commit -m "feat(ui): compose Dashboard page"
```

---

## Phase E: Layout, rail, new-trade page

### Task 23: Build `TradeRail.tsx`

**Files:**
- Create: `frontend/src/components/TradeRail.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/TradeRail.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Trade } from "../api";

export default function TradeRail() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.listTrades().then(setTrades).finally(() => setLoading(false));
  }, []);

  const open   = trades.filter(t => t.status === "entered");
  const closed = trades.filter(t => ["win", "loss", "breakeven"].includes(t.status));

  return (
    <aside style={{
      width: 240, minWidth: 240, borderLeft: "1px solid var(--border)",
      padding: 12, overflowY: "auto", maxHeight: "calc(100vh - 64px)",
    }}>
      <Section title={`Open (${open.length})`} trades={open}   onClick={t => navigate(`/trade/${t.id}`)} />
      <div style={{ height: 16 }} />
      <Section title={`Closed (${closed.length})`} trades={closed} onClick={t => navigate(`/trade/${t.id}`)} />
      {loading && <div className="text-xs text-2" style={{ marginTop: 8 }}>Loading…</div>}
      {!loading && trades.length === 0 && (
        <div className="text-xs text-2" style={{ marginTop: 8 }}>No trades yet.</div>
      )}
    </aside>
  );
}

function Section({ title, trades, onClick }: { title: string; trades: Trade[]; onClick: (t: Trade) => void }) {
  return (
    <div>
      <div className="text-xs text-2" style={{ marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {trades.map(t => <Tile key={t.id} trade={t} onClick={() => onClick(t)} />)}
      </div>
    </div>
  );
}

function Tile({ trade, onClick }: { trade: Trade; onClick: () => void }) {
  const statusClass =
    trade.status === "win" ? "tag-green" :
    trade.status === "loss" ? "tag-red" :
    trade.status === "breakeven" ? "tag-yellow" : "tag-blue";
  return (
    <div className="card" style={{ padding: 8, cursor: "pointer" }} onClick={onClick}>
      <div className="flex between center" style={{ gap: 4 }}>
        <span className="font-500" style={{ fontSize: 13 }}>{trade.pair}</span>
        <span className={`tag ${statusClass}`} style={{ fontSize: 10 }}>{trade.status.toUpperCase()}</span>
      </div>
      <div className="text-xs text-2" style={{ marginTop: 4 }}>
        {trade.direction} · {trade.timeframe}
        {trade.pnl != null && <span> · {trade.pnl >= 0 ? "+" : ""}${trade.pnl}</span>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TradeRail.tsx
git commit -m "feat(ui): add TradeRail sidebar"
```

---

### Task 24: Build `NewTradePage.tsx`

**Files:**
- Create: `frontend/src/components/NewTradePage.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/NewTradePage.tsx`:

```tsx
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";

export default function NewTradePage() {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const isRetro = search.get("mode") === "retro";

  const [pair, setPair] = useState("");
  const [direction, setDirection] = useState<"LONG" | "SHORT">("LONG");
  const [timeframe, setTimeframe] = useState("15m");
  const [strategy, setStrategy] = useState("Zone Failure");
  const [setupScore, setSetupScore] = useState("80");
  const [verdict, setVerdict] = useState("A");
  const [entryPrice, setEntryPrice] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [positionSize, setPositionSize] = useState("");
  const [accountSize, setAccountSize] = useState("");
  const [notes, setNotes] = useState("");
  const [chartUrl, setChartUrl] = useState("");
  const [busy, setBusy] = useState(false);

  // Retro extras
  const [exitPrice, setExitPrice] = useState("");
  const [status, setStatus] = useState<"win" | "loss" | "breakeven">("win");
  const [pnl, setPnl] = useState("");

  const submit = async () => {
    setBusy(true);
    try {
      if (isRetro) {
        const r = await fetch(`/api/trades/retroactive`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pair, direction, timeframe, strategy,
            setup_score: parseInt(setupScore) || 0, verdict,
            criteria_checked: [], confluences: [], notes,
            entry_price: parseFloat(entryPrice), stop_loss: parseFloat(stopLoss),
            take_profit: takeProfit === "" ? null : parseFloat(takeProfit),
            position_size: positionSize === "" ? null : parseFloat(positionSize),
            account_size: accountSize === "" ? null : parseFloat(accountSize),
            status, exit_price: parseFloat(exitPrice),
            pnl: pnl === "" ? null : parseFloat(pnl),
            chart_url: chartUrl,
          }),
        });
        const t = await r.json();
        navigate(`/trade/${t.id}`);
      } else {
        const t = await api.createTrade({
          pair, direction, timeframe, strategy,
          setup_score: parseInt(setupScore) || 0, verdict,
          criteria_checked: [], confluences: [], notes,
          entry_price: parseFloat(entryPrice), stop_loss: parseFloat(stopLoss),
          take_profit: takeProfit === "" ? null : parseFloat(takeProfit),
          position_size: parseFloat(positionSize),
          account_size: parseFloat(accountSize),
          chart_url: chartUrl,
        });
        navigate(`/trade/${t.id}`);
      }
    } finally { setBusy(false); }
  };

  return (
    <div className="card" style={{ maxWidth: 700 }}>
      <h2 style={{ marginTop: 0 }}>{isRetro ? "Log closed trade" : "New trade"}</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <Field label="Pair" value={pair} onChange={setPair} />
        <Field label="Direction" value={direction} onChange={v => setDirection(v as any)} />
        <Field label="Timeframe" value={timeframe} onChange={setTimeframe} />
        <Field label="Strategy" value={strategy} onChange={setStrategy} />
        <Field label="Setup score" value={setupScore} onChange={setSetupScore} type="number" />
        <Field label="Verdict" value={verdict} onChange={setVerdict} />
        <Field label="Entry price" value={entryPrice} onChange={setEntryPrice} type="number" />
        <Field label="Stop loss" value={stopLoss} onChange={setStopLoss} type="number" />
        <Field label="Take profit (opt)" value={takeProfit} onChange={setTakeProfit} type="number" />
        <Field label="Position size" value={positionSize} onChange={setPositionSize} type="number" />
        <Field label="Account size" value={accountSize} onChange={setAccountSize} type="number" />
        <Field label="Chart URL (opt)" value={chartUrl} onChange={setChartUrl} />
      </div>
      {isRetro && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginTop: 8 }}>
          <Field label="Status" value={status} onChange={v => setStatus(v as any)} />
          <Field label="Exit price" value={exitPrice} onChange={setExitPrice} type="number" />
          <Field label="P&L" value={pnl} onChange={setPnl} type="number" />
        </div>
      )}
      <label style={{ display: "block", marginTop: 8 }}>
        <span className="text-xs text-2">Notes</span>
        <textarea className="input" rows={3} value={notes} onChange={e => setNotes(e.target.value)} style={{ width: "100%" }} />
      </label>
      <div className="flex gap-2" style={{ marginTop: 12 }}>
        <button className="btn btn-primary" disabled={busy || !pair} onClick={submit}>
          {isRetro ? "Log trade" : "Create trade"}
        </button>
        <button className="btn btn-ghost" onClick={() => navigate("/")}>Cancel</button>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span className="text-xs text-2">{label}</span>
      <input className="input" type={type} value={value} onChange={e => onChange(e.target.value)} />
    </label>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npm run build
```
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/NewTradePage.tsx
git commit -m "feat(ui): add NewTradePage form"
```

---

### Task 25: Rewrite `main.tsx` (route map + layout shell)

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/index.css` (small additions)

- [ ] **Step 1: Replace `main.tsx`**

Overwrite `frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, NavLink, Navigate, Outlet, Link } from "react-router-dom";
import DashboardPage from "./components/Dashboard";
import TradeDetailPage from "./components/TradeDetailPage";
import NewTradePage from "./components/NewTradePage";
import TradeRail from "./components/TradeRail";
import Review from "./components/Review";
import "./index.css";

function Shell() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="nav">
          <h1 className="nav-title">Trading Journal</h1>
          <div className="nav-links">
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/review">Review</NavLink>
            <Link to="/trade/new" className="btn btn-sm btn-primary">+ New Trade</Link>
            <Link to="/trade/new?mode=retro" className="btn btn-sm btn-ghost">Log retro</Link>
          </div>
        </nav>
        <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
          <main className="main" style={{ flex: 1, padding: 16, overflowY: "auto" }}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/trade/new" element={<NewTradePage />} />
              <Route path="/trade/:id" element={<TradeDetailPage />} />
              <Route path="/review" element={<Review />} />
              <Route path="/plan" element={<Navigate to="/" replace />} />
              <Route path="/trades" element={<Navigate to="/" replace />} />
              <Route path="/analytics" element={<Navigate to="/review" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <TradeRail />
        </div>
      </div>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Shell />
  </React.StrictMode>
);
```

- [ ] **Step 2: Add minor CSS for the rail-friendly layout**

Append to `frontend/src/index.css`:

```css
/* Layout: app fills viewport; nav top, content row below */
.app { display: flex; flex-direction: column; height: 100vh; }
.nav { flex: 0 0 auto; }
.main { min-width: 0; }

/* Mobile: stack the rail below the main */
@media (max-width: 900px) {
  .app > div[style*="display: flex"] { flex-direction: column; }
  aside { width: 100% !important; min-width: 0 !important; border-left: none !important; border-top: 1px solid var(--border); }
}
```

- [ ] **Step 3: Type-check + run dev server**

```bash
cd frontend
npm run build
```
Expected: PASS.

Run dev server and visit `http://localhost:5173`:
```bash
npm run dev
```

You should see:
- Top nav with Dashboard / Review / + New Trade / Log retro
- Dashboard content with KPI cards, equity curve, monthly + weekly bars, heatmap
- Right rail with Open / Closed sections (may be empty)

Stop dev server (Ctrl-C).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.tsx frontend/src/index.css
git commit -m "feat(ui): new route map and layout shell with right-side TradeRail"
```

---

### Task 26: Delete obsolete components

**Files:**
- Delete: `frontend/src/components/PlanForm.tsx`
- Delete: `frontend/src/components/SkipTradeForm.tsx`
- Delete: `frontend/src/components/TradeList.tsx`
- Delete: `frontend/src/components/TradeDetail.tsx`
- Delete: `frontend/src/components/EnterTradeForm.tsx`
- Delete: `frontend/src/components/CloseTradeForm.tsx`

- [ ] **Step 1: Verify nothing imports them**

```bash
cd frontend
grep -r "PlanForm\|SkipTradeForm\|EnterTradeForm\|CloseTradeForm\|TradeList\|TradeDetail" src/ --include="*.ts" --include="*.tsx" | grep -v "components/"
```
Expected: empty (after `main.tsx` was rewritten in Task 25, no other file should reference these).

- [ ] **Step 2: Delete the files**

```bash
rm src/components/PlanForm.tsx
rm src/components/SkipTradeForm.tsx
rm src/components/EnterTradeForm.tsx
rm src/components/CloseTradeForm.tsx
rm src/components/TradeList.tsx
rm src/components/TradeDetail.tsx
```

- [ ] **Step 3: Type-check**

```bash
npm run build
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git rm src/components/PlanForm.tsx src/components/SkipTradeForm.tsx src/components/EnterTradeForm.tsx src/components/CloseTradeForm.tsx src/components/TradeList.tsx src/components/TradeDetail.tsx
git commit -m "chore(ui): remove obsolete plan/enter/skip/list/detail components"
```

---

## Phase F: Verification

### Task 27: End-to-end manual walkthrough

**Files:** none (manual verification + final commit).

- [ ] **Step 1: Run backend**

```bash
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload --port 8000
```

Verify the migration ran cleanly:
```bash
sqlite3 backend/trading_journal.db "PRAGMA table_info(trades);" | grep -E "trailed_stops|updated_at"
```
Expected: both columns present.

Verify the dashboard endpoint works:
```bash
curl -s http://localhost:8000/api/dashboard | python -m json.tool | head -40
```
Expected: a JSON object with the 8 top-level keys from the spec.

- [ ] **Step 2: Run frontend dev server**

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`.

- [ ] **Step 3: Manual flow check**

Walk through:

1. **Dashboard loads** at `/` with KPI cards, equity curve panel, monthly + weekly bars, heatmap.
2. **+ New Trade** → fill `pair=BTCUSDT direction=LONG timeframe=15m strategy="Zone Failure" setup_score=80 verdict=A entry_price=100 stop_loss=90 position_size=1 account_size=1000`, leave others blank, **Create trade**.
3. Navigated to `/trade/<id>`. Verify:
   - Header shows pair/direction/timeframe + ENTERED badge
   - TradingView live widget renders (with `BINANCE:BTCUSDT` on `15m`)
   - Trailed stops table shows empty + "Add trail" form
4. **Add trail price=95**, hit + Add trail. Row appears with timestamp.
5. **Add trail price=105**, then **price=115**. Three rows in the table.
6. **Close trade** → choose **win**, exit_price=130, submit. Status flips to WIN; numbers strip shows R achieved ≈ 3.0 and R locked at -1th ≈ 1.5; the row at index 1 (price=105) is highlighted yellow.
7. **Edit** the trade → change exit_price to 120, save. Page refreshes; R achieved updates to 2.0.
8. **Back** → Dashboard reflects the new closed trade in heatmap/KPIs.
9. **Right rail** shows the closed BTCUSDT tile. Click it → loads the same detail page.
10. **Set chart_url** in Edit mode to a real `https://www.tradingview.com/x/.../` snapshot URL → save → confirm snapshot image renders above the live widget.
11. Visit `/plan` and `/trades` → should redirect to `/`.

If everything passes, you're done.

- [ ] **Step 4: Run full backend test suite to be sure nothing regressed**

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```
Expected: all PASS.

- [ ] **Step 5: Final type-check / build**

```bash
cd frontend
npm run build
```
Expected: PASS, dist/ produced.

- [ ] **Step 6: Tag the work as done**

```bash
git log --oneline -30  # eyeball the trail of commits
git status              # should be clean
```
