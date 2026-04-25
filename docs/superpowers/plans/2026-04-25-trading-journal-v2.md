# Trading Journal v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the trading journal into a Plan/Execution/Result/Mindset workflow with multi-strategy support, mistake/emotion tagging, risk discipline tracking, and review tooling.

**Spec:** `docs/superpowers/specs/2026-04-25-trading-journal-v2-design.md`

**Architecture:** Backend remains FastAPI + SQLite/Turso. New `db/` package separates Turso and SQLAlchemy backends behind a uniform interface. Schema migrations are idempotent ALTER TABLE statements run at startup. Frontend gets three tabs (Plan / Trades / Review) and a Trade Detail drawer with three accordion sections (Plan / Execution / Result), plus reusable TagChips and PartialExits components.

**Tech Stack:** FastAPI 0.115 · SQLAlchemy 2.0 · Turso HTTP API · Pydantic 2.9 · React 18 · TypeScript · Vite

**Working directory:** `trading-journal/` (separate git repo).

---

## Phase 0 — Setup

### Task 0: Create a feature branch and confirm test infrastructure

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Create branch**

```bash
cd trading-journal
git checkout -b v2-journal
```

- [ ] **Step 2: Add pytest to requirements**

Open `backend/requirements.txt` and add:

```
fastapi==0.115.0
uvicorn==0.30.6
sqlalchemy==2.0.35
pydantic==2.9.2
python-dateutil==2.9.0
requests
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 3: Install in venv**

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 4: Confirm pytest works**

```bash
pytest --version
```

Expected: `pytest 8.3.3`

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add pytest and httpx to backend requirements"
```

---

## Phase 1 — Backend foundation

### Task 1: Pure risk-calculation helper (TDD)

**Files:**
- Create: `backend/risk.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_risk.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create empty package files**

```bash
mkdir -p backend/tests
touch backend/tests/__init__.py
```

Create `backend/tests/conftest.py`:

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
```

- [ ] **Step 2: Write failing tests**

Create `backend/tests/test_risk.py`:

```python
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
```

- [ ] **Step 3: Run tests — expect failures**

```bash
cd backend && pytest tests/test_risk.py -v
```

Expected: 5 errors with `ModuleNotFoundError: No module named 'risk'`.

- [ ] **Step 4: Implement**

Create `backend/risk.py`:

```python
"""Pure risk calculation. No DB, no I/O."""
from typing import Optional


def compute_risk(
    entry: Optional[float],
    stop: Optional[float],
    position_size: Optional[float],
    account_size: Optional[float],
) -> dict:
    """Returns {risk_dollars, risk_percent}, both None if any required input is missing."""
    if entry is None or stop is None or position_size is None or account_size is None:
        return {"risk_dollars": None, "risk_percent": None}

    risk_per_unit = abs(entry - stop)
    risk_dollars = round(risk_per_unit * position_size, 4)

    if account_size == 0:
        return {"risk_dollars": risk_dollars, "risk_percent": None}

    risk_percent = round((risk_dollars / account_size) * 100, 4)
    return {"risk_dollars": risk_dollars, "risk_percent": risk_percent}
```

- [ ] **Step 5: Run tests — expect pass**

```bash
pytest tests/test_risk.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/risk.py backend/tests/
git commit -m "feat(backend): add pure risk calc helper with tests"
```

---

### Task 2: Migration system + new tables

**Files:**
- Create: `backend/migrations.py`
- Create: `backend/tests/test_migrations.py`
- Modify: `backend/turso_db.py` (extend `init_tables`)

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_migrations.py`:

```python
import os
import sqlite3
import pytest

# Use a temp SQLite DB and the same SQL migrations the production code runs.
from migrations import V2_ALTERS, ZONE_FAILURE_CRITERIA, ZONE_FAILURE_CORE


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "test.db"
    c = sqlite3.connect(db)
    # Seed with v1 schema
    c.executescript("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT NOT NULL, direction TEXT NOT NULL, timeframe TEXT NOT NULL,
            setup_score INTEGER NOT NULL, verdict TEXT NOT NULL,
            criteria_checked TEXT NOT NULL, notes TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            entry_price REAL, exit_price REAL, stop_loss REAL, take_profit REAL,
            pnl REAL, pnl_percent REAL, rr_achieved REAL,
            lessons TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            closed_at TEXT
        );
    """)
    c.commit()
    yield c
    c.close()


def _apply_alters(conn):
    for sql in V2_ALTERS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise
    conn.commit()


def test_alters_add_all_v2_columns(conn):
    _apply_alters(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(trades)").fetchall()}
    expected_new = {
        "strategy", "planned_entry", "planned_stop", "planned_target", "planned_rr",
        "retroactive", "position_size", "account_size", "risk_dollars", "risk_percent",
        "entry_timing", "emotions_entry", "feelings_entry", "skip_reason",
        "partial_exits", "rules_followed", "mistake_tags", "emotions_exit",
        "feelings_exit", "chart_url",
    }
    assert expected_new.issubset(cols)


def test_alters_are_idempotent(conn):
    _apply_alters(conn)
    _apply_alters(conn)  # second run must not raise


def test_zone_failure_criteria_has_11_items():
    assert len(ZONE_FAILURE_CRITERIA) == 11
    assert ZONE_FAILURE_CORE == ["trend", "zone", "signal", "failure"]
```

- [ ] **Step 2: Run — expect failure**

```bash
pytest tests/test_migrations.py -v
```

Expected: `ModuleNotFoundError: No module named 'migrations'`.

- [ ] **Step 3: Implement**

Create `backend/migrations.py`:

```python
"""Idempotent schema migrations. Run at startup."""
import json

ZONE_FAILURE_CRITERIA = [
    {"id": "trend",   "label": "Trade is in direction of the overall trend", "points": 20, "category": "Core",    "description": "Downtrend = only short setups, Uptrend = only long setups"},
    {"id": "zone",    "label": "Pattern formed at a KEY zone (S/R, trendline, EMA)", "points": 15, "category": "Core",    "description": "Not in mid-range / no man's land"},
    {"id": "signal",  "label": "Signal candle present (Hammer / Hanging Man)", "points": 15, "category": "Core",    "description": "The trap candle that baits traders the wrong way"},
    {"id": "failure", "label": "Next candle is solid body AGAINST the signal candle", "points": 20, "category": "Core",    "description": "Solid red after hammer = SHORT | Solid green after hanging man = LONG"},
    {"id": "body",    "label": "Failure candle has large real body (>60% of total range)", "points": 5, "category": "Quality", "description": "Shows conviction, not a weak doji"},
    {"id": "wick",    "label": "Signal candle wick is 2x+ the body", "points": 5, "category": "Quality", "description": "Shows deep rejection that trapped more traders"},
    {"id": "stop",    "label": "Stop placed beyond signal candle wick (clear invalidation)", "points": 5, "category": "Risk",    "description": "If price goes past the trap wick, thesis is wrong"},
    {"id": "rr",      "label": "R:R is at least 1:2 to next zone", "points": 5, "category": "Risk",    "description": "Target must be at least 2x your stop distance"},
    {"id": "htf",     "label": "Higher timeframe structure agrees", "points": 5, "category": "Quality", "description": "4H setup confirmed by Daily trend direction"},
    {"id": "macro",   "label": "No major news in next 4 hours", "points": 3, "category": "Timing",  "description": "Avoid FOMC, NFP, BOJ etc within 4 hours"},
    {"id": "volume",  "label": "Failure candle shows increased volume/momentum", "points": 2, "category": "Quality", "description": "Trapped traders exiting = visible momentum"},
]
ZONE_FAILURE_CORE = ["trend", "zone", "signal", "failure"]

V2_ALTERS = [
    "ALTER TABLE trades ADD COLUMN strategy TEXT NOT NULL DEFAULT 'Zone Failure'",
    "ALTER TABLE trades ADD COLUMN planned_entry REAL",
    "ALTER TABLE trades ADD COLUMN planned_stop REAL",
    "ALTER TABLE trades ADD COLUMN planned_target REAL",
    "ALTER TABLE trades ADD COLUMN planned_rr REAL",
    "ALTER TABLE trades ADD COLUMN retroactive INTEGER DEFAULT 0",
    "ALTER TABLE trades ADD COLUMN position_size REAL",
    "ALTER TABLE trades ADD COLUMN account_size REAL",
    "ALTER TABLE trades ADD COLUMN risk_dollars REAL",
    "ALTER TABLE trades ADD COLUMN risk_percent REAL",
    "ALTER TABLE trades ADD COLUMN entry_timing TEXT",
    "ALTER TABLE trades ADD COLUMN emotions_entry TEXT DEFAULT ','",
    "ALTER TABLE trades ADD COLUMN feelings_entry TEXT DEFAULT ''",
    "ALTER TABLE trades ADD COLUMN skip_reason TEXT DEFAULT ''",
    "ALTER TABLE trades ADD COLUMN partial_exits TEXT DEFAULT '[]'",
    "ALTER TABLE trades ADD COLUMN rules_followed INTEGER",
    "ALTER TABLE trades ADD COLUMN mistake_tags TEXT DEFAULT ','",
    "ALTER TABLE trades ADD COLUMN emotions_exit TEXT DEFAULT ','",
    "ALTER TABLE trades ADD COLUMN feelings_exit TEXT DEFAULT ''",
    "ALTER TABLE trades ADD COLUMN chart_url TEXT DEFAULT ''",
]

NEW_TABLES = [
    """CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        criteria TEXT NOT NULL,
        is_core_required TEXT DEFAULT '[]',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS account_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        balance REAL NOT NULL,
        recorded_at TEXT DEFAULT (datetime('now')),
        note TEXT DEFAULT ''
    )""",
    """CREATE TABLE IF NOT EXISTS review_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period_type TEXT NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        notes TEXT NOT NULL,
        stats_snapshot TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS _migrations (
        name TEXT PRIMARY KEY,
        applied_at TEXT DEFAULT (datetime('now'))
    )""",
]


def run_migrations(execute_fn, fetch_one_fn):
    """Run all idempotent migrations. `execute_fn(sql, args=None)` and `fetch_one_fn(sql, args=None)` are passed in so this works for both Turso HTTP and SQLAlchemy."""
    # 1. Create new tables
    for sql in NEW_TABLES:
        execute_fn(sql)

    # 2. ALTERs (ignore duplicate-column errors)
    for sql in V2_ALTERS:
        try:
            execute_fn(sql)
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise

    # 3. Seed Zone Failure strategy if empty
    row = fetch_one_fn("SELECT COUNT(*) AS c FROM strategies")
    if int(row["c"]) == 0:
        execute_fn(
            "INSERT INTO strategies (name, criteria, is_core_required) VALUES (?, ?, ?)",
            ["Zone Failure", json.dumps(ZONE_FAILURE_CRITERIA), json.dumps(ZONE_FAILURE_CORE)],
        )

    # 4. One-time status backfill
    already = fetch_one_fn("SELECT name FROM _migrations WHERE name = ?", ["v2_status_backfill"])
    if not already:
        # Open trades with entry_price -> entered, retroactive=1
        execute_fn(
            "UPDATE trades SET status='entered', retroactive=1 WHERE status='open' AND entry_price IS NOT NULL"
        )
        # Open trades without entry_price -> planned
        execute_fn(
            "UPDATE trades SET status='planned' WHERE status='open' AND entry_price IS NULL"
        )
        # Closed trades flagged retroactive
        execute_fn(
            "UPDATE trades SET retroactive=1 WHERE status IN ('win','loss','breakeven')"
        )
        execute_fn("INSERT INTO _migrations (name) VALUES (?)", ["v2_status_backfill"])
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_migrations.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations.py backend/tests/test_migrations.py
git commit -m "feat(backend): add idempotent v2 migrations module"
```

---

### Task 3: Wire migrations into both DB backends

**Files:**
- Modify: `backend/turso_db.py` (replace existing `init_tables`)
- Modify: `backend/main.py` (call run_migrations on startup for SQLAlchemy path too)
- Modify: `backend/models.py` (extend Trade model with v2 columns so SQLAlchemy still works locally)

- [ ] **Step 1: Replace `init_tables` in `backend/turso_db.py`**

Open `backend/turso_db.py`. Replace the entire `init_tables` function (lines 78–101) with:

```python
def init_tables():
    # Ensure trades table exists (v1 schema is fine — migrations.py will ALTER it)
    execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT NOT NULL,
            direction TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            setup_score INTEGER NOT NULL,
            verdict TEXT NOT NULL,
            criteria_checked TEXT NOT NULL,
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            entry_price REAL,
            exit_price REAL,
            stop_loss REAL,
            take_profit REAL,
            pnl REAL,
            pnl_percent REAL,
            rr_achieved REAL,
            lessons TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            closed_at TEXT
        )
    """)
    from migrations import run_migrations
    run_migrations(execute, fetch_one)
```

- [ ] **Step 2: Extend the SQLAlchemy `Trade` model**

Replace `backend/models.py` entirely with:

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pair = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)
    timeframe = Column(String(10), nullable=False)
    strategy = Column(String(100), nullable=False, default="Zone Failure")
    setup_score = Column(Integer, nullable=False)
    verdict = Column(String(100), nullable=False)
    criteria_checked = Column(JSON, nullable=False)
    notes = Column(String(2000), default="")

    planned_entry = Column(Float, nullable=True)
    planned_stop = Column(Float, nullable=True)
    planned_target = Column(Float, nullable=True)
    planned_rr = Column(Float, nullable=True)

    status = Column(String(20), default="planned")
    retroactive = Column(Integer, default=0)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    position_size = Column(Float, nullable=True)
    account_size = Column(Float, nullable=True)
    risk_dollars = Column(Float, nullable=True)
    risk_percent = Column(Float, nullable=True)
    entry_timing = Column(String(20), nullable=True)
    emotions_entry = Column(String(500), default=",")
    feelings_entry = Column(String(2000), default="")
    skip_reason = Column(String(500), default="")

    partial_exits = Column(String(2000), default="[]")
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    rr_achieved = Column(Float, nullable=True)
    rules_followed = Column(Integer, nullable=True)
    mistake_tags = Column(String(500), default=",")
    emotions_exit = Column(String(500), default=",")
    feelings_exit = Column(String(2000), default="")
    lessons = Column(String(2000), default="")
    chart_url = Column(String(500), default="")

    created_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)
```

- [ ] **Step 3: Update SQLAlchemy startup to also run migrations**

Open `backend/main.py`. In the `else:` branch around line 75–78, replace the startup function with:

```python
    @app.on_event("startup")
    def startup():
        from models import Base as ModelBase
        ModelBase.metadata.create_all(bind=engine)
        # Run shared migrations against raw connection
        from migrations import run_migrations
        from sqlalchemy import text

        def _exec(sql, args=None):
            with engine.begin() as conn:
                if args:
                    # Replace ? with :p0, :p1, ... for SQLAlchemy textual binding
                    out = sql
                    params = {}
                    i = 0
                    while "?" in out:
                        out = out.replace("?", f":p{i}", 1)
                        params[f"p{i}"] = args[i]
                        i += 1
                    conn.execute(text(out), params)
                else:
                    conn.execute(text(sql))

        def _fetch_one(sql, args=None):
            with engine.connect() as conn:
                if args:
                    out = sql
                    params = {}
                    i = 0
                    while "?" in out:
                        out = out.replace("?", f":p{i}", 1)
                        params[f"p{i}"] = args[i]
                        i += 1
                    row = conn.execute(text(out), params).mappings().first()
                else:
                    row = conn.execute(text(sql)).mappings().first()
                return dict(row) if row else None

        run_migrations(_exec, _fetch_one)
```

- [ ] **Step 4: Run the local server, confirm startup**

```bash
cd backend && uvicorn main:app --port 8111 &
sleep 3
curl http://localhost:8111/
```

Expected: `{"status":"ok"}`. Kill the server: `kill %1`.

- [ ] **Step 5: Verify migration ran by inspecting the local SQLite**

```bash
sqlite3 backend/trading_journal.db "SELECT name FROM strategies; SELECT name FROM _migrations;"
```

Expected output includes `Zone Failure` and `v2_status_backfill`.

- [ ] **Step 6: Commit**

```bash
git add backend/turso_db.py backend/main.py backend/models.py
git commit -m "feat(backend): wire v2 migrations into both DB backends"
```

---

## Phase 2 — Backend trade-stage endpoints

### Task 4: Refactor `_parse_trade` and add new schemas

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Update `_parse_trade` to include all new fields**

Find `_parse_trade` (around line 156) and replace its body with:

```python
def _parse_trade(row: dict) -> dict:
    if not row:
        return row
    cc = row.get("criteria_checked", "[]")
    if isinstance(cc, str):
        try: cc = json.loads(cc)
        except: cc = []

    pe = row.get("partial_exits", "[]")
    if isinstance(pe, str):
        try: pe = json.loads(pe)
        except: pe = []

    def _f(key):
        v = row.get(key)
        return float(v) if v not in (None, "") else None

    def _i(key):
        v = row.get(key)
        return int(v) if v not in (None, "") else None

    def _tags(key):
        raw = row.get(key) or ","
        # comma-wrapped: ",a,b," -> ["a", "b"]
        return [t for t in raw.split(",") if t]

    return {
        "id": int(row["id"]),
        "pair": row["pair"], "direction": row["direction"], "timeframe": row["timeframe"],
        "strategy": row.get("strategy") or "Zone Failure",
        "setup_score": int(row["setup_score"]),
        "verdict": row["verdict"],
        "criteria_checked": cc,
        "notes": row.get("notes") or "",
        "planned_entry": _f("planned_entry"), "planned_stop": _f("planned_stop"),
        "planned_target": _f("planned_target"), "planned_rr": _f("planned_rr"),
        "status": row.get("status") or "planned",
        "retroactive": bool(_i("retroactive") or 0),
        "entry_price": _f("entry_price"), "exit_price": _f("exit_price"),
        "stop_loss": _f("stop_loss"), "take_profit": _f("take_profit"),
        "position_size": _f("position_size"), "account_size": _f("account_size"),
        "risk_dollars": _f("risk_dollars"), "risk_percent": _f("risk_percent"),
        "entry_timing": row.get("entry_timing"),
        "emotions_entry": _tags("emotions_entry"),
        "feelings_entry": row.get("feelings_entry") or "",
        "skip_reason": row.get("skip_reason") or "",
        "partial_exits": pe,
        "pnl": _f("pnl"), "pnl_percent": _f("pnl_percent"), "rr_achieved": _f("rr_achieved"),
        "rules_followed": (None if row.get("rules_followed") is None else bool(_i("rules_followed"))),
        "mistake_tags": _tags("mistake_tags"),
        "emotions_exit": _tags("emotions_exit"),
        "feelings_exit": row.get("feelings_exit") or "",
        "lessons": row.get("lessons") or "",
        "chart_url": row.get("chart_url") or "",
        "created_at": row.get("created_at"),
        "closed_at": row.get("closed_at"),
    }
```

- [ ] **Step 2: Replace the Pydantic schemas section**

Find the `# --- Schemas ---` block (around line 189). Replace `TradeCreate` and `TradeUpdate` and add new ones:

```python
class TradeCreatePlan(BaseModel):
    pair: str
    direction: str
    timeframe: str
    strategy: str = "Zone Failure"
    setup_score: int
    verdict: str
    criteria_checked: list[str]
    notes: str = ""
    planned_entry: Optional[float] = None
    planned_stop: Optional[float] = None
    planned_target: Optional[float] = None
    planned_rr: Optional[float] = None


class TradeEnter(BaseModel):
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    position_size: float
    account_size: float
    entry_timing: Optional[str] = None      # on_time | late | early
    emotions_entry: list[str] = []
    feelings_entry: str = ""


class TradeSkip(BaseModel):
    skip_reason: str
    emotions_entry: list[str] = []


class TradeClose(BaseModel):
    status: str  # win | loss | breakeven
    exit_price: float
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    rr_achieved: Optional[float] = None
    rules_followed: Optional[bool] = None
    mistake_tags: list[str] = []
    emotions_exit: list[str] = []
    feelings_exit: str = ""
    lessons: str = ""
    chart_url: str = ""
    partial_exits: list[dict] = []


class TradeRetroactive(BaseModel):
    # All Plan + Enter + Close fields together
    pair: str
    direction: str
    timeframe: str
    strategy: str = "Zone Failure"
    setup_score: int
    verdict: str
    criteria_checked: list[str]
    notes: str = ""
    planned_entry: Optional[float] = None
    planned_stop: Optional[float] = None
    planned_target: Optional[float] = None
    planned_rr: Optional[float] = None
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    account_size: Optional[float] = None
    entry_timing: Optional[str] = None
    emotions_entry: list[str] = []
    feelings_entry: str = ""
    status: str  # win | loss | breakeven
    exit_price: float
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    rr_achieved: Optional[float] = None
    rules_followed: Optional[bool] = None
    mistake_tags: list[str] = []
    emotions_exit: list[str] = []
    feelings_exit: str = ""
    lessons: str = ""
    chart_url: str = ""
    partial_exits: list[dict] = []


class TradeUpdate(BaseModel):
    # Generic patch — used for editing any stage's data after the fact
    notes: Optional[str] = None
    planned_entry: Optional[float] = None
    planned_stop: Optional[float] = None
    planned_target: Optional[float] = None
    planned_rr: Optional[float] = None
    status: Optional[str] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    position_size: Optional[float] = None
    account_size: Optional[float] = None
    entry_timing: Optional[str] = None
    emotions_entry: Optional[list[str]] = None
    feelings_entry: Optional[str] = None
    skip_reason: Optional[str] = None
    partial_exits: Optional[list[dict]] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    rr_achieved: Optional[float] = None
    rules_followed: Optional[bool] = None
    mistake_tags: Optional[list[str]] = None
    emotions_exit: Optional[list[str]] = None
    feelings_exit: Optional[str] = None
    lessons: Optional[str] = None
    chart_url: Optional[str] = None


def _tags_to_db(tags: list[str]) -> str:
    """Encode a tag list as a comma-wrapped string. Empty list -> ','."""
    if not tags:
        return ","
    cleaned = [t.strip() for t in tags if t and t.strip()]
    return "," + ",".join(cleaned) + "," if cleaned else ","
```

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "refactor(backend): extend Trade schemas + parser for v2 fields"
```

---

### Task 5: Replace POST /api/trades with the Plan-stage endpoint

**Files:**
- Modify: `backend/main.py` (`create_trade` route)

- [ ] **Step 1: Replace `create_trade`**

Find the `@app.post("/api/trades")` route (around line 220). Replace the function:

```python
@app.post("/api/trades")
def create_trade(trade: TradeCreatePlan):
    data = trade.model_dump()
    data["criteria_checked"] = json.dumps(data["criteria_checked"])
    data["status"] = "planned"
    row = db_create_trade(data)
    return _parse_trade(row)
```

- [ ] **Step 2: Update `db_create_trade` (Turso branch)**

Find `db_create_trade` in the `if USE_TURSO:` branch (around line 29). Replace:

```python
    def db_create_trade(data: dict) -> dict:
        cols = list(data.keys())
        placeholders = ",".join(["?"] * len(cols))
        execute(
            f"INSERT INTO trades ({','.join(cols)}) VALUES ({placeholders})",
            [data[c] for c in cols],
        )
        return fetch_one("SELECT * FROM trades ORDER BY id DESC LIMIT 1")
```

- [ ] **Step 3: Update `db_create_trade` (SQLAlchemy branch)**

Find `db_create_trade` in the `else:` branch (around line 102). Replace:

```python
    def db_create_trade(data: dict) -> dict:
        db = _get_db()
        # SQLAlchemy column criteria_checked is JSON typed, so decode the JSON we just encoded
        if isinstance(data.get("criteria_checked"), str):
            try:
                data["criteria_checked"] = json.loads(data["criteria_checked"])
            except: pass
        t = Trade(**data)
        db.add(t); db.commit(); db.refresh(t)
        # Re-encode for parser
        result = _trade_to_dict(t)
        if isinstance(result.get("criteria_checked"), list):
            result["criteria_checked_list"] = result["criteria_checked"]
        db.close()
        return result
```

- [ ] **Step 4: Update `_trade_to_dict` to include all v2 fields**

Replace the `_trade_to_dict` function (around line 88):

```python
    def _trade_to_dict(t):
        return {
            "id": t.id, "pair": t.pair, "direction": t.direction, "timeframe": t.timeframe,
            "strategy": t.strategy or "Zone Failure",
            "setup_score": t.setup_score, "verdict": t.verdict,
            "criteria_checked": t.criteria_checked if isinstance(t.criteria_checked, list) else json.loads(t.criteria_checked or "[]"),
            "notes": t.notes or "",
            "planned_entry": t.planned_entry, "planned_stop": t.planned_stop,
            "planned_target": t.planned_target, "planned_rr": t.planned_rr,
            "status": t.status or "planned",
            "retroactive": int(t.retroactive or 0),
            "entry_price": t.entry_price, "exit_price": t.exit_price,
            "stop_loss": t.stop_loss, "take_profit": t.take_profit,
            "position_size": t.position_size, "account_size": t.account_size,
            "risk_dollars": t.risk_dollars, "risk_percent": t.risk_percent,
            "entry_timing": t.entry_timing,
            "emotions_entry": t.emotions_entry or ",",
            "feelings_entry": t.feelings_entry or "",
            "skip_reason": t.skip_reason or "",
            "partial_exits": t.partial_exits or "[]",
            "pnl": t.pnl, "pnl_percent": t.pnl_percent, "rr_achieved": t.rr_achieved,
            "rules_followed": t.rules_followed,
            "mistake_tags": t.mistake_tags or ",",
            "emotions_exit": t.emotions_exit or ",",
            "feelings_exit": t.feelings_exit or "",
            "lessons": t.lessons or "",
            "chart_url": t.chart_url or "",
            "created_at": str(t.created_at) if t.created_at else None,
            "closed_at": str(t.closed_at) if t.closed_at else None,
        }
```

- [ ] **Step 5: Smoke-test locally**

```bash
cd backend && uvicorn main:app --port 8111 &
sleep 3
curl -X POST http://localhost:8111/api/trades \
  -H 'Content-Type: application/json' \
  -d '{"pair":"XAU/USD","direction":"LONG","timeframe":"4H","setup_score":80,"verdict":"B SETUP","criteria_checked":["trend","zone","signal","failure"],"planned_entry":2400.0,"planned_stop":2380.0,"planned_target":2440.0,"planned_rr":2.0,"notes":"Sweep low at zone"}'
```

Expected: JSON with `"status":"planned"` and the planned_entry/stop/target populated.

```bash
kill %1
```

- [ ] **Step 6: Commit**

```bash
git add backend/main.py
git commit -m "feat(backend): POST /api/trades creates plan-stage trade"
```

---

### Task 6: Add /enter, /skip, /close, /retroactive endpoints

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add helper to update arbitrary trade fields**

Find `db_update_trade` in the Turso branch and replace:

```python
    def db_update_trade(trade_id: int, data: dict):
        sets = []
        vals = []
        for k, v in data.items():
            sets.append(f"{k} = ?")
            vals.append(v)
        if not sets:
            return db_get_trade(trade_id)
        vals.append(trade_id)
        execute(f"UPDATE trades SET {', '.join(sets)} WHERE id = ?", vals)
        return fetch_one("SELECT * FROM trades WHERE id = ?", [trade_id])
```

(Note: the previous version skipped `None` values. We now allow setting columns to NULL explicitly.)

In the SQLAlchemy branch, replace `db_update_trade`:

```python
    def db_update_trade(trade_id: int, data: dict):
        db = _get_db()
        t = db.execute(select(Trade).where(Trade.id == trade_id)).scalar_one_or_none()
        if not t:
            db.close()
            return None
        for k, v in data.items():
            setattr(t, k, v)
        db.commit(); db.refresh(t)
        result = _trade_to_dict(t)
        db.close()
        return result
```

- [ ] **Step 2: Add the four endpoints to `backend/main.py`**

After the existing `update_trade` PATCH route (around line 240), insert:

```python
@app.post("/api/trades/{trade_id}/enter")
def enter_trade(trade_id: int, data: TradeEnter):
    from risk import compute_risk
    existing = db_get_trade(trade_id)
    if not existing:
        raise HTTPException(404, "Trade not found")
    payload = data.model_dump()
    risk = compute_risk(payload["entry_price"], payload["stop_loss"],
                        payload["position_size"], payload["account_size"])
    update = {
        "status": "entered",
        "entry_price": payload["entry_price"],
        "stop_loss": payload["stop_loss"],
        "take_profit": payload.get("take_profit"),
        "position_size": payload["position_size"],
        "account_size": payload["account_size"],
        "risk_dollars": risk["risk_dollars"],
        "risk_percent": risk["risk_percent"],
        "entry_timing": payload.get("entry_timing"),
        "emotions_entry": _tags_to_db(payload.get("emotions_entry") or []),
        "feelings_entry": payload.get("feelings_entry") or "",
    }
    row = db_update_trade(trade_id, update)
    return _parse_trade(row)


@app.post("/api/trades/{trade_id}/skip")
def skip_trade(trade_id: int, data: TradeSkip):
    existing = db_get_trade(trade_id)
    if not existing:
        raise HTTPException(404, "Trade not found")
    update = {
        "status": "skipped",
        "skip_reason": data.skip_reason,
        "emotions_entry": _tags_to_db(data.emotions_entry or []),
        "closed_at": datetime.utcnow().isoformat(),
    }
    row = db_update_trade(trade_id, update)
    return _parse_trade(row)


@app.post("/api/trades/{trade_id}/close")
def close_trade(trade_id: int, data: TradeClose):
    if data.status not in ("win", "loss", "breakeven"):
        raise HTTPException(400, "status must be win | loss | breakeven")
    existing = db_get_trade(trade_id)
    if not existing:
        raise HTTPException(404, "Trade not found")
    update = {
        "status": data.status,
        "exit_price": data.exit_price,
        "pnl": data.pnl,
        "pnl_percent": data.pnl_percent,
        "rr_achieved": data.rr_achieved,
        "rules_followed": (None if data.rules_followed is None else int(data.rules_followed)),
        "mistake_tags": _tags_to_db(data.mistake_tags or []),
        "emotions_exit": _tags_to_db(data.emotions_exit or []),
        "feelings_exit": data.feelings_exit or "",
        "lessons": data.lessons or "",
        "chart_url": data.chart_url or "",
        "partial_exits": json.dumps(data.partial_exits or []),
        "closed_at": datetime.utcnow().isoformat(),
    }
    row = db_update_trade(trade_id, update)
    return _parse_trade(row)


@app.post("/api/trades/retroactive")
def create_retroactive_trade(trade: TradeRetroactive):
    from risk import compute_risk
    if trade.status not in ("win", "loss", "breakeven"):
        raise HTTPException(400, "status must be win | loss | breakeven")
    risk = compute_risk(trade.entry_price, trade.stop_loss,
                        trade.position_size, trade.account_size)
    data = {
        "pair": trade.pair, "direction": trade.direction, "timeframe": trade.timeframe,
        "strategy": trade.strategy, "setup_score": trade.setup_score, "verdict": trade.verdict,
        "criteria_checked": json.dumps(trade.criteria_checked),
        "notes": trade.notes,
        "planned_entry": trade.planned_entry, "planned_stop": trade.planned_stop,
        "planned_target": trade.planned_target, "planned_rr": trade.planned_rr,
        "status": trade.status, "retroactive": 1,
        "entry_price": trade.entry_price, "stop_loss": trade.stop_loss,
        "take_profit": trade.take_profit, "exit_price": trade.exit_price,
        "position_size": trade.position_size, "account_size": trade.account_size,
        "risk_dollars": risk["risk_dollars"], "risk_percent": risk["risk_percent"],
        "entry_timing": trade.entry_timing,
        "emotions_entry": _tags_to_db(trade.emotions_entry or []),
        "feelings_entry": trade.feelings_entry,
        "pnl": trade.pnl, "pnl_percent": trade.pnl_percent, "rr_achieved": trade.rr_achieved,
        "rules_followed": (None if trade.rules_followed is None else int(trade.rules_followed)),
        "mistake_tags": _tags_to_db(trade.mistake_tags or []),
        "emotions_exit": _tags_to_db(trade.emotions_exit or []),
        "feelings_exit": trade.feelings_exit,
        "lessons": trade.lessons, "chart_url": trade.chart_url,
        "partial_exits": json.dumps(trade.partial_exits or []),
        "closed_at": datetime.utcnow().isoformat(),
    }
    row = db_create_trade(data)
    return _parse_trade(row)
```

- [ ] **Step 3: Update existing PATCH endpoint to recompute risk**

Find `update_trade` (around line 240). Replace:

```python
@app.patch("/api/trades/{trade_id}")
def update_trade(trade_id: int, data: TradeUpdate):
    import traceback
    from risk import compute_risk
    try:
        existing = db_get_trade(trade_id)
        if not existing:
            raise HTTPException(404, "Trade not found")

        update_data = data.model_dump(exclude_unset=True)

        # Encode tag lists as comma-wrapped
        for key in ("emotions_entry", "emotions_exit", "mistake_tags"):
            if key in update_data:
                update_data[key] = _tags_to_db(update_data[key] or [])
        if "partial_exits" in update_data:
            update_data["partial_exits"] = json.dumps(update_data["partial_exits"] or [])
        if "rules_followed" in update_data and update_data["rules_followed"] is not None:
            update_data["rules_followed"] = int(update_data["rules_followed"])

        if update_data.get("status") in ("win", "loss", "breakeven", "skipped"):
            update_data["closed_at"] = datetime.utcnow().isoformat()

        # Recompute risk if any input changed
        risk_keys = {"entry_price", "stop_loss", "position_size", "account_size"}
        if risk_keys & set(update_data.keys()):
            merged = {**(existing or {}), **update_data}
            risk = compute_risk(merged.get("entry_price"), merged.get("stop_loss"),
                                merged.get("position_size"), merged.get("account_size"))
            update_data["risk_dollars"] = risk["risk_dollars"]
            update_data["risk_percent"] = risk["risk_percent"]

        row = db_update_trade(trade_id, update_data)
        return _parse_trade(row)
    except HTTPException:
        raise
    except Exception as e:
        print(f"UPDATE ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(500, str(e))
```

- [ ] **Step 4: Add stage-flow integration test**

Create `backend/tests/test_stages.py`:

```python
import os
os.environ.pop("TURSO_DB_URL", None)  # force SQLAlchemy backend

import json
from fastapi.testclient import TestClient


def _client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Re-import main with fresh DB path
    import importlib, sys
    for m in list(sys.modules):
        if m in ("main", "models", "database", "migrations"):
            sys.modules.pop(m)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import main
    return TestClient(main.app)


def test_full_stage_flow(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/trades", json={
        "pair": "XAU/USD", "direction": "LONG", "timeframe": "4H",
        "setup_score": 80, "verdict": "B SETUP",
        "criteria_checked": ["trend","zone","signal","failure"],
        "planned_entry": 2400.0, "planned_stop": 2380.0,
        "planned_target": 2440.0, "planned_rr": 2.0,
    })
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    assert r.json()["status"] == "planned"

    r = c.post(f"/api/trades/{tid}/enter", json={
        "entry_price": 2402.0, "stop_loss": 2380.0,
        "position_size": 1.0, "account_size": 10000.0,
        "entry_timing": "on_time",
        "emotions_entry": ["confident"],
    })
    assert r.json()["status"] == "entered"
    assert abs(r.json()["risk_dollars"] - 22.0) < 0.001
    assert abs(r.json()["risk_percent"] - 0.22) < 0.001

    r = c.post(f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 2440.0,
        "pnl": 38.0, "rr_achieved": 1.7,
        "rules_followed": True,
        "mistake_tags": [], "emotions_exit": ["calm"],
        "lessons": "Patience paid off",
    })
    assert r.json()["status"] == "win"
    assert r.json()["rules_followed"] is True
    assert "calm" in r.json()["emotions_exit"]


def test_skip_flow(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/trades", json={
        "pair": "EUR/USD", "direction": "SHORT", "timeframe": "1H",
        "setup_score": 60, "verdict": "C SETUP",
        "criteria_checked": ["trend","zone","signal","failure"],
    })
    tid = r.json()["id"]
    r = c.post(f"/api/trades/{tid}/skip", json={
        "skip_reason": "News in 1h", "emotions_entry": ["patient"]
    })
    assert r.json()["status"] == "skipped"
    assert r.json()["skip_reason"] == "News in 1h"
```

- [ ] **Step 5: Run tests**

```bash
cd backend && pytest tests/test_stages.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/tests/test_stages.py
git commit -m "feat(backend): add /enter /skip /close /retroactive endpoints + risk auto-calc"
```

---

## Phase 3 — Backend strategies, account snapshots, reviews

### Task 7: Strategies CRUD

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add Pydantic schemas**

After the existing schemas, add:

```python
class CriterionDef(BaseModel):
    id: str
    label: str
    points: int
    category: str = "Quality"
    description: str = ""


class StrategyCreate(BaseModel):
    name: str
    criteria: list[CriterionDef]
    is_core_required: list[str] = []


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    criteria: Optional[list[CriterionDef]] = None
    is_core_required: Optional[list[str]] = None
```

- [ ] **Step 2: Add routes**

After the trade routes, add:

```python
@app.get("/api/strategies")
def list_strategies():
    rows = fetch_all("SELECT * FROM strategies ORDER BY id ASC") if USE_TURSO else _sa_list_strategies()
    return [_parse_strategy(r) for r in rows]


@app.post("/api/strategies")
def create_strategy(data: StrategyCreate):
    if USE_TURSO:
        execute(
            "INSERT INTO strategies (name, criteria, is_core_required) VALUES (?, ?, ?)",
            [data.name, json.dumps([c.model_dump() for c in data.criteria]),
             json.dumps(data.is_core_required)],
        )
        row = fetch_one("SELECT * FROM strategies WHERE name = ?", [data.name])
    else:
        row = _sa_create_strategy(data.model_dump())
    return _parse_strategy(row)


@app.patch("/api/strategies/{strategy_id}")
def update_strategy(strategy_id: int, data: StrategyUpdate):
    payload = data.model_dump(exclude_unset=True)
    if "criteria" in payload:
        payload["criteria"] = json.dumps(payload["criteria"])
    if "is_core_required" in payload:
        payload["is_core_required"] = json.dumps(payload["is_core_required"])

    sets = ", ".join(f"{k} = ?" for k in payload.keys())
    if not sets:
        raise HTTPException(400, "no fields to update")
    if USE_TURSO:
        execute(f"UPDATE strategies SET {sets} WHERE id = ?", list(payload.values()) + [strategy_id])
        row = fetch_one("SELECT * FROM strategies WHERE id = ?", [strategy_id])
    else:
        row = _sa_update_strategy(strategy_id, payload)
    if not row:
        raise HTTPException(404, "Strategy not found")
    return _parse_strategy(row)


@app.delete("/api/strategies/{strategy_id}")
def delete_strategy(strategy_id: int):
    if USE_TURSO:
        row = fetch_one("SELECT name FROM strategies WHERE id = ?", [strategy_id])
        if not row:
            raise HTTPException(404, "Strategy not found")
        in_use = fetch_one("SELECT COUNT(*) AS c FROM trades WHERE strategy = ?", [row["name"]])
        if int(in_use["c"]) > 0:
            raise HTTPException(409, "Strategy is referenced by existing trades")
        execute("DELETE FROM strategies WHERE id = ?", [strategy_id])
    else:
        _sa_delete_strategy(strategy_id)
    return {"ok": True}


def _parse_strategy(row):
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "criteria": json.loads(row["criteria"]) if isinstance(row.get("criteria"), str) else row.get("criteria") or [],
        "is_core_required": json.loads(row.get("is_core_required") or "[]") if isinstance(row.get("is_core_required"), str) else (row.get("is_core_required") or []),
        "created_at": row.get("created_at"),
    }
```

- [ ] **Step 3: Add SQLAlchemy helpers in the `else` branch (after `db_trades_since`)**

These helpers use raw `text()` queries — matching the snapshots/reviews pattern below — to avoid relying on SQLAlchemy table reflection (which would run at import time, before `run_migrations` has created the strategies table).

```python
    from sqlalchemy import text as _text

    def _sa_list_strategies():
        with engine.connect() as conn:
            rows = conn.execute(_text("SELECT * FROM strategies ORDER BY id ASC")).mappings().all()
            return [dict(r) for r in rows]

    def _sa_create_strategy(data):
        criteria_json = json.dumps([c if isinstance(c, dict) else c.model_dump() for c in data["criteria"]])
        core_json = json.dumps(data["is_core_required"])
        with engine.begin() as conn:
            conn.execute(_text(
                "INSERT INTO strategies (name, criteria, is_core_required) VALUES (:n, :c, :ic)"
            ), {"n": data["name"], "c": criteria_json, "ic": core_json})
            r = conn.execute(_text("SELECT * FROM strategies WHERE name = :n"),
                             {"n": data["name"]}).mappings().first()
            return dict(r)

    def _sa_update_strategy(sid, payload):
        sets = ", ".join(f"{k} = :{k}" for k in payload.keys())
        params = {**payload, "id": sid}
        with engine.begin() as conn:
            conn.execute(_text(f"UPDATE strategies SET {sets} WHERE id = :id"), params)
            r = conn.execute(_text("SELECT * FROM strategies WHERE id = :id"),
                             {"id": sid}).mappings().first()
            return dict(r) if r else None

    def _sa_delete_strategy(sid):
        with engine.begin() as conn:
            r = conn.execute(_text("SELECT * FROM strategies WHERE id = :id"),
                             {"id": sid}).mappings().first()
            if not r:
                raise HTTPException(404, "Strategy not found")
            in_use = conn.execute(_text("SELECT COUNT(*) AS c FROM trades WHERE strategy = :n"),
                                  {"n": r["name"]}).scalar()
            if int(in_use) > 0:
                raise HTTPException(409, "Strategy is referenced by existing trades")
            conn.execute(_text("DELETE FROM strategies WHERE id = :id"), {"id": sid})
```

- [ ] **Step 4: Smoke test**

```bash
cd backend && uvicorn main:app --port 8111 &
sleep 3
curl http://localhost:8111/api/strategies
```

Expected: array containing one strategy named "Zone Failure" with 11 criteria.

```bash
kill %1
```

- [ ] **Step 5: Commit**

```bash
git add backend/main.py
git commit -m "feat(backend): strategies CRUD endpoints"
```

---

### Task 8: Account snapshots

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add schema and routes**

After strategies routes:

```python
class AccountSnapshotCreate(BaseModel):
    balance: float
    note: str = ""


def _parse_snapshot(row):
    if not row: return None
    return {
        "id": int(row["id"]),
        "balance": float(row["balance"]),
        "recorded_at": row.get("recorded_at"),
        "note": row.get("note") or "",
    }


@app.get("/api/account-snapshots")
def list_snapshots():
    if USE_TURSO:
        rows = fetch_all("SELECT * FROM account_snapshots ORDER BY id DESC")
    else:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            rows = [dict(r) for r in conn.execute(_text("SELECT * FROM account_snapshots ORDER BY id DESC")).mappings()]
    return [_parse_snapshot(r) for r in rows]


@app.post("/api/account-snapshots")
def create_snapshot(data: AccountSnapshotCreate):
    if USE_TURSO:
        execute("INSERT INTO account_snapshots (balance, note) VALUES (?, ?)", [data.balance, data.note])
        row = fetch_one("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")
    else:
        from sqlalchemy import text as _text
        with engine.begin() as conn:
            conn.execute(_text("INSERT INTO account_snapshots (balance, note) VALUES (:b, :n)"),
                         {"b": data.balance, "n": data.note})
            row = dict(conn.execute(_text("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")).mappings().first())
    return _parse_snapshot(row)


@app.get("/api/account-snapshots/latest")
def latest_snapshot():
    if USE_TURSO:
        row = fetch_one("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")
    else:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            r = conn.execute(_text("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")).mappings().first()
            row = dict(r) if r else None
    if not row:
        return {"balance": None}
    return _parse_snapshot(row)
```

- [ ] **Step 2: Smoke**

```bash
cd backend && uvicorn main:app --port 8111 &
sleep 3
curl -X POST http://localhost:8111/api/account-snapshots \
  -H 'Content-Type: application/json' \
  -d '{"balance":10000,"note":"Initial"}'
curl http://localhost:8111/api/account-snapshots/latest
kill %1
```

Expected: 200 with `{"balance":10000,...}`.

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat(backend): account snapshots CRUD"
```

---

### Task 9: Reviews CRUD with stats snapshot

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add schema and routes**

After account snapshots:

```python
class ReviewCreate(BaseModel):
    period_type: str  # week | month | custom
    period_start: str  # ISO date
    period_end: str
    notes: str


def _parse_review(row):
    if not row: return None
    return {
        "id": int(row["id"]),
        "period_type": row["period_type"],
        "period_start": row["period_start"],
        "period_end": row["period_end"],
        "notes": row["notes"],
        "stats_snapshot": json.loads(row["stats_snapshot"]) if isinstance(row.get("stats_snapshot"), str) else row.get("stats_snapshot"),
        "created_at": row.get("created_at"),
    }


@app.get("/api/reviews")
def list_reviews():
    if USE_TURSO:
        rows = fetch_all("SELECT id, period_type, period_start, period_end, notes, created_at FROM review_notes ORDER BY id DESC")
    else:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            rows = [dict(r) for r in conn.execute(_text("SELECT id, period_type, period_start, period_end, notes, created_at FROM review_notes ORDER BY id DESC")).mappings()]
    return [{
        "id": int(r["id"]), "period_type": r["period_type"],
        "period_start": r["period_start"], "period_end": r["period_end"],
        "notes": r["notes"], "created_at": r.get("created_at"),
    } for r in rows]


@app.get("/api/reviews/{review_id}")
def get_review(review_id: int):
    if USE_TURSO:
        row = fetch_one("SELECT * FROM review_notes WHERE id = ?", [review_id])
    else:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            r = conn.execute(_text("SELECT * FROM review_notes WHERE id = :i"), {"i": review_id}).mappings().first()
            row = dict(r) if r else None
    if not row:
        raise HTTPException(404, "Review not found")
    return _parse_review(row)


@app.post("/api/reviews")
def create_review(data: ReviewCreate):
    # Snapshot current analytics for the requested range
    snapshot = _compute_analytics_range(data.period_start, data.period_end)
    if USE_TURSO:
        execute(
            "INSERT INTO review_notes (period_type, period_start, period_end, notes, stats_snapshot) VALUES (?, ?, ?, ?, ?)",
            [data.period_type, data.period_start, data.period_end, data.notes, json.dumps(snapshot)],
        )
        row = fetch_one("SELECT * FROM review_notes ORDER BY id DESC LIMIT 1")
    else:
        from sqlalchemy import text as _text
        with engine.begin() as conn:
            conn.execute(_text("""
                INSERT INTO review_notes (period_type, period_start, period_end, notes, stats_snapshot)
                VALUES (:t, :s, :e, :n, :ss)
            """), {"t": data.period_type, "s": data.period_start, "e": data.period_end,
                   "n": data.notes, "ss": json.dumps(snapshot)})
            row = dict(conn.execute(_text("SELECT * FROM review_notes ORDER BY id DESC LIMIT 1")).mappings().first())
    return _parse_review(row)


@app.delete("/api/reviews/{review_id}")
def delete_review(review_id: int):
    if USE_TURSO:
        execute("DELETE FROM review_notes WHERE id = ?", [review_id])
    else:
        from sqlalchemy import text as _text
        with engine.begin() as conn:
            conn.execute(_text("DELETE FROM review_notes WHERE id = :i"), {"i": review_id})
    return {"ok": True}
```

- [ ] **Step 2: Stub `_compute_analytics_range`**

The full analytics rewrite happens in Phase 4. For now add a stub at module level (just before the routes):

```python
def _compute_analytics_range(start_iso: str, end_iso: str) -> dict:
    # Will be replaced in Phase 4. For now return current 14-day analytics.
    return get_analytics(days=14)
```

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat(backend): reviews CRUD with stats snapshot stub"
```

---

## Phase 4 — Backend analytics module

### Task 10: Extract analytics into its own module (TDD)

**Files:**
- Create: `backend/analytics.py`
- Create: `backend/tests/test_analytics.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_analytics.py`:

```python
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
        _trade(status="win", rules_followed=True, retroactive=True, pnl=15),  # excluded
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
        _trade(status="loss", retroactive=True, pnl=-5),  # excluded — no plan
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
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/test_analytics.py -v
```

Expected: ModuleNotFoundError on `analytics`.

- [ ] **Step 3: Implement `backend/analytics.py`**

```python
"""Analytics computations over a list of parsed trade dicts."""
from collections import defaultdict
from datetime import datetime, timedelta

RISK_THRESHOLD_PCT = 2.0


def compute_analytics(trades: list[dict], days: int | None = None,
                      period_start: str | None = None, period_end: str | None = None) -> dict:
    closed = [t for t in trades if t["status"] in ("win", "loss", "breakeven")]
    wins = [t for t in closed if t["status"] == "win"]
    losses = [t for t in closed if t["status"] == "loss"]
    breakevens = [t for t in closed if t["status"] == "breakeven"]
    skipped = [t for t in trades if t["status"] == "skipped"]
    entered_open = [t for t in trades if t["status"] == "entered"]
    planned = [t for t in trades if t["status"] == "planned"]

    total_pnl = sum(t["pnl"] or 0 for t in closed)
    avg_score = sum(t["setup_score"] for t in trades) / len(trades) if trades else 0
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    avg_rr = sum(t["rr_achieved"] or 0 for t in closed) / len(closed) if closed else 0

    return {
        "period_days": days,
        "period_start": period_start, "period_end": period_end,
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "open_trades": len(entered_open),
        "planned_trades": len(planned),
        "skipped_trades": len(skipped),
        "wins": len(wins), "losses": len(losses), "breakeven": len(breakevens),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "avg_score": round(avg_score, 1),
        "avg_rr": round(avg_rr, 2),
        "score_analysis": _score_analysis(closed),
        "pair_breakdown": _pair_breakdown(closed),
        "direction_stats": _direction_stats(closed),
        "plan_adherence": _plan_adherence(trades),
        "risk_discipline": _risk_discipline(trades),
        "mistake_impact": _tag_impact([t for t in closed if not t["retroactive"]], "mistake_tags"),
        "emotion_impact": {
            "entry": _tag_impact(closed, "emotions_entry"),
            "exit":  _tag_impact(closed, "emotions_exit"),
        },
        "timing_impact": _timing_impact(closed),
        "strategy_breakdown": _strategy_breakdown(closed),
        "edge_composite": _edge_composite(closed),
        "trades": trades,
    }


def _score_analysis(closed):
    buckets = {"A (85-100)": [], "B (70-84)": [], "C (55-69)": [], "D (<55)": []}
    for t in closed:
        s = t["setup_score"]
        if s >= 85: buckets["A (85-100)"].append(t)
        elif s >= 70: buckets["B (70-84)"].append(t)
        elif s >= 55: buckets["C (55-69)"].append(t)
        else: buckets["D (<55)"].append(t)
    out = {}
    for bucket, bt in buckets.items():
        if bt:
            bw = [t for t in bt if t["status"] == "win"]
            out[bucket] = {
                "count": len(bt),
                "win_rate": round(len(bw) / len(bt) * 100, 1),
                "avg_pnl": round(sum(t["pnl"] or 0 for t in bt) / len(bt), 2),
            }
    return out


def _pair_breakdown(closed):
    pairs = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0})
    for t in closed:
        p = t["pair"]
        if t["status"] == "win": pairs[p]["wins"] += 1
        elif t["status"] == "loss": pairs[p]["losses"] += 1
        pairs[p]["pnl"] = round(pairs[p]["pnl"] + (t["pnl"] or 0), 2)
    return dict(pairs)


def _direction_stats(closed):
    out = {}
    for d in ("LONG", "SHORT"):
        rows = [t for t in closed if t["direction"] == d]
        wins = [t for t in rows if t["status"] == "win"]
        out[d] = {
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
            "pnl": round(sum(t["pnl"] or 0 for t in rows), 2),
        }
    return out


def _plan_adherence(trades):
    # Lifecycle started with a plan = not retroactive, status in
    # entered, win, loss, breakeven, skipped
    planned_lifecycle = [
        t for t in trades
        if not t["retroactive"]
        and t["status"] in ("entered", "win", "loss", "breakeven", "skipped")
    ]
    closed = [t for t in planned_lifecycle if t["status"] in ("win", "loss", "breakeven")]
    skipped = [t for t in planned_lifecycle if t["status"] == "skipped"]
    rules_known = [t for t in closed if t["rules_followed"] is not None]
    followed = [t for t in rules_known if t["rules_followed"]]
    broken = [t for t in rules_known if not t["rules_followed"]]
    fwins = [t for t in followed if t["status"] == "win"]
    bwins = [t for t in broken if t["status"] == "win"]
    return {
        "rules_followed_pct": round(len(followed) / len(rules_known) * 100, 1) if rules_known else 0,
        "rules_followed_win_rate": round(len(fwins) / len(followed) * 100, 1) if followed else 0,
        "rules_broken_win_rate": round(len(bwins) / len(broken) * 100, 1) if broken else 0,
        "skip_rate": round(len(skipped) / len(planned_lifecycle) * 100, 1) if planned_lifecycle else 0,
        "retroactive_rate": round(
            len([t for t in trades if t["retroactive"]]) / len(trades) * 100, 1
        ) if trades else 0,
    }


def _risk_discipline(trades):
    rows = [t for t in trades if t["risk_percent"] is not None]
    if not rows:
        return {"avg_risk_pct": 0, "max_risk_pct": 0, "over_threshold_count": 0, "histogram": []}
    avg = sum(t["risk_percent"] for t in rows) / len(rows)
    mx = max(t["risk_percent"] for t in rows)
    over = len([t for t in rows if t["risk_percent"] > RISK_THRESHOLD_PCT])

    bucket_defs = [("<0.5%", 0, 0.5), ("0.5-1%", 0.5, 1.0), ("1-2%", 1.0, 2.0),
                   ("2-3%", 2.0, 3.0), (">3%", 3.0, float("inf"))]
    hist = []
    for name, lo, hi in bucket_defs:
        count = len([t for t in rows if lo <= t["risk_percent"] < hi])
        hist.append({"bucket": name, "count": count})

    return {
        "avg_risk_pct": round(avg, 2),
        "max_risk_pct": round(mx, 2),
        "over_threshold_count": over,
        "histogram": hist,
    }


def _tag_impact(closed, key):
    by_tag = defaultdict(lambda: {"count": 0, "wins": 0, "pnl_sum": 0.0})
    for t in closed:
        tags = t[key] or []
        if not tags:
            if key == "mistake_tags":
                by_tag["(none)"]["count"] += 1
                if t["status"] == "win": by_tag["(none)"]["wins"] += 1
                by_tag["(none)"]["pnl_sum"] += t["pnl"] or 0
            continue
        for tag in tags:
            by_tag[tag]["count"] += 1
            if t["status"] == "win": by_tag[tag]["wins"] += 1
            by_tag[tag]["pnl_sum"] += t["pnl"] or 0
    rows = []
    for tag, agg in by_tag.items():
        rows.append({
            "tag": tag,
            "count": agg["count"],
            "win_rate": round(agg["wins"] / agg["count"] * 100, 1) if agg["count"] else 0,
            "avg_pnl": round(agg["pnl_sum"] / agg["count"], 2) if agg["count"] else 0,
            "total_pnl": round(agg["pnl_sum"], 2),
        })
    rows.sort(key=lambda r: abs(r["total_pnl"]), reverse=True)
    return rows


def _timing_impact(closed):
    out = {}
    for bucket in ("on_time", "late", "early"):
        rows = [t for t in closed if t["entry_timing"] == bucket]
        wins = [t for t in rows if t["status"] == "win"]
        out[bucket] = {
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
        }
    return out


def _strategy_breakdown(closed):
    by_strat = defaultdict(list)
    for t in closed:
        by_strat[t["strategy"]].append(t)
    out = []
    for s, rows in by_strat.items():
        wins = [t for t in rows if t["status"] == "win"]
        out.append({
            "strategy": s,
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
            "expectancy": round(sum(t["pnl"] or 0 for t in rows) / len(rows), 2) if rows else 0,
        })
    return out


def _score_bucket_label(score):
    if score >= 85: return "A+"
    if score >= 70: return "B"
    if score >= 55: return "C"
    return "D"


def _edge_composite(closed):
    eligible = [t for t in closed if not t["retroactive"]]
    by_slice = defaultdict(list)
    for t in eligible:
        if t["rules_followed"] is None: continue
        no_mistakes = not t["mistake_tags"]
        key = (t["strategy"], _score_bucket_label(t["setup_score"]),
               bool(t["rules_followed"]), no_mistakes)
        by_slice[key].append(t)

    candidates = [(k, v) for k, v in by_slice.items() if len(v) >= 5]
    if not candidates:
        return {"headline": "Not enough data yet", "count": 0}

    candidates.sort(key=lambda kv: sum(t["pnl"] or 0 for t in kv[1]), reverse=True)
    (strategy, score_bucket, rules_ok, no_mistakes), rows = candidates[0]
    wins = [t for t in rows if t["status"] == "win"]
    rr_vals = [t["rr_achieved"] for t in rows if t["rr_achieved"] is not None]
    headline_parts = [f"{strategy} {score_bucket} setups"]
    if rules_ok: headline_parts.append("plan followed")
    if no_mistakes: headline_parts.append("no mistakes")
    return {
        "headline": ", ".join(headline_parts),
        "filter": {
            "strategy": strategy, "score_bucket": score_bucket,
            "rules_followed": rules_ok, "no_mistakes": no_mistakes,
        },
        "count": len(rows),
        "win_rate": round(len(wins) / len(rows) * 100, 1),
        "avg_rr": round(sum(rr_vals) / len(rr_vals), 2) if rr_vals else 0,
        "total_pnl": round(sum(t["pnl"] or 0 for t in rows), 2),
    }
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_analytics.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/analytics.py backend/tests/test_analytics.py
git commit -m "feat(backend): analytics module with edge composite + tag impact"
```

---

### Task 11: Wire analytics module into the route + add date-range support

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Replace `get_analytics` route**

Find `@app.get("/api/analytics")` (around line 271). Replace:

```python
@app.get("/api/analytics")
def get_analytics(days: int | None = None,
                  start_from: Optional[str] = None,
                  end_to: Optional[str] = None):
    return _compute_analytics_range(start_from, end_to, days)


def _compute_analytics_range(start_from: Optional[str] = None,
                              end_to: Optional[str] = None,
                              days: Optional[int] = 14) -> dict:
    from analytics import compute_analytics
    if start_from and end_to:
        rows = db_trades_between(start_from, end_to)
        period_start, period_end = start_from, end_to
        period_days = None
    else:
        d = days or 14
        cutoff = (datetime.utcnow() - timedelta(days=d)).isoformat()
        rows = db_trades_since(cutoff)
        period_start = cutoff
        period_end = datetime.utcnow().isoformat()
        period_days = d
    trades = [_parse_trade(r) for r in rows]
    return compute_analytics(trades, days=period_days,
                              period_start=period_start, period_end=period_end)
```

- [ ] **Step 2: Add `db_trades_between` to both backends**

In the `if USE_TURSO:` branch, after `db_trades_since`:

```python
    def db_trades_between(start_iso: str, end_iso: str):
        return fetch_all(
            "SELECT * FROM trades WHERE created_at >= ? AND created_at <= ? ORDER BY created_at DESC",
            [start_iso, end_iso],
        )
```

In the `else:` branch, after `db_trades_since`:

```python
    def db_trades_between(start_iso: str, end_iso: str):
        db = _get_db()
        trades = [_trade_to_dict(t) for t in db.execute(
            select(Trade).where(Trade.created_at >= start_iso, Trade.created_at <= end_iso)
                         .order_by(Trade.created_at.desc())
        ).scalars().all()]
        db.close()
        return trades
```

- [ ] **Step 3: Smoke test the new analytics endpoint**

```bash
cd backend && uvicorn main:app --port 8111 &
sleep 3
curl 'http://localhost:8111/api/analytics?days=30' | python -m json.tool | head -40
kill %1
```

Expected: JSON with `plan_adherence`, `risk_discipline`, `mistake_impact`, `edge_composite` keys.

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat(backend): wire analytics module + date-range support"
```

---

## Phase 5 — Frontend foundation

### Task 12: Tag/timing constants and risk helper

**Files:**
- Create: `frontend/src/constants/tags.ts`
- Create: `frontend/src/lib/risk.ts`

- [ ] **Step 1: Constants**

Create `frontend/src/constants/tags.ts`:

```ts
export const MISTAKE_TAGS = [
  "moved_sl", "exited_early", "oversized",
  "chased_entry", "against_trend", "ignored_news",
  "fomo_entry", "no_plan", "revenge_trade", "held_too_long",
] as const;

export const EMOTION_TAGS = [
  "confident", "patient", "anxious", "fearful", "fomo",
  "greedy", "frustrated", "calm", "hesitant", "excited",
] as const;

export const ENTRY_TIMING = ["on_time", "late", "early"] as const;

export const PARTIAL_EXIT_REASONS = [
  "took_profit", "cut_loss", "scaled_out", "sl_adjusted",
] as const;

export const labelize = (tag: string) =>
  tag.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
```

- [ ] **Step 2: Risk helper (frontend mirror of backend logic)**

Create `frontend/src/lib/risk.ts`:

```ts
export function computeRisk(
  entry: number | null,
  stop: number | null,
  positionSize: number | null,
  accountSize: number | null,
): { risk_dollars: number | null; risk_percent: number | null } {
  if (entry == null || stop == null || positionSize == null || accountSize == null) {
    return { risk_dollars: null, risk_percent: null };
  }
  const dollars = Math.round(Math.abs(entry - stop) * positionSize * 10000) / 10000;
  if (accountSize === 0) return { risk_dollars: dollars, risk_percent: null };
  const pct = Math.round((dollars / accountSize) * 100 * 10000) / 10000;
  return { risk_dollars: dollars, risk_percent: pct };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/constants/ frontend/src/lib/
git commit -m "feat(frontend): tag constants + client risk helper"
```

---

### Task 13: Extend `api.ts` with v2 types and methods

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Replace `frontend/src/api.ts` entirely**

```ts
const BASE = import.meta.env.VITE_API_URL || 'https://trading-journal-1-8ork.onrender.com/api'

export type TradeStatus = 'planned' | 'entered' | 'win' | 'loss' | 'breakeven' | 'skipped'
export type EntryTiming = 'on_time' | 'late' | 'early'
export type CloseStatus = 'win' | 'loss' | 'breakeven'

export interface PartialExit {
  price: number
  size_pct: number
  reason: 'took_profit' | 'cut_loss' | 'scaled_out' | 'sl_adjusted'
}

export interface Trade {
  id: number
  pair: string
  direction: 'LONG' | 'SHORT'
  timeframe: string
  strategy: string
  setup_score: number
  verdict: string
  criteria_checked: string[]
  notes: string
  planned_entry: number | null
  planned_stop: number | null
  planned_target: number | null
  planned_rr: number | null
  status: TradeStatus
  retroactive: boolean
  entry_price: number | null
  exit_price: number | null
  stop_loss: number | null
  take_profit: number | null
  position_size: number | null
  account_size: number | null
  risk_dollars: number | null
  risk_percent: number | null
  entry_timing: EntryTiming | null
  emotions_entry: string[]
  feelings_entry: string
  skip_reason: string
  partial_exits: PartialExit[]
  pnl: number | null
  pnl_percent: number | null
  rr_achieved: number | null
  rules_followed: boolean | null
  mistake_tags: string[]
  emotions_exit: string[]
  feelings_exit: string
  lessons: string
  chart_url: string
  created_at: string
  closed_at: string | null
}

export interface Strategy {
  id: number
  name: string
  criteria: { id: string; label: string; points: number; category: string; description: string }[]
  is_core_required: string[]
  created_at: string
}

export interface AccountSnapshot {
  id: number
  balance: number
  recorded_at: string
  note: string
}

export interface Review {
  id: number
  period_type: 'week' | 'month' | 'custom'
  period_start: string
  period_end: string
  notes: string
  stats_snapshot?: AnalyticsData
  created_at: string
}

export interface AnalyticsData {
  period_days: number | null
  period_start: string | null
  period_end: string | null
  total_trades: number
  closed_trades: number
  open_trades: number
  planned_trades: number
  skipped_trades: number
  wins: number
  losses: number
  breakeven: number
  win_rate: number
  total_pnl: number
  avg_score: number
  avg_rr: number
  score_analysis: Record<string, { count: number; win_rate: number; avg_pnl: number }>
  pair_breakdown: Record<string, { wins: number; losses: number; pnl: number }>
  direction_stats: Record<string, { count: number; win_rate: number; pnl: number }>
  plan_adherence: {
    rules_followed_pct: number
    rules_followed_win_rate: number
    rules_broken_win_rate: number
    skip_rate: number
    retroactive_rate: number
  }
  risk_discipline: {
    avg_risk_pct: number
    max_risk_pct: number
    over_threshold_count: number
    histogram: { bucket: string; count: number }[]
  }
  mistake_impact: { tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number }[]
  emotion_impact: {
    entry: { tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number }[]
    exit:  { tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number }[]
  }
  timing_impact: Record<string, { count: number; win_rate: number }>
  strategy_breakdown: { strategy: string; count: number; win_rate: number; expectancy: number }[]
  edge_composite: {
    headline: string
    count: number
    win_rate?: number
    avg_rr?: number
    total_pnl?: number
    filter?: Record<string, unknown>
  }
  trades: Trade[]
}

async function request<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    let msg = `API error: ${res.status}`
    try { const j = await res.json(); if (j.detail) msg = j.detail } catch {}
    throw new Error(msg)
  }
  return res.json()
}

export const api = {
  // Trades
  createPlan: (data: {
    pair: string; direction: string; timeframe: string; strategy: string;
    setup_score: number; verdict: string; criteria_checked: string[]; notes?: string;
    planned_entry?: number | null; planned_stop?: number | null;
    planned_target?: number | null; planned_rr?: number | null;
  }) => request<Trade>('/trades', { method: 'POST', body: JSON.stringify(data) }),

  enterTrade: (id: number, data: {
    entry_price: number; stop_loss: number; take_profit?: number | null;
    position_size: number; account_size: number;
    entry_timing?: EntryTiming | null;
    emotions_entry?: string[]; feelings_entry?: string;
  }) => request<Trade>(`/trades/${id}/enter`, { method: 'POST', body: JSON.stringify(data) }),

  skipTrade: (id: number, data: { skip_reason: string; emotions_entry?: string[] }) =>
    request<Trade>(`/trades/${id}/skip`, { method: 'POST', body: JSON.stringify(data) }),

  closeTrade: (id: number, data: {
    status: CloseStatus; exit_price: number;
    pnl?: number | null; pnl_percent?: number | null; rr_achieved?: number | null;
    rules_followed?: boolean | null;
    mistake_tags?: string[]; emotions_exit?: string[];
    feelings_exit?: string; lessons?: string; chart_url?: string;
    partial_exits?: PartialExit[];
  }) => request<Trade>(`/trades/${id}/close`, { method: 'POST', body: JSON.stringify(data) }),

  createRetroactiveTrade: (data: Record<string, unknown>) =>
    request<Trade>('/trades/retroactive', { method: 'POST', body: JSON.stringify(data) }),

  listTrades: (status?: string) =>
    request<Trade[]>(`/trades${status ? `?status=${status}` : ''}`),

  getTrade: (id: number) => request<Trade>(`/trades/${id}`),

  updateTrade: (id: number, data: Partial<Trade>) =>
    request<Trade>(`/trades/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  deleteTrade: (id: number) =>
    request<{ ok: boolean }>(`/trades/${id}`, { method: 'DELETE' }),

  // Strategies
  listStrategies: () => request<Strategy[]>('/strategies'),
  createStrategy: (data: Omit<Strategy, 'id' | 'created_at'>) =>
    request<Strategy>('/strategies', { method: 'POST', body: JSON.stringify(data) }),
  updateStrategy: (id: number, data: Partial<Strategy>) =>
    request<Strategy>(`/strategies/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteStrategy: (id: number) =>
    request<{ ok: boolean }>(`/strategies/${id}`, { method: 'DELETE' }),

  // Account snapshots
  listSnapshots: () => request<AccountSnapshot[]>('/account-snapshots'),
  createSnapshot: (data: { balance: number; note?: string }) =>
    request<AccountSnapshot>('/account-snapshots', { method: 'POST', body: JSON.stringify(data) }),
  latestSnapshot: () =>
    request<{ balance: number | null }>('/account-snapshots/latest'),

  // Reviews
  listReviews: () => request<Review[]>('/reviews'),
  getReview: (id: number) => request<Review>(`/reviews/${id}`),
  createReview: (data: { period_type: string; period_start: string; period_end: string; notes: string }) =>
    request<Review>('/reviews', { method: 'POST', body: JSON.stringify(data) }),
  deleteReview: (id: number) =>
    request<{ ok: boolean }>(`/reviews/${id}`, { method: 'DELETE' }),

  // Analytics
  getAnalytics: (params: { days?: number; from?: string; to?: string } = {}) => {
    const q = new URLSearchParams()
    if (params.days) q.set('days', String(params.days))
    if (params.from) q.set('start_from', params.from)
    if (params.to) q.set('end_to', params.to)
    return request<AnalyticsData>(`/analytics${q.toString() ? `?${q.toString()}` : ''}`)
  },
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.ts
git commit -m "feat(frontend): extend api.ts with v2 types and endpoints"
```

---

### Task 14: Tab nav layout and shared CSS

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Replace `frontend/src/main.tsx`**

```tsx
import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import PlanForm from './components/PlanForm'
import TradeList from './components/TradeList'
import Review from './components/Review'

type Tab = 'plan' | 'trades' | 'review'

function App() {
  const [tab, setTab] = useState<Tab>('plan')
  return (
    <div className="app">
      <header className="app-header">
        <h1>Trading Journal</h1>
        <nav className="tabs">
          <button onClick={() => setTab('plan')}     className={`tab ${tab === 'plan'   ? 'active' : ''}`}>Plan</button>
          <button onClick={() => setTab('trades')}   className={`tab ${tab === 'trades' ? 'active' : ''}`}>Trades</button>
          <button onClick={() => setTab('review')}   className={`tab ${tab === 'review' ? 'active' : ''}`}>Review</button>
        </nav>
      </header>
      <main className="app-main">
        {tab === 'plan'   && <PlanForm />}
        {tab === 'trades' && <TradeList />}
        {tab === 'review' && <Review />}
      </main>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
```

- [ ] **Step 2: Append CSS for tabs, drawer, chips, etc.**

Append to the end of `frontend/src/index.css`:

```css
/* App layout */
.app { max-width: 720px; margin: 0 auto; padding: 16px; }
.app-header { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
.app-header h1 { font-size: 22px; margin: 0; }
.tabs { display: flex; gap: 8px; }
.tab {
  padding: 8px 16px; border-radius: 8px;
  background: var(--bg2); border: 1px solid var(--border);
  font-size: 14px; cursor: pointer;
}
.tab.active { background: var(--blue); color: #fff; border-color: var(--blue); }

/* Trade Detail Drawer */
.drawer-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.4); z-index: 100;
  display: flex; justify-content: flex-end;
}
.drawer {
  background: var(--bg); width: min(560px, 100%);
  height: 100%; overflow-y: auto; padding: 20px;
  border-left: 1px solid var(--border);
}
@media (max-width: 600px) { .drawer { width: 100%; } }

.accordion { border: 1px solid var(--border); border-radius: 8px; margin-bottom: 12px; }
.accordion-header {
  padding: 12px 14px; cursor: pointer;
  display: flex; justify-content: space-between; align-items: center;
  background: var(--bg2);
}
.accordion-body { padding: 14px; }

/* Tag chips */
.chip-row { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  padding: 5px 12px; border-radius: 999px;
  border: 1px solid var(--border); background: var(--bg2);
  font-size: 12px; cursor: pointer; user-select: none;
}
.chip.selected { background: var(--blue); color: #fff; border-color: var(--blue); }
.chip.mistake.selected { background: var(--red); border-color: var(--red); }

/* Risk display */
.risk-display { font-size: 12px; color: var(--text2); margin-top: 6px; }
.risk-display.warn { color: var(--red); }

/* Status group headings */
.status-group h3 {
  font-size: 13px; text-transform: uppercase; color: var(--text2);
  margin: 16px 0 8px; letter-spacing: .5px;
}
```

- [ ] **Step 3: Run dev server, confirm tabs render**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173. Click each tab. Expected: clicks switch the tab indicator. Components don't exist yet — placeholder errors are fine for now (we'll replace `PlanForm`, `TradeList`, `Review` in next tasks).

If errors block the load, comment out the imports temporarily to verify tab nav, then proceed.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.tsx frontend/src/index.css
git commit -m "feat(frontend): tab navigation and shared CSS for drawer/chips"
```

---

## Phase 6 — Frontend Plan tab

### Task 15: PlanForm component (replace TradeChecklist)

**Files:**
- Delete: `frontend/src/components/TradeChecklist.tsx`
- Create: `frontend/src/components/PlanForm.tsx`

- [ ] **Step 1: Create `frontend/src/components/PlanForm.tsx`**

```tsx
import { useEffect, useState } from "react";
import { api, Strategy } from "../api";

interface FormState {
  pair: string; tf: string; dir: "LONG" | "SHORT";
  notes: string;
  planned_entry: string; planned_stop: string; planned_target: string;
}

const initialForm: FormState = {
  pair: "", tf: "4H", dir: "SHORT",
  notes: "",
  planned_entry: "", planned_stop: "", planned_target: "",
};

export default function PlanForm() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategyId, setStrategyId] = useState<number | null>(null);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [form, setForm] = useState<FormState>(initialForm);
  const [showDesc, setShowDesc] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.listStrategies().then(s => {
      setStrategies(s);
      if (s.length && strategyId == null) setStrategyId(s[0].id);
    });
  }, []);

  const strategy = strategies.find(s => s.id === strategyId);
  const cores = strategy?.is_core_required || [];

  const toggle = (id: string) => setChecked(p => ({ ...p, [id]: !p[id] }));

  const score = strategy
    ? strategy.criteria.reduce((s, c) => s + (checked[c.id] ? c.points : 0), 0)
    : 0;
  const coresMet = cores.every(id => checked[id]);

  const verdict = (() => {
    if (!strategy) return { text: "Select a strategy", color: "var(--text2)" };
    if (score >= 85 && coresMet) return { text: "A+ SETUP -- Full size, this is your edge", color: "var(--green)" };
    if (score >= 70 && coresMet) return { text: "B SETUP -- Reduced size, solid enough",      color: "var(--yellow)" };
    if (score >= 55 && coresMet) return { text: "C SETUP -- Marginal, consider skipping",     color: "#D85A30" };
    if (!coresMet)               return { text: "MISSING CORE -- Do NOT trade",                color: "var(--red)" };
    return { text: "SKIP -- Not enough confluence", color: "var(--red)" };
  })();

  const computedRR = (() => {
    const e = parseFloat(form.planned_entry);
    const s = parseFloat(form.planned_stop);
    const t = parseFloat(form.planned_target);
    if (!isFinite(e) || !isFinite(s) || !isFinite(t) || e === s) return null;
    return Math.round((Math.abs(t - e) / Math.abs(e - s)) * 100) / 100;
  })();

  const reset = () => {
    setChecked({});
    setForm(initialForm);
  };

  const save = async () => {
    if (!form.pair || !strategy || saving) return;
    setSaving(true);
    try {
      const data: Record<string, unknown> = {
        pair: form.pair, direction: form.dir, timeframe: form.tf,
        strategy: strategy.name,
        setup_score: score,
        verdict: verdict.text,
        criteria_checked: Object.keys(checked).filter(k => checked[k]),
        notes: form.notes,
      };
      if (form.planned_entry)  data.planned_entry  = parseFloat(form.planned_entry);
      if (form.planned_stop)   data.planned_stop   = parseFloat(form.planned_stop);
      if (form.planned_target) data.planned_target = parseFloat(form.planned_target);
      if (computedRR != null)  data.planned_rr     = computedRR;
      await api.createPlan(data as Parameters<typeof api.createPlan>[0]);
      setSaved(true);
      reset();
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      alert("Failed to save plan: " + (e instanceof Error ? e.message : "Unknown error"));
    } finally {
      setSaving(false);
    }
  };

  if (!strategy) {
    return <p className="text-2 text-sm">Loading strategies...</p>;
  }

  return (
    <div>
      <div className="flex gap-2 center mb-3">
        <label className="text-sm">Strategy:</label>
        <select value={strategyId ?? ""} onChange={e => setStrategyId(Number(e.target.value))}>
          {strategies.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>

      <div className="flex gap-2 wrap mb-3">
        <input
          placeholder="Pair (e.g. XAG/USD)"
          value={form.pair}
          onChange={e => setForm(p => ({ ...p, pair: e.target.value.toUpperCase() }))}
          style={{ flex: 1, minWidth: 120 }}
        />
        {["1H", "2H", "4H", "1D"].map(t => (
          <button key={t} onClick={() => setForm(p => ({ ...p, tf: t }))}
            className={`btn btn-sm ${form.tf === t ? "btn-primary" : "btn-ghost"}`}>
            {t}
          </button>
        ))}
        {(["SHORT", "LONG"] as const).map(d => (
          <button key={d} onClick={() => setForm(p => ({ ...p, dir: d }))}
            className="btn btn-sm"
            style={{
              background: form.dir === d ? (d === "LONG" ? "var(--green-bg)" : "var(--red-bg)") : "transparent",
              color: d === "LONG" ? "var(--green)" : "var(--red)",
              border: `1.5px solid ${form.dir === d ? (d === "LONG" ? "var(--green)" : "var(--red)") : "var(--border)"}`,
              fontWeight: form.dir === d ? 600 : 400,
            }}>
            {d}
          </button>
        ))}
      </div>

      <div className="flex col gap-2">
        {strategy.criteria.map(c => {
          const isCore = cores.includes(c.id);
          return (
            <div key={c.id}>
              <div onClick={() => toggle(c.id)} className="card" style={{
                cursor: "pointer",
                borderColor: checked[c.id] ? "var(--blue)" : isCore ? "var(--border2)" : "var(--border)",
                background: checked[c.id] ? "var(--blue-bg)" : "var(--bg2)",
                padding: "10px 14px", marginBottom: 0,
              }}>
                <div className="flex center gap-2">
                  <div style={{
                    width: 22, height: 22, borderRadius: 6, flexShrink: 0,
                    border: `2px solid ${checked[c.id] ? "var(--blue)" : "var(--border2)"}`,
                    background: checked[c.id] ? "var(--blue)" : "transparent",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "#fff", fontSize: 14, fontWeight: 700,
                  }}>{checked[c.id] ? "✓" : ""}</div>
                  <div className="grow">
                    <span className="text-sm">{c.label}</span>
                    {isCore && <span className="tag tag-red" style={{ marginLeft: 6 }}>CORE</span>}
                  </div>
                  <span className="text-xs text-2 font-500" style={{ flexShrink: 0 }}>+{c.points}</span>
                  <span onClick={e => { e.stopPropagation(); setShowDesc(showDesc === c.id ? null : c.id); }}
                    style={{
                      width: 20, height: 20, borderRadius: "50%", border: "1px solid var(--border)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 12, color: "var(--text2)", cursor: "pointer", flexShrink: 0,
                    }}>?</span>
                </div>
              </div>
              {showDesc === c.id && (
                <div className="text-xs text-2" style={{ padding: "6px 14px 6px 48px" }}>{c.description}</div>
              )}
            </div>
          );
        })}
      </div>

      <div className="card mt-3" style={{ textAlign: "center", borderColor: verdict.color, borderWidth: 2 }}>
        <div style={{ fontSize: 40, fontWeight: 500, color: verdict.color }}>{score}/100</div>
        <div style={{ fontSize: 15, fontWeight: 500, color: verdict.color, marginTop: 4 }}>{verdict.text}</div>
        {form.pair && <div className="text-sm text-2 mt-2">{form.pair} | {form.dir} | {form.tf}</div>}
      </div>

      <div className="card mt-3">
        <h3 className="text-sm font-500 mb-2">Plan</h3>
        <div className="flex gap-2">
          <div className="grow">
            <label className="text-xs text-2">Planned entry</label>
            <input type="number" step="any" value={form.planned_entry}
              onChange={e => setForm(p => ({ ...p, planned_entry: e.target.value }))} />
          </div>
          <div className="grow">
            <label className="text-xs text-2">Planned stop</label>
            <input type="number" step="any" value={form.planned_stop}
              onChange={e => setForm(p => ({ ...p, planned_stop: e.target.value }))} />
          </div>
          <div className="grow">
            <label className="text-xs text-2">Planned target</label>
            <input type="number" step="any" value={form.planned_target}
              onChange={e => setForm(p => ({ ...p, planned_target: e.target.value }))} />
          </div>
        </div>
        {computedRR != null && (
          <div className="text-xs text-2 mt-2">Planned R:R = {computedRR}</div>
        )}
      </div>

      <textarea
        placeholder="Logic / why this trade"
        value={form.notes}
        rows={3}
        className="mt-3"
        onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
        style={{ resize: "vertical" }}
      />

      <button onClick={save} disabled={!form.pair || saving}
        className="btn btn-primary mt-3" style={{ width: "100%" }}>
        {saved ? "Saved!" : saving ? "Saving..." : form.pair ? `Save Plan: ${form.pair} ${form.dir}` : "Enter pair to save"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Delete the old TradeChecklist**

```bash
rm frontend/src/components/TradeChecklist.tsx
```

- [ ] **Step 3: Run dev server and manually test**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173 with backend running on 8111. Verify:
- Strategy dropdown shows "Zone Failure"
- 11 criteria render
- Checking criteria updates score and verdict
- Filling pair + planned_entry/stop/target shows R:R
- Save button creates a planned trade (verify in DB)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/PlanForm.tsx frontend/src/components/TradeChecklist.tsx
git commit -m "feat(frontend): PlanForm component with strategy dropdown and planned-price inputs"
```

---

### Task 16: StrategyManager modal

**Files:**
- Create: `frontend/src/components/StrategyManager.tsx`
- Modify: `frontend/src/components/PlanForm.tsx` (add Edit Strategy link)

- [ ] **Step 1: Create the modal**

Create `frontend/src/components/StrategyManager.tsx`:

```tsx
import { useEffect, useState } from "react";
import { api, Strategy } from "../api";

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

interface CritDraft { id: string; label: string; points: number; category: string; description: string; is_core: boolean }

export default function StrategyManager({ open, onClose, onSaved }: Props) {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [editing, setEditing] = useState<Strategy | null>(null);
  const [name, setName] = useState("");
  const [crits, setCrits] = useState<CritDraft[]>([]);
  const [saving, setSaving] = useState(false);

  const loadAll = async () => {
    const s = await api.listStrategies();
    setStrategies(s);
  };

  useEffect(() => { if (open) loadAll(); }, [open]);

  const startNew = () => {
    setEditing(null);
    setName("New Strategy");
    setCrits([]);
  };

  const startEdit = (s: Strategy) => {
    setEditing(s);
    setName(s.name);
    setCrits(s.criteria.map(c => ({
      ...c, is_core: s.is_core_required.includes(c.id),
    })));
  };

  const addCrit = () => {
    setCrits(p => [...p, {
      id: `c${p.length + 1}`,
      label: "",
      points: 5,
      category: "Quality",
      description: "",
      is_core: false,
    }]);
  };

  const updateCrit = (i: number, patch: Partial<CritDraft>) => {
    setCrits(p => p.map((c, idx) => idx === i ? { ...c, ...patch } : c));
  };

  const removeCrit = (i: number) => setCrits(p => p.filter((_, idx) => idx !== i));

  const save = async () => {
    if (!name.trim() || saving) return;
    setSaving(true);
    try {
      const payload = {
        name: name.trim(),
        criteria: crits.map(({ is_core: _ic, ...c }) => c),
        is_core_required: crits.filter(c => c.is_core).map(c => c.id),
      };
      if (editing) {
        await api.updateStrategy(editing.id, payload);
      } else {
        await api.createStrategy(payload);
      }
      await loadAll();
      onSaved();
      setEditing(null); setName(""); setCrits([]);
    } catch (e) {
      alert("Save failed: " + (e instanceof Error ? e.message : "Unknown"));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (s: Strategy) => {
    if (!confirm(`Delete strategy "${s.name}"?`)) return;
    try {
      await api.deleteStrategy(s.id);
      await loadAll();
      onSaved();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 720 }}>
        <h3>Strategies</h3>

        {!editing && name === "" ? (
          <>
            <div className="flex col gap-2 mt-2">
              {strategies.map(s => (
                <div key={s.id} className="card flex between center" style={{ padding: "8px 12px" }}>
                  <div>
                    <b>{s.name}</b>
                    <span className="text-xs text-2 ml-2">{s.criteria.length} criteria</span>
                  </div>
                  <div className="flex gap-2">
                    <button className="btn btn-sm btn-ghost" onClick={() => startEdit(s)}>Edit</button>
                    <button className="btn btn-sm btn-ghost" style={{ color: "var(--red)" }} onClick={() => remove(s)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-3" style={{ justifyContent: "flex-end" }}>
              <button className="btn btn-sm btn-ghost" onClick={onClose}>Close</button>
              <button className="btn btn-sm btn-primary" onClick={startNew}>+ New strategy</button>
            </div>
          </>
        ) : (
          <>
            <div className="mt-2">
              <label className="text-xs text-2">Name</label>
              <input value={name} onChange={e => setName(e.target.value)} />
            </div>
            <div className="mt-3">
              <div className="flex between center mb-2">
                <span className="text-sm font-500">Criteria</span>
                <button className="btn btn-sm btn-ghost" onClick={addCrit}>+ Add criterion</button>
              </div>
              {crits.map((c, i) => (
                <div key={i} className="card" style={{ padding: 10, marginBottom: 8 }}>
                  <div className="flex gap-2">
                    <input style={{ flex: 1 }} placeholder="Criterion label"
                      value={c.label} onChange={e => updateCrit(i, { label: e.target.value })} />
                    <input style={{ width: 70 }} type="number" min={0} max={100}
                      value={c.points} onChange={e => updateCrit(i, { points: parseInt(e.target.value || "0") })} />
                  </div>
                  <div className="flex gap-2 mt-1">
                    <input style={{ width: 110 }} placeholder="id" value={c.id}
                      onChange={e => updateCrit(i, { id: e.target.value.replace(/\s+/g, "_") })} />
                    <input style={{ width: 130 }} placeholder="Category" value={c.category}
                      onChange={e => updateCrit(i, { category: e.target.value })} />
                    <label className="flex center gap-1 text-xs">
                      <input type="checkbox" checked={c.is_core}
                        onChange={e => updateCrit(i, { is_core: e.target.checked })} />
                      Core
                    </label>
                    <button className="btn btn-sm btn-ghost" style={{ color: "var(--red)" }}
                      onClick={() => removeCrit(i)}>Remove</button>
                  </div>
                  <input className="mt-1" placeholder="Description (shown on tap of ?)"
                    value={c.description} onChange={e => updateCrit(i, { description: e.target.value })} />
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-3" style={{ justifyContent: "flex-end" }}>
              <button className="btn btn-sm btn-ghost" onClick={() => { setEditing(null); setName(""); setCrits([]); }}>Cancel</button>
              <button className="btn btn-sm btn-primary" onClick={save} disabled={saving}>
                {saving ? "Saving..." : "Save"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add the link in PlanForm**

In `frontend/src/components/PlanForm.tsx`, just below the strategy `<select>`, add:

```tsx
        <button className="btn btn-sm btn-ghost" onClick={() => setShowStrategies(true)}>
          Edit / new strategy
        </button>
```

Add `import StrategyManager from "./StrategyManager";` near the top, and inside `PlanForm` add:

```tsx
  const [showStrategies, setShowStrategies] = useState(false);
```

At the bottom of the returned JSX, before the closing `</div>`, add:

```tsx
      <StrategyManager
        open={showStrategies}
        onClose={() => setShowStrategies(false)}
        onSaved={() => api.listStrategies().then(setStrategies)}
      />
```

- [ ] **Step 3: Manual verification**

Reload the dev server. Click "Edit / new strategy" → modal lists "Zone Failure" → click Edit → modify a criterion → Save → close modal → confirm new criterion appears in checklist.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/StrategyManager.tsx frontend/src/components/PlanForm.tsx
git commit -m "feat(frontend): strategy manager modal"
```

---

## Phase 7 — Frontend Trades tab

### Task 17: Reusable TagChips component

**Files:**
- Create: `frontend/src/components/TagChips.tsx`

- [ ] **Step 1: Create**

```tsx
import { useState } from "react";
import { labelize } from "../constants/tags";

interface Props {
  options: readonly string[] | string[];
  selected: string[];
  onChange: (next: string[]) => void;
  variant?: "default" | "mistake";
  allowCustom?: boolean;
}

export default function TagChips({ options, selected, onChange, variant = "default", allowCustom = true }: Props) {
  const [adding, setAdding] = useState(false);
  const [custom, setCustom] = useState("");

  const toggle = (tag: string) => {
    if (selected.includes(tag)) onChange(selected.filter(t => t !== tag));
    else onChange([...selected, tag]);
  };

  const addCustom = () => {
    const t = custom.trim().toLowerCase().replace(/\s+/g, "_");
    if (t && !selected.includes(t)) onChange([...selected, t]);
    setCustom(""); setAdding(false);
  };

  const allOptions = Array.from(new Set([...options, ...selected]));

  return (
    <div className="chip-row">
      {allOptions.map(t => (
        <span key={t}
          className={`chip ${variant} ${selected.includes(t) ? "selected" : ""}`}
          onClick={() => toggle(t)}>
          {labelize(t)}
        </span>
      ))}
      {allowCustom && !adding && (
        <span className="chip" onClick={() => setAdding(true)}>+ custom</span>
      )}
      {adding && (
        <span className="chip" style={{ padding: 0 }}>
          <input autoFocus
            value={custom}
            onChange={e => setCustom(e.target.value)}
            onBlur={addCustom}
            onKeyDown={e => { if (e.key === "Enter") addCustom(); if (e.key === "Escape") { setAdding(false); setCustom(""); } }}
            style={{ width: 100, border: "none", padding: "4px 8px", background: "transparent" }} />
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TagChips.tsx
git commit -m "feat(frontend): TagChips reusable component"
```

---

### Task 18: PartialExits component

**Files:**
- Create: `frontend/src/components/PartialExits.tsx`

- [ ] **Step 1: Create**

```tsx
import { PartialExit } from "../api";
import { PARTIAL_EXIT_REASONS, labelize } from "../constants/tags";

interface Props {
  value: PartialExit[];
  onChange: (next: PartialExit[]) => void;
}

export default function PartialExits({ value, onChange }: Props) {
  const update = (i: number, patch: Partial<PartialExit>) => {
    onChange(value.map((p, idx) => idx === i ? { ...p, ...patch } : p));
  };
  const remove = (i: number) => onChange(value.filter((_, idx) => idx !== i));
  const add = () => onChange([...value, { price: 0, size_pct: 50, reason: "took_profit" }]);

  return (
    <div className="flex col gap-1">
      {value.map((p, i) => (
        <div key={i} className="flex gap-1 center">
          <input type="number" step="any" placeholder="price" value={p.price || ""}
            onChange={e => update(i, { price: parseFloat(e.target.value) || 0 })} style={{ width: 100 }} />
          <input type="number" step="any" placeholder="size %" value={p.size_pct || ""}
            onChange={e => update(i, { size_pct: parseFloat(e.target.value) || 0 })} style={{ width: 80 }} />
          <select value={p.reason} onChange={e => update(i, { reason: e.target.value as PartialExit["reason"] })}>
            {PARTIAL_EXIT_REASONS.map(r => <option key={r} value={r}>{labelize(r)}</option>)}
          </select>
          <button className="btn btn-sm btn-ghost" onClick={() => remove(i)} style={{ color: "var(--red)" }}>×</button>
        </div>
      ))}
      <button className="btn btn-sm btn-ghost" onClick={add} style={{ alignSelf: "flex-start" }}>+ Add partial exit</button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PartialExits.tsx
git commit -m "feat(frontend): PartialExits component"
```

---

### Task 19: AccountBalanceModal

**Files:**
- Create: `frontend/src/components/AccountBalanceModal.tsx`

- [ ] **Step 1: Create**

```tsx
import { useState } from "react";
import { api } from "../api";

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved: (balance: number) => void;
  current: number | null;
}

export default function AccountBalanceModal({ open, onClose, onSaved, current }: Props) {
  const [balance, setBalance] = useState(current ? String(current) : "");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const save = async () => {
    const b = parseFloat(balance);
    if (!isFinite(b) || saving) return;
    setSaving(true);
    try {
      await api.createSnapshot({ balance: b, note });
      onSaved(b);
      onClose();
    } catch (e) {
      alert("Save failed: " + (e instanceof Error ? e.message : "Unknown"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 380 }}>
        <h3>Update account balance</h3>
        <div className="flex col gap-2 mt-2">
          <label className="text-xs text-2">Balance ($)</label>
          <input type="number" step="any" value={balance}
            onChange={e => setBalance(e.target.value)} autoFocus />
          <label className="text-xs text-2">Note (optional)</label>
          <input value={note} onChange={e => setNote(e.target.value)} placeholder="e.g. Deposit $1000" />
          <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
            <button className="btn btn-sm btn-ghost" onClick={onClose}>Cancel</button>
            <button className="btn btn-sm btn-primary" onClick={save} disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/AccountBalanceModal.tsx
git commit -m "feat(frontend): AccountBalanceModal"
```

---

### Task 20: EnterTradeForm + SkipTradeForm

**Files:**
- Create: `frontend/src/components/EnterTradeForm.tsx`
- Create: `frontend/src/components/SkipTradeForm.tsx`

- [ ] **Step 1: EnterTradeForm**

```tsx
import { useEffect, useState } from "react";
import { api, Trade } from "../api";
import { computeRisk } from "../lib/risk";
import { ENTRY_TIMING, EMOTION_TAGS, labelize } from "../constants/tags";
import TagChips from "./TagChips";
import AccountBalanceModal from "./AccountBalanceModal";

interface Props {
  trade: Trade;
  onSaved: (t: Trade) => void;
  onCancel: () => void;
}

export default function EnterTradeForm({ trade, onSaved, onCancel }: Props) {
  const [entry, setEntry] = useState(trade.planned_entry?.toString() || "");
  const [stop, setStop]  = useState(trade.planned_stop?.toString()  || "");
  const [target, setTarget] = useState(trade.planned_target?.toString() || "");
  const [posSize, setPosSize] = useState("1");
  const [acctSize, setAcctSize] = useState<string>("");
  const [timing, setTiming] = useState<typeof ENTRY_TIMING[number] | "">("on_time");
  const [emotions, setEmotions] = useState<string[]>([]);
  const [feelings, setFeelings] = useState("");
  const [showBalance, setShowBalance] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.latestSnapshot().then(s => {
      if (s.balance != null) setAcctSize(String(s.balance));
    });
  }, []);

  const e = parseFloat(entry); const s = parseFloat(stop);
  const ps = parseFloat(posSize); const ac = parseFloat(acctSize);
  const risk = computeRisk(
    isFinite(e) ? e : null,
    isFinite(s) ? s : null,
    isFinite(ps) ? ps : null,
    isFinite(ac) ? ac : null,
  );

  const save = async () => {
    if (!entry || !stop || !posSize || !acctSize || saving) return;
    setSaving(true);
    try {
      const t = await api.enterTrade(trade.id, {
        entry_price: parseFloat(entry),
        stop_loss: parseFloat(stop),
        take_profit: target ? parseFloat(target) : null,
        position_size: parseFloat(posSize),
        account_size: parseFloat(acctSize),
        entry_timing: (timing || null) as Props["trade"]["entry_timing"],
        emotions_entry: emotions,
        feelings_entry: feelings,
      });
      onSaved(t);
    } catch (err) {
      alert("Failed: " + (err instanceof Error ? err.message : "Unknown"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex col gap-2">
      <div className="flex gap-2">
        <div className="grow">
          <label className="text-xs text-2">Actual entry</label>
          <input type="number" step="any" value={entry} onChange={ev => setEntry(ev.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">Actual stop</label>
          <input type="number" step="any" value={stop} onChange={ev => setStop(ev.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">Take profit</label>
          <input type="number" step="any" value={target} onChange={ev => setTarget(ev.target.value)} />
        </div>
      </div>

      <div className="flex gap-2 center">
        <div className="grow">
          <label className="text-xs text-2">Position size</label>
          <input type="number" step="any" value={posSize} onChange={ev => setPosSize(ev.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">Account size ($)</label>
          <input type="number" step="any" value={acctSize} onChange={ev => setAcctSize(ev.target.value)} />
        </div>
        <button className="btn btn-sm btn-ghost" style={{ marginTop: 16 }}
          onClick={() => setShowBalance(true)}>Update</button>
      </div>

      {risk.risk_dollars != null && (
        <div className={`risk-display ${risk.risk_percent != null && risk.risk_percent > 2 ? "warn" : ""}`}>
          Risk: ${risk.risk_dollars}
          {risk.risk_percent != null && ` (${risk.risk_percent}% of account)`}
        </div>
      )}

      <div>
        <label className="text-xs text-2">Entry timing</label>
        <div className="flex gap-1 mt-1">
          {ENTRY_TIMING.map(t => (
            <button key={t} className={`btn btn-sm ${timing === t ? "btn-primary" : "btn-ghost"}`}
              onClick={() => setTiming(t)}>{labelize(t)}</button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs text-2">Feelings at entry</label>
        <TagChips options={EMOTION_TAGS} selected={emotions} onChange={setEmotions} />
      </div>

      <textarea placeholder="What was going through my head"
        value={feelings} onChange={ev => setFeelings(ev.target.value)} rows={2} />

      <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-sm btn-ghost" onClick={onCancel}>Cancel</button>
        <button className="btn btn-sm btn-primary" onClick={save} disabled={saving}>
          {saving ? "Saving..." : "Mark as Entered"}
        </button>
      </div>

      <AccountBalanceModal
        open={showBalance}
        onClose={() => setShowBalance(false)}
        current={isFinite(ac) ? ac : null}
        onSaved={(b) => setAcctSize(String(b))}
      />
    </div>
  );
}
```

- [ ] **Step 2: SkipTradeForm**

```tsx
import { useState } from "react";
import { api, Trade } from "../api";
import { EMOTION_TAGS } from "../constants/tags";
import TagChips from "./TagChips";

interface Props {
  trade: Trade;
  onSaved: (t: Trade) => void;
  onCancel: () => void;
}

export default function SkipTradeForm({ trade, onSaved, onCancel }: Props) {
  const [reason, setReason] = useState("");
  const [emotions, setEmotions] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!reason.trim() || saving) return;
    setSaving(true);
    try {
      const t = await api.skipTrade(trade.id, { skip_reason: reason, emotions_entry: emotions });
      onSaved(t);
    } catch (err) {
      alert("Failed: " + (err instanceof Error ? err.message : "Unknown"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex col gap-2">
      <div>
        <label className="text-xs text-2">Why did you skip this trade?</label>
        <input value={reason} onChange={e => setReason(e.target.value)} placeholder="e.g. News in 1h" />
      </div>
      <div>
        <label className="text-xs text-2">Feelings</label>
        <TagChips options={EMOTION_TAGS} selected={emotions} onChange={setEmotions} />
      </div>
      <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-sm btn-ghost" onClick={onCancel}>Cancel</button>
        <button className="btn btn-sm btn-primary" onClick={save} disabled={saving || !reason.trim()}>
          {saving ? "Saving..." : "Mark as Skipped"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/EnterTradeForm.tsx frontend/src/components/SkipTradeForm.tsx
git commit -m "feat(frontend): EnterTradeForm and SkipTradeForm"
```

---

### Task 21: CloseTradeForm

**Files:**
- Create: `frontend/src/components/CloseTradeForm.tsx`

- [ ] **Step 1: Create**

```tsx
import { useState } from "react";
import { api, Trade, PartialExit, CloseStatus } from "../api";
import { MISTAKE_TAGS, EMOTION_TAGS } from "../constants/tags";
import TagChips from "./TagChips";
import PartialExits from "./PartialExits";

interface Props {
  trade: Trade;
  onSaved: (t: Trade) => void;
  onCancel: () => void;
}

export default function CloseTradeForm({ trade, onSaved, onCancel }: Props) {
  const [status, setStatus] = useState<CloseStatus>("win");
  const [exitPrice, setExitPrice] = useState(trade.exit_price?.toString() || "");
  const [pnl, setPnl] = useState(trade.pnl?.toString() || "");
  const [pnlPct, setPnlPct] = useState(trade.pnl_percent?.toString() || "");
  const [rr, setRr] = useState(trade.rr_achieved?.toString() || "");
  const [rulesFollowed, setRulesFollowed] = useState<boolean | null>(true);
  const [mistakes, setMistakes] = useState<string[]>(trade.mistake_tags || []);
  const [emotions, setEmotions] = useState<string[]>(trade.emotions_exit || []);
  const [feelings, setFeelings] = useState(trade.feelings_exit || "");
  const [lessons, setLessons] = useState(trade.lessons || "");
  const [chartUrl, setChartUrl] = useState(trade.chart_url || "");
  const [partials, setPartials] = useState<PartialExit[]>(trade.partial_exits || []);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!exitPrice || saving) return;
    setSaving(true);
    try {
      const t = await api.closeTrade(trade.id, {
        status,
        exit_price: parseFloat(exitPrice),
        pnl: pnl ? parseFloat(pnl) : null,
        pnl_percent: pnlPct ? parseFloat(pnlPct) : null,
        rr_achieved: rr ? parseFloat(rr) : null,
        rules_followed: rulesFollowed,
        mistake_tags: mistakes,
        emotions_exit: emotions,
        feelings_exit: feelings,
        lessons,
        chart_url: chartUrl,
        partial_exits: partials,
      });
      onSaved(t);
    } catch (err) {
      alert("Failed: " + (err instanceof Error ? err.message : "Unknown"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex col gap-2">
      <div className="flex gap-1">
        {(["win", "loss", "breakeven"] as CloseStatus[]).map(s => (
          <button key={s} className={`btn btn-sm ${status === s ? "btn-primary" : "btn-ghost"}`}
            style={{ background: status === s ? (s === "win" ? "var(--green)" : s === "loss" ? "var(--red)" : "var(--yellow)") : undefined }}
            onClick={() => setStatus(s)}>{s.toUpperCase()}</button>
        ))}
      </div>

      <div className="flex gap-2">
        <div className="grow">
          <label className="text-xs text-2">Exit price</label>
          <input type="number" step="any" value={exitPrice} onChange={e => setExitPrice(e.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">P/L ($)</label>
          <input type="number" step="any" value={pnl} onChange={e => setPnl(e.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">P/L %</label>
          <input type="number" step="any" value={pnlPct} onChange={e => setPnlPct(e.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">R:R</label>
          <input type="number" step="any" value={rr} onChange={e => setRr(e.target.value)} />
        </div>
      </div>

      <div>
        <label className="text-xs text-2">Partial exits</label>
        <PartialExits value={partials} onChange={setPartials} />
      </div>

      <div>
        <label className="text-xs text-2">Did you follow your plan?</label>
        <div className="flex gap-1 mt-1">
          <button className={`btn btn-sm ${rulesFollowed === true ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setRulesFollowed(true)}>Yes</button>
          <button className={`btn btn-sm ${rulesFollowed === false ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setRulesFollowed(false)}>No</button>
        </div>
      </div>

      <div>
        <label className="text-xs text-2">Mistakes</label>
        <TagChips options={MISTAKE_TAGS} selected={mistakes} onChange={setMistakes} variant="mistake" />
      </div>

      <div>
        <label className="text-xs text-2">Feelings at exit</label>
        <TagChips options={EMOTION_TAGS} selected={emotions} onChange={setEmotions} />
      </div>

      <textarea placeholder="What was going through my head" rows={2}
        value={feelings} onChange={e => setFeelings(e.target.value)} />

      <textarea placeholder="Lessons learned" rows={3}
        value={lessons} onChange={e => setLessons(e.target.value)} />

      <input placeholder="TradingView chart URL"
        value={chartUrl} onChange={e => setChartUrl(e.target.value)} />

      <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-sm btn-ghost" onClick={onCancel}>Cancel</button>
        <button className="btn btn-sm btn-primary" onClick={save} disabled={saving || !exitPrice}>
          {saving ? "Saving..." : "Close Trade"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CloseTradeForm.tsx
git commit -m "feat(frontend): CloseTradeForm with mistakes/emotions/partials"
```

---

### Task 22: TradeDetail drawer

**Files:**
- Create: `frontend/src/components/TradeDetail.tsx`

- [ ] **Step 1: Create**

```tsx
import { useState } from "react";
import { api, Trade } from "../api";
import EnterTradeForm from "./EnterTradeForm";
import SkipTradeForm from "./SkipTradeForm";
import CloseTradeForm from "./CloseTradeForm";
import { labelize } from "../constants/tags";

interface Props {
  trade: Trade;
  onClose: () => void;
  onChanged: (t: Trade | null) => void;  // null = deleted
}

type Section = "plan" | "execution" | "result";
type Mode = "view" | "enter" | "skip" | "close";

export default function TradeDetail({ trade, onClose, onChanged }: Props) {
  const [open, setOpen] = useState<Section>("plan");
  const [mode, setMode] = useState<Mode>("view");

  const remove = async () => {
    if (!confirm("Delete this trade?")) return;
    await api.deleteTrade(trade.id);
    onChanged(null);
    onClose();
  };

  const Plan = (
    <div>
      <div className="flex gap-2 wrap mb-2">
        <span className="font-500">{trade.pair}</span>
        <span className={`tag ${trade.direction === "LONG" ? "tag-green" : "tag-red"}`}>{trade.direction}</span>
        <span className="tag tag-blue">{trade.timeframe}</span>
        <span className="tag tag-blue">{trade.strategy}</span>
        <span className="font-500">{trade.setup_score}/100</span>
      </div>
      <div className="text-xs text-2">{trade.verdict}</div>
      {(trade.planned_entry != null || trade.planned_stop != null || trade.planned_target != null) && (
        <div className="text-sm mt-2">
          Plan: entry {trade.planned_entry ?? "—"} · stop {trade.planned_stop ?? "—"} · target {trade.planned_target ?? "—"}
          {trade.planned_rr != null && ` · R:R ${trade.planned_rr}`}
        </div>
      )}
      {trade.notes && <div className="text-sm text-2 mt-2" style={{ fontStyle: "italic" }}>{trade.notes}</div>}
    </div>
  );

  const Execution = trade.status === "planned" ? (
    <div className="flex gap-2">
      <button className="btn btn-sm btn-primary" onClick={() => setMode("enter")}>Mark as Entered</button>
      <button className="btn btn-sm btn-ghost" onClick={() => setMode("skip")}>Mark as Skipped</button>
    </div>
  ) : trade.status === "skipped" ? (
    <div className="text-sm">
      <b>Skipped</b> — {trade.skip_reason}
      {trade.emotions_entry.length > 0 && (
        <div className="text-xs text-2 mt-1">Felt: {trade.emotions_entry.map(labelize).join(", ")}</div>
      )}
    </div>
  ) : (
    <div className="text-sm">
      Entry {trade.entry_price ?? "—"} · Stop {trade.stop_loss ?? "—"} · TP {trade.take_profit ?? "—"}<br/>
      Position {trade.position_size ?? "—"} · Account ${trade.account_size ?? "—"}<br/>
      <b>Risk:</b> ${trade.risk_dollars ?? "—"} ({trade.risk_percent ?? "—"}% of account)
      {trade.entry_timing && <span> · {labelize(trade.entry_timing)}</span>}
      {trade.emotions_entry.length > 0 && (
        <div className="text-xs text-2 mt-1">Felt at entry: {trade.emotions_entry.map(labelize).join(", ")}</div>
      )}
      {trade.feelings_entry && (
        <div className="text-xs text-2 mt-1" style={{ fontStyle: "italic" }}>{trade.feelings_entry}</div>
      )}
    </div>
  );

  const Result = trade.status === "entered" ? (
    <button className="btn btn-sm btn-primary" onClick={() => setMode("close")}>Close Trade</button>
  ) : ["win", "loss", "breakeven"].includes(trade.status) ? (
    <div className="text-sm">
      <b style={{ color: trade.status === "win" ? "var(--green)" : trade.status === "loss" ? "var(--red)" : "var(--yellow)" }}>
        {trade.status.toUpperCase()}
      </b>
      {" "}· Exit {trade.exit_price ?? "—"}
      {trade.pnl != null && <> · P/L ${trade.pnl}</>}
      {trade.rr_achieved != null && <> · R:R {trade.rr_achieved}</>}
      <div className="mt-1">
        Plan followed: <b>{trade.rules_followed === true ? "Yes" : trade.rules_followed === false ? "No" : "—"}</b>
      </div>
      {trade.mistake_tags.length > 0 && (
        <div className="mt-1 text-xs text-2">Mistakes: {trade.mistake_tags.map(labelize).join(", ")}</div>
      )}
      {trade.emotions_exit.length > 0 && (
        <div className="mt-1 text-xs text-2">Felt at exit: {trade.emotions_exit.map(labelize).join(", ")}</div>
      )}
      {trade.lessons && (
        <div className="mt-2 text-sm" style={{ fontStyle: "italic" }}>Lessons: {trade.lessons}</div>
      )}
      {trade.chart_url && (
        <div className="mt-2"><a href={trade.chart_url} target="_blank" rel="noreferrer">📈 Chart</a></div>
      )}
    </div>
  ) : (
    <div className="text-2 text-xs">Mark as Entered first.</div>
  );

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={e => e.stopPropagation()}>
        <div className="flex between center mb-3">
          <h2 style={{ fontSize: 18 }}>{trade.pair} {trade.direction}</h2>
          <button className="btn btn-sm btn-ghost" onClick={onClose}>×</button>
        </div>

        {mode === "view" && (
          <>
            <Section title="Plan" body={Plan} open={open === "plan"} onToggle={() => setOpen("plan")} />
            <Section title="Execution" body={Execution} open={open === "execution"} onToggle={() => setOpen("execution")} />
            <Section title="Result" body={Result} open={open === "result"} onToggle={() => setOpen("result")} />

            <div className="flex gap-2 mt-3" style={{ justifyContent: "flex-end" }}>
              <button className="btn btn-sm btn-ghost" style={{ color: "var(--red)" }} onClick={remove}>Delete trade</button>
            </div>
          </>
        )}
        {mode === "enter" && (
          <EnterTradeForm trade={trade}
            onSaved={t => { setMode("view"); onChanged(t); }}
            onCancel={() => setMode("view")} />
        )}
        {mode === "skip" && (
          <SkipTradeForm trade={trade}
            onSaved={t => { setMode("view"); onChanged(t); }}
            onCancel={() => setMode("view")} />
        )}
        {mode === "close" && (
          <CloseTradeForm trade={trade}
            onSaved={t => { setMode("view"); onChanged(t); }}
            onCancel={() => setMode("view")} />
        )}
      </div>
    </div>
  );
}

function Section({ title, body, open, onToggle }: {
  title: string; body: React.ReactNode; open: boolean; onToggle: () => void;
}) {
  return (
    <div className="accordion">
      <div className="accordion-header" onClick={onToggle}>
        <b>{title}</b>
        <span>{open ? "▾" : "▸"}</span>
      </div>
      {open && <div className="accordion-body">{body}</div>}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TradeDetail.tsx
git commit -m "feat(frontend): TradeDetail drawer with stage forms"
```

---

### Task 23: TradeList grouped by status

**Files:**
- Modify: `frontend/src/components/TradeList.tsx`

- [ ] **Step 1: Replace entirely**

```tsx
import { useEffect, useState } from "react";
import { api, Trade, TradeStatus } from "../api";
import TradeDetail from "./TradeDetail";

const GROUPS: { label: string; statuses: TradeStatus[] }[] = [
  { label: "Planned", statuses: ["planned"] },
  { label: "Open",    statuses: ["entered"] },
  { label: "Closed",  statuses: ["win", "loss", "breakeven"] },
  { label: "Skipped", statuses: ["skipped"] },
];

export default function TradeList() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [active, setActive] = useState<Trade | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setTrades(await api.listTrades());
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const groups = GROUPS.map(g => ({
    ...g,
    trades: trades.filter(t => g.statuses.includes(t.status)),
  })).filter(g => g.trades.length > 0);

  const onChanged = (t: Trade | null) => {
    if (t) setActive(t);
    load();
  };

  if (loading) return <p className="text-2 text-sm">Loading...</p>;
  if (trades.length === 0) return <p className="text-2 text-sm">No trades yet. Plan one!</p>;

  return (
    <div>
      {groups.map(g => (
        <div key={g.label} className="status-group">
          <h3>{g.label} ({g.trades.length})</h3>
          {g.trades.map(t => <TradeCard key={t.id} trade={t} onClick={() => setActive(t)} />)}
        </div>
      ))}
      {active && <TradeDetail trade={active} onClose={() => setActive(null)} onChanged={onChanged} />}
    </div>
  );
}

function TradeCard({ trade, onClick }: { trade: Trade; onClick: () => void }) {
  const border = trade.setup_score >= 85 ? "var(--green)"
              : trade.setup_score >= 70 ? "var(--yellow)"
              : trade.setup_score >= 55 ? "#D85A30" : "var(--red)";
  const statusColor = trade.status === "win" ? "tag-green"
                    : trade.status === "loss" ? "tag-red"
                    : trade.status === "breakeven" ? "tag-yellow"
                    : "tag-blue";
  return (
    <div className="card" style={{ borderLeft: `3px solid ${border}`, cursor: "pointer" }} onClick={onClick}>
      <div className="flex between center">
        <div className="flex gap-2 center wrap">
          <span className="font-500">{trade.pair}</span>
          <span className={`tag ${trade.direction === "LONG" ? "tag-green" : "tag-red"}`}>{trade.direction}</span>
          <span className="tag tag-blue">{trade.timeframe}</span>
          <span className={`tag ${statusColor}`}>{trade.status.toUpperCase()}</span>
          {trade.retroactive && <span className="tag" style={{ background: "var(--bg2)", color: "var(--text2)" }}>RETRO</span>}
        </div>
        <span className="font-500">{trade.setup_score}/100</span>
      </div>
      <div className="text-xs text-2 mt-2">
        {new Date(trade.created_at).toLocaleString()}
        {trade.risk_percent != null && <span> · risk {trade.risk_percent}%</span>}
        {trade.pnl != null && <span> · P/L ${trade.pnl}</span>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Manual verification**

Reload the dev server. Plan a trade in Plan tab → switch to Trades → see it under Planned. Click → drawer opens → "Mark as Entered" → fill form → save → status changes to OPEN. Click again → "Close Trade" → fill → save → moves to CLOSED.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TradeList.tsx
git commit -m "feat(frontend): TradeList grouped by status with drawer"
```

---

## Phase 8 — Frontend Review tab

### Task 24: Review component (replaces Analytics)

**Files:**
- Delete: `frontend/src/components/Analytics.tsx`
- Create: `frontend/src/components/Review.tsx`

- [ ] **Step 1: Create**

```tsx
import { useEffect, useState } from "react";
import { api, AnalyticsData, Review as ReviewT } from "../api";
import { labelize } from "../constants/tags";

const PRESETS = [
  { id: "7",   label: "7 days",  days: 7 },
  { id: "14",  label: "14 days", days: 14 },
  { id: "30",  label: "30 days", days: 30 },
  { id: "90",  label: "90 days", days: 90 },
] as const;

export default function Review() {
  const [preset, setPreset] = useState<typeof PRESETS[number]["id"] | "custom">("14");
  const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [reviews, setReviews] = useState<ReviewT[]>([]);
  const [showWrite, setShowWrite] = useState(false);
  const [reviewBody, setReviewBody] = useState("");
  const [savingReview, setSavingReview] = useState(false);
  const [activeReview, setActiveReview] = useState<ReviewT | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      let d: AnalyticsData;
      if (preset === "custom" && from && to) {
        d = await api.getAnalytics({ from, to });
      } else if (preset !== "custom") {
        const days = PRESETS.find(p => p.id === preset)?.days || 14;
        d = await api.getAnalytics({ days });
      } else {
        return;
      }
      setData(d);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [preset, from, to]);
  useEffect(() => { api.listReviews().then(setReviews); }, []);

  const saveReview = async () => {
    if (!data || !reviewBody.trim() || savingReview) return;
    setSavingReview(true);
    try {
      const r = await api.createReview({
        period_type: preset === "custom" ? "custom" : preset === "30" ? "month" : "week",
        period_start: data.period_start || "",
        period_end: data.period_end || "",
        notes: reviewBody,
      });
      setReviews(prev => [r, ...prev]);
      setReviewBody(""); setShowWrite(false);
    } finally {
      setSavingReview(false);
    }
  };

  const view = activeReview?.stats_snapshot || data;

  return (
    <div>
      <div className="flex gap-2 wrap mb-3 center">
        {PRESETS.map(p => (
          <button key={p.id}
            className={`btn btn-sm ${preset === p.id ? "btn-primary" : "btn-ghost"}`}
            onClick={() => { setPreset(p.id); setActiveReview(null); }}>
            {p.label}
          </button>
        ))}
        <button className={`btn btn-sm ${preset === "custom" ? "btn-primary" : "btn-ghost"}`}
          onClick={() => { setPreset("custom"); setActiveReview(null); }}>
          Custom
        </button>
        {preset === "custom" && (
          <>
            <input type="date" value={from} onChange={e => setFrom(e.target.value)} />
            <input type="date" value={to}   onChange={e => setTo(e.target.value)} />
          </>
        )}
      </div>

      {activeReview && (
        <div className="card" style={{ background: "var(--blue-bg)" }}>
          <div className="flex between center">
            <b>Viewing saved review: {activeReview.period_start?.slice(0,10)} → {activeReview.period_end?.slice(0,10)}</b>
            <button className="btn btn-sm btn-ghost" onClick={() => setActiveReview(null)}>Close</button>
          </div>
          <div className="text-sm mt-2" style={{ whiteSpace: "pre-wrap" }}>{activeReview.notes}</div>
        </div>
      )}

      {loading && !view && <p className="text-2 text-sm">Loading...</p>}
      {view && <Stats d={view} />}

      <div className="status-group">
        <h3>Saved reviews</h3>
        {reviews.length === 0 ? (
          <p className="text-2 text-xs">None yet.</p>
        ) : reviews.map(r => (
          <div key={r.id} className="card flex between center" style={{ padding: "8px 12px", cursor: "pointer" }}
            onClick={async () => setActiveReview(await api.getReview(r.id))}>
            <div>
              <b>{r.period_start?.slice(0,10)} → {r.period_end?.slice(0,10)}</b>
              <div className="text-xs text-2">{r.notes.slice(0, 80)}{r.notes.length > 80 ? "..." : ""}</div>
            </div>
            <button className="btn btn-sm btn-ghost" style={{ color: "var(--red)" }}
              onClick={async (e) => { e.stopPropagation(); if (confirm("Delete review?")) {
                await api.deleteReview(r.id);
                setReviews(prev => prev.filter(x => x.id !== r.id));
              }}}>Delete</button>
          </div>
        ))}
      </div>

      {!activeReview && !showWrite && (
        <button className="btn btn-primary mt-3" onClick={() => setShowWrite(true)} style={{ width: "100%" }}>
          + Write review for this period
        </button>
      )}
      {showWrite && (
        <div className="card mt-3">
          <textarea rows={5} placeholder="Reflection on this period..."
            value={reviewBody} onChange={e => setReviewBody(e.target.value)} />
          <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
            <button className="btn btn-sm btn-ghost" onClick={() => setShowWrite(false)}>Cancel</button>
            <button className="btn btn-sm btn-primary" onClick={saveReview} disabled={savingReview}>
              {savingReview ? "Saving..." : "Save review"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Stats({ d }: { d: AnalyticsData }) {
  return (
    <div className="flex col gap-3">
      <div className="card">
        <div className="flex between center">
          <span><b>{d.total_trades}</b> trades · <b>{d.closed_trades}</b> closed · <b>{d.skipped_trades}</b> skipped</span>
          <span><b style={{ color: d.total_pnl >= 0 ? "var(--green)" : "var(--red)" }}>${d.total_pnl}</b></span>
        </div>
        <div className="text-sm text-2 mt-1">
          Win rate {d.win_rate}% · Avg score {d.avg_score} · Avg R {d.avg_rr}
        </div>
      </div>

      {d.edge_composite && (
        <div className="card" style={{ borderColor: "var(--green)", borderWidth: 2 }}>
          <div className="text-xs text-2">YOUR EDGE</div>
          <div className="font-500">{d.edge_composite.headline}</div>
          {d.edge_composite.count > 0 && (
            <div className="text-sm mt-1">
              {d.edge_composite.count} trades · {d.edge_composite.win_rate}% win rate
              {d.edge_composite.avg_rr != null && ` · ${d.edge_composite.avg_rr} avg R`}
              {d.edge_composite.total_pnl != null && ` · $${d.edge_composite.total_pnl} total P/L`}
            </div>
          )}
        </div>
      )}

      <div className="card">
        <h4 className="text-sm mb-2">Plan adherence</h4>
        <div className="text-sm">
          Rules followed {d.plan_adherence.rules_followed_pct}% of the time<br/>
          Win rate when followed: <b>{d.plan_adherence.rules_followed_win_rate}%</b><br/>
          Win rate when broken: <b>{d.plan_adherence.rules_broken_win_rate}%</b><br/>
          Skip rate: {d.plan_adherence.skip_rate}% · Retroactive: {d.plan_adherence.retroactive_rate}%
        </div>
      </div>

      <div className="card">
        <h4 className="text-sm mb-2">Risk discipline</h4>
        <div className="text-sm">
          Avg risk {d.risk_discipline.avg_risk_pct}% · Max {d.risk_discipline.max_risk_pct}%
          {d.risk_discipline.over_threshold_count > 0 && (
            <span style={{ color: "var(--red)" }}> · {d.risk_discipline.over_threshold_count} over threshold</span>
          )}
        </div>
        <div className="text-xs text-2 mt-1">
          {d.risk_discipline.histogram.map(b => (
            <span key={b.bucket} style={{ marginRight: 12 }}>
              {b.bucket}: {b.count}
            </span>
          ))}
        </div>
      </div>

      {d.mistake_impact.length > 0 && (
        <div className="card">
          <h4 className="text-sm mb-2">Mistake impact</h4>
          <table className="text-sm" style={{ width: "100%" }}>
            <thead>
              <tr><th align="left">Tag</th><th>Count</th><th>Win %</th><th>Total P/L</th></tr>
            </thead>
            <tbody>
              {d.mistake_impact.map(r => (
                <tr key={r.tag}>
                  <td>{r.tag === "(none)" ? <i>No mistakes</i> : labelize(r.tag)}</td>
                  <td align="center">{r.count}</td>
                  <td align="center">{r.win_rate}%</td>
                  <td align="right" style={{ color: r.total_pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                    ${r.total_pnl}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(d.emotion_impact.entry.length > 0 || d.emotion_impact.exit.length > 0) && (
        <div className="card">
          <h4 className="text-sm mb-2">Emotion impact</h4>
          <EmotionTable label="Entry" rows={d.emotion_impact.entry} />
          <EmotionTable label="Exit" rows={d.emotion_impact.exit} />
        </div>
      )}

      <div className="card">
        <h4 className="text-sm mb-2">Timing</h4>
        {Object.entries(d.timing_impact).map(([k, v]) => (
          <span key={k} style={{ marginRight: 16 }} className="text-sm">
            {labelize(k)}: <b>{v.count}</b> ({v.win_rate}% win)
          </span>
        ))}
      </div>

      {d.strategy_breakdown.length > 1 && (
        <div className="card">
          <h4 className="text-sm mb-2">Strategy breakdown</h4>
          {d.strategy_breakdown.map(s => (
            <div key={s.strategy} className="text-sm">
              <b>{s.strategy}</b>: {s.count} trades · {s.win_rate}% win · expectancy ${s.expectancy}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EmotionTable({ label, rows }: { label: string;
  rows: { tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number }[] }) {
  if (!rows.length) return null;
  return (
    <div className="mt-2">
      <div className="text-xs text-2">{label}</div>
      {rows.slice(0, 5).map(r => (
        <div key={r.tag} className="text-sm flex between" style={{ paddingTop: 2 }}>
          <span>{labelize(r.tag)}</span>
          <span>{r.count} · {r.win_rate}% · <b style={{ color: r.total_pnl >= 0 ? "var(--green)" : "var(--red)" }}>${r.total_pnl}</b></span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Delete the old Analytics**

```bash
rm frontend/src/components/Analytics.tsx
```

- [ ] **Step 3: Manual verification**

Reload the dev server. Switch to Review tab. With at least one closed trade, all panels render. Click 7d/14d/30d → results update. Custom date range works. Write a review → appears in Saved reviews → click → re-shows the snapshot. Delete a review.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Review.tsx frontend/src/components/Analytics.tsx
git commit -m "feat(frontend): Review tab with edge composite, mistake/emotion tables, saved reviews"
```

---

## Phase 9 — Smoke test, deploy, manual verification

### Task 25: End-to-end smoke script

**Files:**
- Create: `trading-journal/scripts/e2e_smoke.py`

- [ ] **Step 1: Create**

```bash
mkdir -p scripts
```

Create `scripts/e2e_smoke.py`:

```python
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
    # 1. Health
    h = requests.get(f"{BASE}/").json()
    assert h["status"] == "ok"
    print("✓ Health check")

    # 2. Strategies seeded
    strategies = call("GET", "/api/strategies")
    assert any(s["name"] == "Zone Failure" for s in strategies), strategies
    print(f"✓ Strategies: {[s['name'] for s in strategies]}")

    # 3. Plan a trade
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

    # 4. Enter
    entered = call("POST", f"/api/trades/{tid}/enter", json={
        "entry_price": 100.5, "stop_loss": 95.0,
        "position_size": 1.0, "account_size": 10000.0,
        "entry_timing": "on_time", "emotions_entry": ["confident"],
    })
    assert entered["status"] == "entered"
    assert abs(entered["risk_dollars"] - 5.5) < 0.001
    print(f"✓ Entered (risk ${entered['risk_dollars']})")

    # 5. Close
    closed = call("POST", f"/api/trades/{tid}/close", json={
        "status": "win", "exit_price": 110.0,
        "pnl": 9.5, "rr_achieved": 1.7,
        "rules_followed": True,
        "mistake_tags": [], "emotions_exit": ["calm"],
        "lessons": "Smoke test passed",
    })
    assert closed["status"] == "win"
    print("✓ Closed as WIN")

    # 6. Analytics see the trade
    a = call("GET", "/api/analytics?days=1")
    assert a["closed_trades"] >= 1
    print(f"✓ Analytics: {a['closed_trades']} closed, {a['total_pnl']} total P/L")

    # 7. Cleanup
    call("DELETE", f"/api/trades/{tid}")
    print("✓ Cleanup")

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run against local backend**

```bash
cd backend && uvicorn main:app --port 8111 &
sleep 3
cd .. && python scripts/e2e_smoke.py http://localhost:8111
kill %1
```

Expected: all 7 ✓ checks pass.

- [ ] **Step 3: Commit**

```bash
git add scripts/e2e_smoke.py
git commit -m "test: e2e smoke script for v2 API"
```

---

### Task 26: Manual verification + deploy

- [ ] **Step 1: Manual frontend verification (local)**

Start backend on 8111 and frontend on 5173. Verify each item:

- [ ] Plan tab: strategy dropdown, criteria checklist, planned prices, R:R auto-calc, save creates planned trade
- [ ] Trades tab: groups (Planned, Open, Closed, Skipped) appear and update
- [ ] Trade card click: drawer opens
- [ ] Drawer Plan section: shows what was planned
- [ ] Drawer Execution → Mark as Entered: account balance default loaded, risk auto-calc, save → status becomes OPEN
- [ ] Drawer Execution → Mark as Skipped: skip reason saves, status becomes SKIPPED
- [ ] Drawer Result → Close Trade: partial exits add/remove, mistakes & emotions chips, custom tag input, save → status becomes WIN/LOSS/BE
- [ ] Edit a closed trade by re-opening the drawer (data should persist)
- [ ] Strategy manager: open from Plan tab → edit Zone Failure → add a criterion → save → checklist updates
- [ ] Account balance modal: update balance from Enter form
- [ ] Review tab: 7d / 14d / 30d preset switch, edge composite renders, mistake table, emotion entry/exit tables, timing impact, save review note, view saved review snapshot
- [ ] Delete trade and delete review work
- [ ] Mobile width (resize browser to <600px): drawer is full-screen, chip rows wrap

- [ ] **Step 2: Run pytest one more time**

```bash
cd backend && pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Push and deploy**

```bash
cd /Users/tejpalkumawat/Documents/buildfactory/trading-journal
git push origin v2-journal
gh pr create --title "Trading Journal v2 — Plan/Execution/Result/Mindset framework" \
  --body "$(cat <<'EOF'
## Summary

- Three-stage trade workflow: Plan → Entered/Skipped → Closed
- Multi-strategy support with editable criteria
- Mistake & emotion tag chips (predefined + custom)
- Risk-% tracking via account snapshots
- Auto-analytics: plan adherence, risk discipline, mistake/emotion impact, edge composite
- Saved review notes with frozen stats snapshots
- TradingView chart-URL field per trade

Spec: `docs/superpowers/specs/2026-04-25-trading-journal-v2-design.md`

## Test plan
- [ ] Backend pytest passes (test_risk, test_migrations, test_stages, test_analytics)
- [ ] Local smoke script passes against localhost:8111
- [ ] Frontend manual verification checklist (see Task 26 in plan)
- [ ] After deploy: smoke script passes against Render URL
- [ ] After deploy: existing v1 trades still load correctly (status backfilled)
EOF
)"
```

After merge, monitor:
- Render auto-deploys backend; check `/api/strategies` returns Zone Failure.
- Cloudflare auto-deploys frontend.
- Run `python scripts/e2e_smoke.py https://trading-journal-1-8ork.onrender.com` to confirm.

- [ ] **Step 4: Verify production migration ran**

After Render redeploy completes, hit:

```bash
curl https://trading-journal-1-8ork.onrender.com/api/strategies
```

Expected: array containing Zone Failure with 11 criteria. If empty, check Render logs for migration errors.

- [ ] **Step 5: Smoke production**

```bash
python scripts/e2e_smoke.py https://trading-journal-1-8ork.onrender.com
```

Expected: all ✓ pass.

---

## Risks & rollback

If migration fails on production Turso:
- Render logs will show the failing ALTER. Most likely cause: column already exists (idempotent path swallows it). If a different error, manually run the missing ALTERs via Turso CLI.
- Rollback path: revert the merge commit, redeploy. Existing v1 trades are untouched (no value changes), only status was rewritten — but `_migrations` row blocks re-running the backfill, so the rollback re-deploy is safe.

If frontend bundle breaks on Cloudflare:
- Check CF Pages build log. Most likely a TypeScript error from missing field. Fix locally, push.
- Users see the old bundle until CF redeploys (2-3 min).

---

## Files modified/created

**Backend (created):**
`backend/risk.py`, `backend/migrations.py`, `backend/analytics.py`, `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_risk.py`, `backend/tests/test_migrations.py`, `backend/tests/test_stages.py`, `backend/tests/test_analytics.py`

**Backend (modified):**
`backend/main.py` (large), `backend/turso_db.py` (init_tables), `backend/models.py` (extended Trade), `backend/requirements.txt`

**Frontend (created):**
`frontend/src/constants/tags.ts`, `frontend/src/lib/risk.ts`, `frontend/src/components/PlanForm.tsx`, `frontend/src/components/StrategyManager.tsx`, `frontend/src/components/TradeDetail.tsx`, `frontend/src/components/EnterTradeForm.tsx`, `frontend/src/components/SkipTradeForm.tsx`, `frontend/src/components/CloseTradeForm.tsx`, `frontend/src/components/AccountBalanceModal.tsx`, `frontend/src/components/TagChips.tsx`, `frontend/src/components/PartialExits.tsx`, `frontend/src/components/Review.tsx`

**Frontend (modified):**
`frontend/src/api.ts`, `frontend/src/main.tsx`, `frontend/src/index.css`

**Frontend (deleted):**
`frontend/src/components/TradeChecklist.tsx`, `frontend/src/components/Analytics.tsx`

**Other (created):**
`scripts/e2e_smoke.py`
