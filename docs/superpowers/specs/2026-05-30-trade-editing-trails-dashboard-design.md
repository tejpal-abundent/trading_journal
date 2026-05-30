# Trade editing, trailed stops, embedded charts, and P&L dashboard

**Date:** 2026-05-30
**Status:** Approved for planning
**Scope:** Six features that collectively reshape the journal from a plan/review tool into an open-trade-management + retrospective-analytics tool.

---

## 1. Why

Six concrete pain points, taken from the user's request:

1. Closed-trade data is read-only today. Mistakes in entry price, exit price, mistake tags, or lessons cannot be corrected without a delete-and-recreate cycle.
2. The TradingView snapshot URL is a tiny "📈 Chart" link. The user wants to *see* the chart inside the journal without clicking through.
3. The planning workflow (`/plan` route, `planned` status, `Skipped` flow) is unused friction. Every trade the user logs is one that was actually taken.
4. The trade list is a long vertical column that fills the main view. The user wants the list to be peripheral and the *current trade* (or dashboard) to be the focus.
5. There is no concept of moving a stop loss after entry. The user trails stops in real life and wants to log each move and have R-multiples reflect the trail strategy.
6. There is no time-bucketed P&L view. The user wants to know how May went vs. June, what this week looks like, and a running equity curve.

---

## 2. What is changing — at a glance

| Area | Before | After |
|---|---|---|
| Trade creation | Plan → Enter → Close (3 steps) | Enter → Close (2 steps); retroactive create still available |
| Trade list location | Main column, full width | Right rail (~220px), sticky, scrollable |
| Trade detail | Modal overlay | Full-page route `/trade/:id` |
| Editability of closed trades | Not supported | `Edit` button → every field editable; derived fields auto-recalc on save |
| Chart visibility | Text link only | Snapshot image inline (when URL is `tradingview.com/x/...`) + live Advanced Chart widget |
| Stop loss | Single value per trade | Original SL + ordered list of trail levels with timestamps |
| R-multiple | One number (`rr_achieved`) | Two numbers: `rr_achieved` (vs original SL) and `r_locked_at_penultimate_trail` (vs -1th trail, when applicable) |
| Default landing page | Plan form | Dashboard at `/` (KPIs + monthly/weekly P&L + heatmap + equity curve) |

---

## 3. Data model

### 3.1 New columns on `trades`

| Column | Type | Default | Purpose |
|---|---|---|---|
| `trailed_stops` | TEXT | `'[]'` | JSON array of trail objects, ordered chronologically. See §3.2 for shape. Does NOT include the original `stop_loss` (that is the implicit 0th). |
| `updated_at` | DATETIME | `NULL` | Bumped on every PATCH. Surfaces in the UI as "edited at …" when present and != `created_at`. |

### 3.2 `trailed_stops` shape

```json
[
  { "price": 105.0, "at": "2026-05-30T14:22:00Z", "note": "moved to break-even" },
  { "price": 115.0, "at": "2026-05-30T15:10:00Z" },
  { "price": 125.0, "at": "2026-05-30T15:48:00Z", "note": "swing high" }
]
```

- `price` required, float.
- `at` required, ISO-8601 UTC string.
- `note` optional, ≤200 chars.
- Array is always sorted by `at` ascending. Backend enforces sort on every write.

### 3.3 Deprecated, kept in DB

These columns/values are no longer written by the new UI but are NOT dropped — old rows keep their data and the columns remain so the migration is reversible.

- Columns: `planned_entry`, `planned_stop`, `planned_target`, `planned_rr`, `skip_reason`.
- Status values: `'planned'`, `'skipped'`.
- The new list/dashboard endpoints filter out rows with these statuses. Direct `GET /api/trades/{id}` still returns them (debugging / restore path).

### 3.4 Migration

One Alembic-style migration adds the two columns. Existing rows get `trailed_stops = '[]'` and `updated_at = created_at`. The `planned` / `skipped` rows are untouched; they simply stop appearing in lists once the frontend ships.

No data deletion. No backfill of `trailed_stops` from historical trades (we don't have the data).

---

## 4. API delta

### 4.1 New endpoints

#### `GET /api/dashboard`

Returns aggregates over all closed trades (status ∈ {`win`, `loss`, `breakeven`}).

**Response:**

```json
{
  "this_week":  { "label": "Week of 2026-05-25",
                  "pnl": 150.0, "trades": 3, "win_rate": 0.67 },
  "this_month": { "label": "May 2026",
                  "pnl": 1240.0, "trades": 14, "win_rate": 0.64 },
  "ytd":        { "label": "YTD 2026",
                  "pnl": 4810.0, "trades": 72, "win_rate": 0.58 },
  "open_trades": { "count": 2 },

  "monthly": [
    { "label": "Jan 2026", "year": 2026, "month": 1,
      "pnl_close_date": 320, "pnl_split": 290,
      "trades": 6, "win_rate": 0.50 },
    ...
  ],

  "weekly": [
    { "label": "Week of 2026-05-04", "iso_year": 2026, "iso_week": 19,
      "pnl": 410, "trades": 5, "win_rate": 0.60 },
    ...
  ],

  "daily_heatmap": [
    { "date": "2026-03-02", "pnl": 50.0, "trades": 1 },
    ...
  ],

  "equity_curve": [
    { "date": "2026-01-04", "cumulative_pnl": 120.0, "trade_id": 1 },
    { "date": "2026-01-07", "cumulative_pnl": 240.0, "trade_id": 2 },
    ...
  ]
}
```

**Buckets returned:**
- `monthly`: 12 most recent calendar months (oldest first), inclusive of the current month.
- `weekly`: 4 most recent ISO weeks (oldest first), inclusive of the current week.
- `daily_heatmap`: every day in the trailing 90-day window, including zero days (P&L = 0, trades = 0).
- `equity_curve`: one point per closed trade since the start of the account, ordered by `closed_at` ascending. Starting baseline is the latest `account_snapshots.balance` if any exists, otherwise 0.

**Timezone:** all date bucketing uses the server's local timezone (the journal is single-user). `closed_at` is stored UTC; conversion happens in Python at aggregate time using `datetime.fromisoformat(...).astimezone()`. If the user later runs the backend in a different timezone, monthly buckets near boundaries may shift by one day — acceptable.

**Cross-month attribution:**
- `pnl_close_date`: the trade's full P&L is added to its `closed_at` month.
- `pnl_split`: P&L is divided across months it spanned, weighted by days held in each calendar month.
  - `days_held = (date(closed_at) - date(opened_at)).days + 1` (inclusive of both endpoints).
  - For each month *m* the trade touched: `weight_m = days_of_trade_in_m / days_held`.
  - `pnl_split_for_m = round(weight_m * pnl, 2)`.
  - "Opened at" = the trade's `created_at` (we don't track entry-fill timestamps separately).
- `trades` and `win_rate` columns are always close-date attribution regardless of toggle — fractional trade counts have no meaning.

#### `POST /api/trades/{id}/trails`

Append a trail level.

**Request:** `{ "price": float, "note"?: string }`. `at` is server-stamped.

**Response:** updated `Trade` (the full one, with new array).

**Errors:** 404 if trade missing, 400 if trade status is not `entered`.

#### `DELETE /api/trades/{id}/trails/{index}`

Remove a trail by its current array index.

**Response:** updated `Trade`.

**Errors:** 404 if trade missing, 400 if index out of range.

### 4.2 Modified endpoints

#### `POST /api/trades`

Now creates a trade directly in `status = 'entered'`. Request body becomes:

```python
class TradeEnterCreate(BaseModel):
    pair: str
    direction: str          # "LONG" | "SHORT"
    timeframe: str
    strategy: str = "Zone Failure"
    setup_score: int
    verdict: str
    criteria_checked: list[str]
    notes: str = ""
    confluences: list[str] = []
    entry_price: float
    stop_loss: float
    take_profit: float | None = None
    position_size: float
    account_size: float
    entry_timing: str | None = None
    emotions_entry: list[str] = []
    feelings_entry: str = ""
    chart_url: str = ""
```

Server fills `risk_dollars` and `risk_percent` via existing `compute_risk()`. `status` is forced to `'entered'`.

#### `PATCH /api/trades/{id}`

Accepts ALL trade fields including `trailed_stops` (full array replacement — the trails table in the UI just writes the whole array). On every PATCH:
- Bump `updated_at` to `datetime.utcnow()`.
- If any of {`entry_price`, `exit_price`, `stop_loss`, `position_size`, `account_size`} changed, recompute `risk_dollars`, `risk_percent`, and (if status is closed) `rr_achieved`.
- If `trailed_stops` is in the payload, sort it by `at` before save.

`pnl` is editable. If the client sends `pnl`, the server stores exactly what was sent (manual override). If the client omits `pnl` and the request changes numeric fields, server does NOT auto-derive `pnl` — that field is the user's domain (varies by instrument, leverage, fees).

#### `POST /api/trades/{id}/close`

Existing endpoint stays. Adds: after writing, server recomputes `rr_achieved` from final entry/exit/stop and stores it (overriding any `rr_achieved` the client sent — closing is the canonical recalc moment).

### 4.3 Removed endpoints

- `POST /api/trades/{id}/enter` — entering is now the same as creating.
- `POST /api/trades/{id}/skip` — skipping is gone with the Plan flow.

`POST /api/trades/retroactive` is kept (used for backfilling historical closed trades).

---

## 5. R-multiple computation

Both numbers are derived server-side on every relevant write and stored alongside the trade.

```python
dir_sign = 1 if direction == "LONG" else -1
original_R_distance = abs(entry_price - stop_loss)   # > 0 always; entry==stop is rejected at validation

# Classic R achieved, always present on closed trades:
rr_achieved = round(
    (exit_price - entry_price) * dir_sign / original_R_distance,
    2,
)

# Locked-R from penultimate trail:
r_locked_at_penultimate_trail = None
if status == "win" and len(trailed_stops) >= 2:
    penultimate_price = trailed_stops[-2]["price"]
    r_locked_at_penultimate_trail = round(
        (exit_price - penultimate_price) * dir_sign / original_R_distance,
        2,
    )
```

Why penultimate, not last: the *last* trail level is typically the one that got hit (closing the trade). The level just before it is the "real risk in the market" during the profitable run — and the move from there to exit is the slice of the move that was protected by your trail strategy. This is the number that answers "did my trailing add value?".

`r_locked_at_penultimate_trail` is omitted on losses and breakevens, and on trades with fewer than 2 trails. It is a new field on the JSON response, optional.

---

## 6. Frontend architecture

### 6.1 Route map (after)

| Route | Component | Purpose |
|---|---|---|
| `/` | `Dashboard` | Default landing; KPIs, monthly/weekly bars, heatmap, equity curve |
| `/trade/:id` | `TradeDetailPage` | Full-page view of one trade (view or edit mode) |
| `/trade/new` | `NewTradePage` | Form to create a new (entered) trade |
| `/trade/new?mode=retro` | `NewTradePage` | Same form, posts to `/api/trades/retroactive` |
| `/review` | `Review` | Unchanged |
| `/analytics` | redirect → `/review` | Keep existing redirect |

**Removed:** `/plan`, `/trades`. Old links to those redirect to `/`.

### 6.2 Layout shell

```
+--------------------------------------------------------------+
| Trading Journal      Dashboard  Review  [+ New Trade]        |
+------------------------------------------------+-------------+
|                                                | OPEN (2)    |
|                                                |  BTC LONG   |
|                                                |  +1.2R …    |
|                                                |  ETH SHORT  |
|                                                |  unrealized |
|        <Outlet>                                +-------------+
|        Dashboard or TradeDetailPage            | CLOSED (42) |
|                                                |  SOL WIN    |
|                                                |  +$80       |
|                                                |  AVAX LOSS  |
|                                                |  -$30       |
|                                                |  …          |
+------------------------------------------------+-------------+
```

The right rail is its own component (`TradeRail`), independent of the route — it's always visible on desktop. On narrow viewports (<900px), the rail collapses into a floating "Trades (N)" button at bottom-right that, when tapped, slides the rail in as an overlay.

### 6.3 Components inventory

**New:**
- `Dashboard.tsx` — top-level dashboard layout
- `KPICard.tsx` — small "label / big number / sub-line" card used 4× on dashboard
- `MonthlyBars.tsx` — bar chart of monthly P&L, with `[Close date | Split by days]` toggle (client-side switch between `pnl_close_date` and `pnl_split` series)
- `WeeklyBars.tsx` — bar chart of weekly P&L
- `DailyHeatmap.tsx` — 90-day calendar heatmap (green = profit day, red = loss day, gray = no trades), one cell per day
- `EquityCurve.tsx` — Recharts `<LineChart>` of cumulative P&L over time
- `TradeRail.tsx` — sticky right-side panel with Open / Closed sections; tile click → `navigate(/trade/:id)`
- `TradeDetailPage.tsx` — full-page trade view; replaces modal `TradeDetail.tsx`; toggles between view and edit mode
- `NewTradePage.tsx` — form for creating an entered trade (`mode=retro` switches the submit endpoint and reveals the exit/lessons fields inline)
- `CloseTradePanel.tsx` — inline panel rendered on `TradeDetailPage` when status is `entered`; collects exit_price, status (win/loss/breakeven), mistake_tags, emotions_exit, feelings_exit, lessons; posts to `/api/trades/{id}/close`
- `TrailedStopsTable.tsx` — chronological table of trails with inline edit, add-row, delete-row; highlights penultimate row when status is `win`
- `ChartEmbed.tsx` — renders snapshot image (if URL matches `tradingview.com/x/`) + Advanced Chart widget; handles 404 fallback
- `EditableField.tsx` — small helper component used in edit-mode for consistent input styling
- `lib/dashboard.ts` — date bucketing helpers, currency formatting
- `lib/tradingview.ts` — pure helpers: `parseTradingViewSnapshot(url)`, `timeframeToInterval(tf)`

**Modified:**
- `main.tsx` — new route map, removes `/plan` and `/trades` routes, adds layout with right rail
- `api.ts` — add `getDashboard`, `addTrail`, `deleteTrail`; remove `enter`, `skip`, the old plan-create types; tighten `Trade` to include `trailed_stops`, `updated_at`, `r_locked_at_penultimate_trail`
- `Review.tsx` — no functional change; just confirm it still renders correctly with the new layout shell

**Removed:**
- `PlanForm.tsx`
- `SkipTradeForm.tsx`
- `TradeList.tsx` (replaced by `TradeRail.tsx`)
- `TradeDetail.tsx` (replaced by `TradeDetailPage.tsx`)
- `EnterTradeForm.tsx` (subsumed into `NewTradePage.tsx`)
- `EnterTradeForm.tsx` and `CloseTradeForm.tsx` are absorbed into `NewTradePage` (entry) and a small inline `CloseTradePanel` rendered on `TradeDetailPage` when status is `entered` (close)

### 6.4 TradeDetailPage structure

Two modes, toggled by an `Edit` button in the header.

Closing a trade is a **state transition**, not an edit. It is its own action with its own endpoint (`POST /close`) and its own inline UI (`CloseTradePanel`) shown on the detail page when status is `entered`. Editing existing field values (including on already-closed trades) goes through `Edit` mode and `PATCH /api/trades/{id}`. Two separate concerns, two separate buttons.

**View mode:**

1. **Header** — Back arrow · pair/direction/timeframe/strategy chips · status badge · `Edit` button · `Delete` button · (when status is `entered`) `Close trade` button that opens the inline `CloseTradePanel`.
2. **Chart panel** — `<ChartEmbed snapshotUrl={trade.chart_url} symbol={trade.pair} timeframe={trade.timeframe} />`. Snapshot above, live widget below, both labeled.
3. **Numbers strip** — Entry · Exit · Original SL · TP · Size · Risk $ / % · R achieved · R locked at -1th trail (if present) · P&L. Compact horizontal grid.
4. **Trailed stops** — `<TrailedStopsTable />`. Read-only view: 1 row per trail with price, time, note. Penultimate row tinted yellow on `win` status. "+ Add trail" button (visible in view mode too — adding a trail is a frequent action you want to do quickly while the trade is open).
5. **Plan / Process** — verdict, setup_score, criteria_checked, confluences, notes.
6. **Outcome** — rules_followed, mistake_tags, emotions_exit, feelings_exit, lessons.

**Edit mode:**

Same six sections, but every value becomes an input. Save sends one PATCH with the full editable payload (server takes care of recalculating derived fields). Cancel reverts to view mode without firing a request.

The Trailed-Stops table is always editable (price and note inline-editable, row delete is a small × button) — adding/removing trails is an operational action, not part of edit mode.

### 6.5 ChartEmbed details

```typescript
function parseTradingViewSnapshot(url: string): string | null {
  // Matches https://www.tradingview.com/x/HASH/ or /x/HASH or with/without trailing slash
  const m = url.match(/tradingview\.com\/x\/([A-Za-z0-9]+)/);
  return m ? `https://s3.tradingview.com/snapshots/x/${m[1]}.png` : null;
}

function timeframeToInterval(tf: string): string {
  // Map our timeframe codes to TradingView interval strings
  const map: Record<string, string> = {
    "1m": "1", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "4h": "240", "1d": "D", "1w": "W"
  };
  return map[tf.toLowerCase()] ?? "D";
}
```

Snapshot `<img>` has an `onError` that hides itself. Live widget mounts a `<div>` and injects `<script src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js">` with config in its body — TradingView's documented embed pattern. The widget needs `symbol` formatted with exchange prefix when possible (e.g., `BINANCE:BTCUSDT`); when the pair has no exchange marker we pass it through as-is and let TradingView resolve.

### 6.6 Loading and empty states

- Dashboard before first trade: shows the layout with all cards reading "—" / "no data" rather than blank space.
- Dashboard during fetch: skeleton placeholders for each card.
- Trade rail before first trade: "No open trades · No closed trades · Hit + New Trade to start".
- TradeDetailPage on bad ID: redirect to `/` with a toast "Trade not found".

---

## 7. Backend implementation notes

### 7.1 New module: `dashboard.py`

Single function `compute_dashboard(trades: list[dict]) -> dict` that takes parsed trades and returns the shape in §4.1. Lives in `backend/dashboard.py`. Pure function, no DB access — `main.py` fetches trades and calls it. Testable in isolation.

### 7.2 Trail mutation logic

Lives in `main.py` next to the other route handlers, since it's a thin wrapper over `db_update_trade`. The handler reads the existing trade, appends/removes, sorts, dumps to JSON, calls `db_update_trade`.

### 7.3 R-multiple recalc

Lives in `risk.py` alongside `compute_risk`, as a new function `compute_rr(entry, exit_price, stop_loss, direction, status, trailed_stops) -> dict`. Called from:
- `POST /api/trades/{id}/close`
- `PATCH /api/trades/{id}` when any of {entry, exit, stop, trails} changed
- `POST /api/trades/retroactive`

Returns `{"rr_achieved": float, "r_locked_at_penultimate_trail": float | None}`.

### 7.4 Database compatibility

The project supports both SQLite (default) and Turso (via `TURSO_DB_URL`). Both new columns (`trailed_stops TEXT`, `updated_at DATETIME`) work natively in both. The migration is registered through `migrations.py`'s shared `run_migrations` machinery so both paths apply it on startup.

---

## 8. Testing

### 8.1 Backend (pytest)

- **`tests/test_dashboard.py`** — happy path with mixed trades; cross-month split arithmetic; equity curve order/baseline; empty input.
- **`tests/test_trails.py`** — POST/DELETE trail endpoints; ordering enforced; index-out-of-range; appending to non-entered trade rejected.
- **`tests/test_rr_recalc.py`** — `compute_rr` math: long/short, win/loss/breakeven, no-trails / 1 trail / 2+ trails (penultimate selection), entry==stop rejected.
- **`tests/test_edit_endpoint.py`** — PATCH bumps `updated_at`; partial payloads work; numeric-field changes trigger recalc; `pnl` manual override is preserved; trailed_stops sort enforcement.
- **`tests/test_migration.py`** — fresh DB gets both new columns; existing rows get `trailed_stops='[]'` and `updated_at=created_at`.

### 8.2 Frontend (vitest, where the project already has it)

- `lib/tradingview.test.ts` — URL parsing (valid snapshot, missing, query-string, trailing slash, non-TV URL); timeframe mapping (all keys, unknown).
- `lib/dashboard.test.ts` — cross-month split math; week boundary; heatmap zero-fill; equity curve cumulative sum.
- `TrailedStopsTable.test.tsx` — render with N trails; highlight penultimate on win; add/delete trail callbacks.
- `ChartEmbed.test.tsx` — snapshot image hidden on error; widget script injection idempotent across rerenders.

No new test infra. The project already runs pytest in `backend/` and (per repo state) has at least `backend/tests/test_stats.py` and `backend/tests/test_analytics.py`.

---

## 9. Out of scope (explicit)

- Multi-account or multi-strategy filters on the dashboard. (Today the journal is one account.)
- A first-class mobile layout. The desktop layout collapses to a floating button below 900px, which is acceptable but not optimized.
- Realtime price feed in the rail (e.g., showing unrealized P&L on open trades). Open trades show entry/stop/size only.
- A standalone "trail strategy comparison" analytics page. We surface `r_locked_at_penultimate_trail` per-trade but don't aggregate it across trades in this iteration.
- Drag-to-reorder trails. Trails are time-ordered; you can only delete/add.
- Snapshot image hosting beyond TradingView's `tradingview.com/x/` pattern. Custom URLs render as links only.

---

## 10. Migration rollout

1. Run migration: adds `trailed_stops`, `updated_at` columns, backfills.
2. Deploy backend with new endpoints alive and old `/enter` / `/skip` returning 410 Gone with a one-line "endpoint removed" message.
3. Deploy frontend that uses the new endpoints.

Steps 2 and 3 ship together (single-user app, no need for staged rollout).

Old `planned` and `skipped` trades in the DB stay present but invisible. If the user wants them visible later, the rail can grow a "Show archived" toggle — out of scope for this spec.

---

## 11. Definition of done

- [ ] Migration applied, both new columns present in dev DB.
- [ ] All new endpoints return the documented shapes (verified by curl + tests).
- [ ] Dashboard route renders with at least 14 days of seeded data and visibly distinct values for each card.
- [ ] Right rail visible on every route, open & closed sections populated, click navigates to detail.
- [ ] Trade detail page renders in view & edit modes; Save sends a single PATCH and updates derived fields.
- [ ] Snapshot image renders for a real `tradingview.com/x/...` URL; falls back cleanly when URL doesn't match.
- [ ] Live TradingView widget loads with `BTCUSDT` on `15m`.
- [ ] Adding a trail via the UI updates the table and bumps `r_locked_at_penultimate_trail` on closed-in-profit trades.
- [ ] Editing any field on a closed trade and saving works without errors.
- [ ] Backend pytest suite passes (existing + new tests).
- [ ] No regression in the `Review.tsx` page (statistical-honesty layer still renders).
