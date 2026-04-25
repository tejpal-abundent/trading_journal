# Trading Journal v2 — Plan / Execution / Result / Mindset Framework

**Date:** 2026-04-25
**Author:** tejpal@buildfactory.io
**Status:** Approved for planning

## 1. Goal

Expand the existing trading journal from a simple "log + close" flow into a structured journal that captures the four phases of a trade — Plan, Execution, Result, Mindset — plus mistake/emotion tagging, multi-strategy support, and weekly/monthly review tooling. The aim is to collect enough data to surface the user's edge automatically, not just store trade rows.

## 2. Scope

**In scope**
- Three-stage trade workflow (Plan → Entered or Skipped → Closed) with each stage's data captured at the right moment.
- Mistake-tag and emotion-tag chip vocabularies (predefined + custom) attached per trade.
- Risk tracking via account size + position size, with risk-% auto-derived.
- Multi-strategy support: a `strategies` table with editable per-strategy criteria, seeded with the existing zone-failure setup.
- TradingView chart-URL field per trade (option B from brainstorm — no image hosting).
- Auto-analytics dashboard with new metrics (plan adherence, risk discipline, mistake-tag impact, emotion impact, timing impact, edge composite).
- Manual review notes saved with frozen stats snapshots.
- Account-balance snapshot history.

**Out of scope**
- Image upload / R2 storage for chart screenshots.
- Multi-user auth (still single-user).
- Mobile app (responsive web only).
- Real-time price feeds or broker integration.
- Notifications / reminders.

## 3. Decisions log (from brainstorming)

| Question | Choice | Implication |
|---|---|---|
| Workflow stages | C — three stages, middle stage optional via Skipped path | Tracks "did I plan this?" and "did I follow through?" |
| Mindset capture | C — chip tags + free-text | Tags drive analytics; text captures nuance |
| Position size & risk | B — % risk + account size, $ risk derived | Risk-discipline analytics, account snapshots |
| Mistakes & edge | A — per-trade mistake chips, edge auto-derived | No separate "mistakes" doc; analytics surface them |
| Chart screenshots | B — TradingView URL paste | No storage cost, manual upload step |
| Weekly/Monthly review | C — auto dashboard + manual review notes | Stats snapshot frozen at write time |
| Strategy generality | C — multiple strategies, custom criteria stored as JSON | Editable; existing checklist becomes one of many |

## 4. Data model

Four tables on the existing Turso (SQLite) database. The `trades` table extends in place; three new tables are added.

### 4.1 `trades` (extended)

```sql
CREATE TABLE trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT DEFAULT (datetime('now')),
  closed_at TEXT,

  -- Plan stage
  pair TEXT NOT NULL,
  direction TEXT NOT NULL,            -- LONG | SHORT
  timeframe TEXT NOT NULL,
  strategy TEXT NOT NULL DEFAULT 'Zone Failure',
  setup_score INTEGER NOT NULL,
  verdict TEXT NOT NULL,
  criteria_checked TEXT NOT NULL,     -- JSON list of criterion ids
  planned_entry REAL,
  planned_stop REAL,
  planned_target REAL,
  planned_rr REAL,
  notes TEXT DEFAULT '',              -- "Logic / why this trade" — pre-trade rationale

  -- Execution stage (entry_price / stop_loss / take_profit are the *actual* values, reused from v1)
  status TEXT DEFAULT 'planned',      -- planned | entered | win | loss | breakeven | skipped
  retroactive INTEGER DEFAULT 0,      -- 1 if plan filled after entry
  entry_price REAL,                   -- actual entry
  stop_loss REAL,                     -- actual stop
  take_profit REAL,                   -- actual target
  position_size REAL,
  account_size REAL,
  risk_dollars REAL,                  -- derived
  risk_percent REAL,                  -- derived
  entry_timing TEXT,                  -- on_time | late | early
  emotions_entry TEXT DEFAULT ',',    -- comma-wrapped list, e.g. ",fomo,confident,"
  feelings_entry TEXT DEFAULT '',
  skip_reason TEXT DEFAULT '',

  -- Result stage
  exit_price REAL,
  partial_exits TEXT DEFAULT '[]',    -- JSON list of {price, size_pct, reason}
  pnl REAL,
  pnl_percent REAL,
  rr_achieved REAL,
  rules_followed INTEGER,             -- nullable bool
  mistake_tags TEXT DEFAULT ',',      -- comma-wrapped list
  emotions_exit TEXT DEFAULT ',',     -- comma-wrapped list
  feelings_exit TEXT DEFAULT '',
  lessons TEXT DEFAULT '',
  chart_url TEXT DEFAULT ''
);
```

Comma-wrapped list format example: a trade tagged `fomo` and `oversized` stores `,fomo,oversized,`. SQL search uses `WHERE mistake_tags LIKE '%,fomo,%'` to avoid substring collisions (e.g., `fomo` matching inside `confomo`).

### 4.2 `strategies`

```sql
CREATE TABLE strategies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  criteria TEXT NOT NULL,             -- JSON list of {id, label, points, category, description}
  is_core_required TEXT DEFAULT '[]', -- JSON list of criterion ids that must all be checked
  created_at TEXT DEFAULT (datetime('now'))
);
```

Seeded on first boot with one row representing the existing Zone Failure setup (11 criteria, 4 cores).

### 4.3 `account_snapshots`

```sql
CREATE TABLE account_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  balance REAL NOT NULL,
  recorded_at TEXT DEFAULT (datetime('now')),
  note TEXT DEFAULT ''
);
```

Latest row's balance defaults the `account_size` field on a new trade entry. User updates it explicitly when they meaningfully change account balance (deposit / withdrawal / catch-up).

### 4.4 `review_notes`

```sql
CREATE TABLE review_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  period_type TEXT NOT NULL,          -- week | month | custom
  period_start TEXT NOT NULL,         -- ISO date
  period_end TEXT NOT NULL,
  notes TEXT NOT NULL,
  stats_snapshot TEXT NOT NULL,       -- JSON of the analytics payload at write time
  created_at TEXT DEFAULT (datetime('now'))
);
```

### 4.5 Tag vocabularies (frontend constants, not DB)

`src/constants/tags.ts`:

```ts
export const MISTAKE_TAGS = [
  "moved_sl", "exited_early", "oversized",
  "chased_entry", "against_trend", "ignored_news",
  "fomo_entry", "no_plan", "revenge_trade", "held_too_long",
];

export const EMOTION_TAGS = [
  "confident", "patient", "anxious", "fearful", "fomo",
  "greedy", "frustrated", "calm", "hesitant", "excited",
];

export const ENTRY_TIMING = ["on_time", "late", "early"];
```

User-typed custom tags are stored in the comma-wrapped list alongside predefined ones — no schema awareness of which is which. Analytics aggregates over all unique tags it sees in the data.

## 5. Workflow

### 5.1 Stage transitions

```
              ┌──────────┐
              │ planned  │  (Save Plan)
              └────┬─────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   "Mark Entered"         "Mark Skipped"
        │                     │
   ┌────▼─────┐           ┌───▼────┐
   │ entered  │           │ skipped │  (terminal)
   └────┬─────┘           └────────┘
        │
   "Close Trade"
        │
   ┌────▼────────────────────┐
   │ win | loss | breakeven  │  (terminal)
   └─────────────────────────┘
```

Backwards path (retroactive): user can also create a closed trade in one form when they forgot to log the plan. This sets `retroactive=1` and is excluded from plan-adherence analytics.

### 5.2 Stage data requirements

| Stage | Required fields | Optional fields |
|---|---|---|
| Plan | pair, direction, timeframe, strategy, criteria_checked, setup_score, verdict | planned_entry, planned_stop, planned_target, notes |
| Enter | entry_price, stop_loss, position_size, account_size | take_profit, entry_timing, emotions_entry, feelings_entry |
| Skip | skip_reason | emotions_entry |
| Close | exit_price, status (win/loss/breakeven), pnl OR pnl_percent | partial_exits, rr_achieved, rules_followed, mistake_tags, emotions_exit, feelings_exit, lessons, chart_url |

Risk fields (`risk_dollars`, `risk_percent`) are computed server-side on Enter from `entry_price`, `stop_loss`, `position_size`, `account_size`.

## 6. UI

### 6.1 Top-level layout — three tabs

1. **Plan** — strategy dropdown → criteria checklist → planned price inputs → logic textarea → "Save Plan" button.
2. **Trades** — list grouped by status (Planned · Open · Closed · Skipped); filter pills; click a card → Trade Detail Drawer.
3. **Review** — date range picker; auto stats dashboard; saved-reviews list; "Write review for this period" CTA.

### 6.2 Trade Detail Drawer

Slides in from right (full-screen on mobile). Three accordion sections per trade:

- **Plan** — read-only summary + edit pencil. Always visible.
- **Execution** — visible when `status >= entered`. Shows actual entry / risk / feelings, or two CTAs ("Mark Entered" / "Mark Skipped") if `status=planned`.
- **Result** — visible when `status >= entered`. Shows exit / PnL / mistakes / lessons, or "Close Trade" CTA if `status=entered`.

Each section has an Edit button to reopen its form. Trades remain editable after close (lessons often arrive days later).

### 6.3 Form patterns

- **Tag chips** — horizontal pill row with predefined tags. Selected pills get colored background. "+ custom" pill opens an inline text input that adds a custom tag to that trade.
- **Partial exits** — dynamic list with "+ Add partial exit" button. Each row: price, % of position, reason dropdown (`took_profit | cut_loss | scaled_out | sl_adjusted`).
- **Risk auto-calc** — as `entry_price`, `stop_loss`, `position_size`, `account_size` are typed, a small line below the form shows `Risk: $X (Y% of account)` updated live. Sent to server on save.
- **Strategy criteria editor** — modal launched from the strategy dropdown. Add / remove / rename criteria; change points; mark as core. Edits don't retroactively change already-logged trades because each trade stores the criteria IDs, not the strategy ref.

### 6.4 File structure

| File | Purpose |
|---|---|
| `src/api.ts` | Extended `Trade` type, new API methods |
| `src/components/PlanForm.tsx` | Was `TradeChecklist.tsx`; generalized for any strategy |
| `src/components/TradeList.tsx` | Now groups by status, opens drawer |
| `src/components/TradeDetail.tsx` | New — accordion drawer |
| `src/components/EnterTradeForm.tsx` | New |
| `src/components/CloseTradeForm.tsx` | New |
| `src/components/SkipTradeForm.tsx` | New |
| `src/components/Review.tsx` | Was `Analytics.tsx`; adds date range, review notes |
| `src/components/StrategyManager.tsx` | New — strategies CRUD modal |
| `src/components/AccountBalanceModal.tsx` | New — record account snapshot |
| `src/constants/tags.ts` | New — tag vocabularies |
| `src/lib/risk.ts` | New — pure risk-calc helpers |

## 7. Backend

### 7.1 Module split

`backend/main.py` is already 340 lines and the analytics function is ~70 lines and growing. Split:

- `backend/main.py` — FastAPI app, schemas, route registrations, db-layer dispatch.
- `backend/db/__init__.py` — exports `db_*` functions; chooses Turso or SQLAlchemy backend.
- `backend/db/turso_backend.py` — Turso-flavored `db_*` impls (extracted from current `if USE_TURSO` branch).
- `backend/db/sqlite_backend.py` — SQLAlchemy-flavored impls (extracted from `else` branch).
- `backend/analytics.py` — all stat computations.
- `backend/migrations.py` — `init_tables()` + `run_migrations()` (idempotent ALTERs and seeds).

### 7.2 New endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/trades` | TradeCreatePlan | Trade (status=planned) |
| POST | `/api/trades/retroactive` | TradeCreateFull | Trade (retroactive=1, status=closed) |
| POST | `/api/trades/{id}/enter` | TradeEnter | Trade (status=entered) |
| POST | `/api/trades/{id}/skip` | TradeSkip | Trade (status=skipped) |
| POST | `/api/trades/{id}/close` | TradeClose | Trade (status=win/loss/breakeven) |
| PATCH | `/api/trades/{id}` | partial Trade | Trade (edits any stage's data) |
| GET | `/api/trades` | — | list, filterable by status |
| DELETE | `/api/trades/{id}` | — | ok |
| GET | `/api/strategies` | — | list |
| POST | `/api/strategies` | StrategyCreate | Strategy |
| PATCH | `/api/strategies/{id}` | StrategyUpdate | Strategy |
| DELETE | `/api/strategies/{id}` | — | ok (rejects if any trade references it) |
| GET | `/api/account-snapshots` | — | list |
| POST | `/api/account-snapshots` | `{balance, note}` | AccountSnapshot |
| GET | `/api/account-snapshots/latest` | — | latest balance (for new-trade default) |
| GET | `/api/analytics?days=N` or `?from=&to=` | — | extended analytics payload (see 7.4) |
| GET | `/api/reviews` | — | list |
| POST | `/api/reviews` | `{period_type, period_start, period_end, notes}` | Review with frozen stats_snapshot |
| GET | `/api/reviews/{id}` | — | full review with snapshot |
| DELETE | `/api/reviews/{id}` | — | ok |

### 7.3 Risk calculation (server-side)

```
risk_per_unit  = abs(entry_price - stop_loss)
risk_dollars   = risk_per_unit * position_size
risk_percent   = (risk_dollars / account_size) * 100
```

Computed in `/api/trades/{id}/enter` and stored, rounded to 4 decimals. Also recomputed by `PATCH /api/trades/{id}` whenever any of `entry_price`, `stop_loss`, `position_size`, or `account_size` is in the patch body. If any required input is null after the patch, both `risk_dollars` and `risk_percent` are set to null.

### 7.4 Analytics payload

Extends the current shape:

```json
{
  "period_days": 14,
  "period_start": "2026-04-11", "period_end": "2026-04-25",
  "total_trades": 22, "closed_trades": 18, "open_trades": 2,
  "planned_trades": 0, "skipped_trades": 2,
  "wins": 11, "losses": 6, "breakeven": 1,
  "win_rate": 61.1, "total_pnl": 432.50,
  "avg_score": 78.4, "avg_rr": 1.85,
  "score_analysis": { "A (85-100)": {...}, "B (70-84)": {...}, ... },
  "pair_breakdown": { "XAG/USD": {...} },
  "direction_stats": { "LONG": {...}, "SHORT": {...} },

  "plan_adherence": {
    "rules_followed_pct": 73.0,
    "rules_followed_win_rate": 64.0,
    "rules_broken_win_rate": 31.0,
    "skip_rate": 9.0,
    "retroactive_rate": 0.0
  },
  "risk_discipline": {
    "avg_risk_pct": 1.2, "max_risk_pct": 3.4,
    "over_threshold_count": 2,
    "histogram": [{"bucket": "<0.5%", "count": 3}, ...]
  },
  "mistake_impact": [
    { "tag": "moved_sl", "count": 4, "win_rate": 25.0, "total_pnl": -180.0 },
    { "tag": "(none)", "count": 12, "win_rate": 75.0, "total_pnl": 540.0 }
  ],
  "emotion_impact": {
    "entry": [{ "tag": "fomo", "count": 3, "win_rate": 33.3, "avg_pnl": -60.0 }],
    "exit":  [{ "tag": "anxious", "count": 5, "win_rate": 40.0, "avg_pnl": -20.0 }]
  },
  "timing_impact": {
    "on_time": { "count": 14, "win_rate": 68.0 },
    "late":    { "count": 3,  "win_rate": 33.0 },
    "early":   { "count": 1,  "win_rate": 0.0 }
  },
  "strategy_breakdown": [
    { "strategy": "Zone Failure", "count": 18, "win_rate": 61.1, "expectancy": 24.0 }
  ],
  "edge_composite": {
    "headline": "Zone Failure A+ setups, plan followed, no mistakes",
    "filter": { "strategy": "Zone Failure", "score_min": 85, "rules_followed": true, "no_mistakes": true },
    "count": 7, "win_rate": 78.0, "avg_rr": 2.4, "total_pnl": 410.0
  },
  "trades": [...]
}
```

`edge_composite` is computed by ranking the cross-product of (strategy × score_bucket × rules_followed × no_mistakes) by total_pnl, picking the top slice with at least 5 trades. If no slice clears 5 trades, the field is `{"headline": "Not enough data yet", "count": 0}` and other keys are omitted.

**Aggregation rules**

- Mistake-tag and emotion-tag tables: a trade with N tags contributes to N tag rows. `(none)` is its own bucket containing trades with zero mistake tags.
- `skip_rate` denominator: count of trades whose lifecycle began with a plan (status in entered, win, loss, breakeven, or skipped). Retroactive trades (no plan stage) are excluded from the denominator.
- All `*_rate` fields are clamped 0–100, rounded to one decimal.

## 8. Migration

`run_migrations()` in `backend/migrations.py` runs at startup. Each step is idempotent.

```python
ALTERS = [
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

for sql in ALTERS:
    try:
        execute(sql)
    except Exception as e:
        if "duplicate column" not in str(e).lower():
            raise

# Seed strategies if empty
if fetch_one("SELECT COUNT(*) AS c FROM strategies")["c"] == 0:
    execute("INSERT INTO strategies (name, criteria, is_core_required) VALUES (?, ?, ?)",
            ["Zone Failure", json.dumps(ZONE_FAILURE_CRITERIA), json.dumps(["trend","zone","signal","failure"])])

# Backfill: existing closed trades get strategy='Zone Failure' (already default), status preserved
```

**One-time data migration** (runs once after ALTERs, gated by the `_migrations` table):

Since we kept the v1 column names `entry_price`/`stop_loss`/`take_profit` and `notes`, no value copies are needed. Only the `status` field needs reinterpreting:

- Existing rows with `status='open'` AND non-null `entry_price` → `status='entered'`, `retroactive=1` (we never had a separate plan).
- Existing rows with `status='open'` AND null `entry_price` → `status='planned'` (pure plans the v1 UI hadn't moved to result yet).
- Existing closed rows (`status` in `win`, `loss`, `breakeven`) → keep status, set `retroactive=1`.

A `_migrations` table tracks which one-time migrations have run:

```sql
CREATE TABLE IF NOT EXISTS _migrations (
  name TEXT PRIMARY KEY,
  applied_at TEXT DEFAULT (datetime('now'))
);
```

The data migration inserts `('v2_status_backfill', now())` on success; subsequent boots see the row and skip.

## 9. Testing

### 9.1 Backend (pytest)

- `tests/test_analytics.py` — fixture builds a set of trades; asserts each analytics block.
  - Plan adherence: trades with `rules_followed=true` and `false` mixed.
  - Risk discipline: trades at varying risk %, threshold = 2%.
  - Mistake impact: trades with overlapping tag sets; ensures none-bucket aggregates correctly.
  - Edge composite: 6 trades matching a slice; asserts headline picks it.
- `tests/test_stages.py` — round-trip a trade through `plan → enter → close`; assert each endpoint mutates the right fields and risk auto-calc is correct.
- `tests/test_migrations.py` — start with the v1 schema, run migrations, assert v2 schema; idempotent on second run.

Tests run against the SQLAlchemy/SQLite backend in-memory; the Turso backend is a thin wrapper and is exercised manually post-deploy.

### 9.2 Frontend

No automated tests added. A manual verification checklist lives in the implementation plan covering: plan save, mark entered, mark skipped, close (each outcome), edit each stage, partial exit add/remove, strategy criteria edit, account snapshot save, review save, date-range filter, mobile drawer.

### 9.3 Smoke

A `scripts/e2e_smoke.py` script: creates a strategy, plans a trade, enters it, closes it as a win, asserts analytics show 1 closed trade win-rate 100%. Runnable against any backend URL.

## 10. Deployment

No infra changes. Push triggers Render (backend) and Cloudflare (frontend) deploys. First deploy after merge runs the migration on Turso. Frontend's Vite build picks up new components automatically.

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| 20 ALTER statements at first boot are slow over Turso HTTP | Run once, log progress, idempotent so reruns are cheap |
| Comma-wrapped tag search misses semantically-similar tags (e.g., `fomo` vs `fomo_entry`) | Mistake tags use the predefined list; analytics aggregates by exact tag string |
| User edits a strategy's criteria, breaking historical comparisons | Trades store criterion IDs at log time, not a strategy ref; old trades' scores remain valid |
| Account size forgotten and risk-% becomes meaningless | UI prompts to confirm account size on every Enter form (defaulted from latest snapshot) |
| Free Render dyno sleep makes save feel broken | Existing UX (Saving... state) covers it; not made worse |

## 12. Open items (to revisit after MVP)

- Image upload for chart screenshots (Approach C from brainstorm).
- Notifications / reminders to write weekly review.
- Multi-user / auth.
- Broker import (CSV).
- Export to CSV.
