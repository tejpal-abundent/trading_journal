# TEJ CAPITAL — Design Spec

**Date:** 2026-08-16
**Branch:** `feature/tej-capital` (base `origin/main`)
**Repo:** `tejpal-abundent/trading_journal`
**Location:** `trading-journal/tej-capital/`
**Status:** approved for spec — pending user review before implementation-plan step

---

## 0. Purpose and non-goals

**Purpose.** A fund-operations platform for a single discretionary trader (Tejpal
Kumawat). Records daily marks, computes an institutional-grade track record,
enforces a written risk policy, and — the part no trading app does — states
plainly when the numbers do not yet mean anything.

This subsystem lives inside the existing `trading-journal/` repo but shares no
tables, no models, and no code paths with the existing app. The only integration
point is a single nav item added to the existing `trading-journal/frontend`
that opens the TEJ CAPITAL UI in a new browser tab (`target="_blank"`).

**Non-goals.**

- Charting, signal generation, backtesting, order placement, position sizing
  that touches execution, social feed.
- Multi-user, multi-tenant, or team collaboration. Single trader.
- Rewriting the existing `trading-journal/backend` or `trading-journal/frontend`.
- Broker connectivity beyond CSV in v1 (interfaces are scaffolded — see §7).

**Success measure.** The trader still enters a mark every evening in month 30.
Every design decision defers to that. Product Brief §10 is quoted here on record:
*"The predictable way this project dies is that Milestone 9 gets built in week
one and the daily mark never becomes a habit."* The scope decision to scaffold
all 9 milestones was made by the user with this risk stated and overridden.

---

## 1. Scope

Scope for v1 = all 9 milestones from Product Brief §9, scaffolded end-to-end.
Every screen, every table, every metric enumerated in the source documents is
present at merge. Where an integration requires third-party credentials the
trader has not yet configured (Temporal server, Telegram bot, Qdrant, broker
APIs, LLM keys), the module ships as an importable interface with a stubbed
backend and a documented "not configured" fall-through — so the app runs and
tests pass out of the box on `docker compose up`.

Fully wired at merge (all 12 screens render with real data):

- Today (daily mark), Trade Entry (before/after), Ledger heatmap, Monthly
  return grid, Performance dashboard (every metric group), Edge Attribution,
  Risk Policy live monitor, Accounts & Capital, Audit Trail, Monthly
  Tearsheet (in-browser render), Settings, Allocator View (read-only
  shareable link with journal fields hidden, token-gated, expiring).
- `core/` pure metric engine with pytest coverage for every metric.
- Postgres + TimescaleDB schema with Alembic migrations.
- CSV broker import fully functional.
- Nav link added to existing `trading-journal/frontend`.
- `docker-compose.yml` bringing up the full stack for local use.

Scaffolded with interfaces + stubs (return `NotConfiguredError` or a clear
"not configured" response until credentials are set — noted "wired in
follow-up commits"):

- Broker adapters beyond CSV: MT5, Bybit, Darwinex.
- Temporal worker execution — workflow and activity definitions are present
  and importable; requires a running Temporal server to actually schedule.
- Telegram delivery — interface present; requires `TELEGRAM_BOT_TOKEN` +
  `TELEGRAM_CHAT_ID`.
- Qdrant journal search and LLM commentary / pattern detection / pre-trade
  check — interfaces present; require `QDRANT_URL` and `LLM_API_KEY`.
- Tearsheet PDF export — the Monthly Tearsheet screen itself renders in
  browser; PDF generation requires a Chromium or wkhtmltopdf install and
  falls through to an HTML download with a "install Chromium to enable PDF"
  notice until then.

---

## 2. The rules the system must enforce

Copied from Product Brief §2, restated as invariants the code must not violate.

- **R1** Records are append-only. Corrections create new rows that supersede
  old ones; both remain visible with a written reason.
- **R2** Cash flows and NAV live in separate tables. No code path treats a
  deposit as a gain.
- **R3** A day with no mark is not a flat day. Missing days are visually
  distinguished and excluded from every statistic. Zero-padding is forbidden.
- **R4** Composite membership is declared once at account creation with a
  written reason for exclusion. Cannot be changed retroactively.
- **R5** Risk limits are versioned by effective date. Amendments append, never
  update. Amending during a drawdown is blocked (override available, logged).
- **R6** Every metric is presented with its observation count. No bare ratios.
- **R7** The verdict band tells the truth about statistical significance in
  plain English, even when it hurts.

These invariants are enforced at the code level in `core/`, at the schema level
via unique constraints and `superseded_by` FKs, and at the API level via
business rules in the routers. Frontend enforcement is defence-in-depth only.

---

## 3. Repository layout

```
trading-journal/                    (existing repo, existing files untouched)
├── backend/                        (existing; not modified)
├── frontend/                       (existing; single nav link added)
│   └── src/App.tsx                 add: <a href="/tej-capital/" target="_blank">TEJ Capital ↗</a>
└── tej-capital/                    NEW subsystem
    ├── backend/
    │   ├── app/
    │   │   ├── core/               pure functions, no I/O
    │   │   │   ├── returns.py      daily_twr, composite_twr, reconcile, detect_anomalies
    │   │   │   ├── metrics.py      every return/risk/risk-adjusted metric
    │   │   │   ├── stats.py        Sharpe t-stat, PSR, MinTRL, Deflated Sharpe, CI
    │   │   │   ├── trades.py       expectancy, payoff, MAE/MFE, concentration
    │   │   │   ├── attribution.py  grouped stats + verdict tags
    │   │   │   └── verdict.py      plain-English verdict band
    │   │   ├── domain/             SQLAlchemy models
    │   │   ├── api/                FastAPI routers (one file per resource)
    │   │   ├── ingest/             BrokerAdapter Protocol + adapters
    │   │   ├── workflows/          Temporal activities + nightly_close workflow
    │   │   ├── alerts/             telegram.py
    │   │   ├── ai/                 qdrant_search, commentary, pattern_detect, pretrade_check
    │   │   ├── export/             tearsheet_pdf, csv_exports, ddq_pack
    │   │   ├── config.py           pydantic-settings, env-driven
    │   │   ├── db.py               engine + session factory
    │   │   └── main.py             FastAPI app + router registration
    │   ├── migrations/             Alembic (env.py, versions/)
    │   ├── tests/                  pytest — core/ has ≥37 unit tests
    │   ├── pyproject.toml
    │   ├── requirements.txt
    │   ├── Dockerfile
    │   └── alembic.ini
    ├── frontend/
    │   ├── src/
    │   │   ├── pages/              12 screens (§5)
    │   │   ├── components/         metric cards, verdict band, ledger heatmap, monthly grid
    │   │   ├── lib/api.ts          typed client
    │   │   ├── hooks/
    │   │   ├── App.tsx
    │   │   └── main.tsx
    │   ├── index.html
    │   ├── package.json
    │   ├── tsconfig.json
    │   └── vite.config.ts
    ├── docker-compose.yml          postgres (timescale), api, worker, web, caddy
    ├── .env.example
    ├── Caddyfile
    └── README.md
```

The existing `trading-journal/backend/models.py`, `database.py`, etc. are
NOT touched. All new tables are physically in a separate database (`tej_capital`)
in the same Postgres instance, and additionally prefixed `tej_` at the table
level as belt-and-braces isolation.

---

## 4. Data model

All tables prefixed `tej_`. Money columns `Numeric(20, 8)`. No `float`.
Timestamps `TIMESTAMPTZ`. UUIDs for primary keys unless noted.

### 4.1 Core ledger tables

**`tej_accounts`** — broker / prop / demo accounts.
`id, name, broker, currency, account_type (live|prop_funded|prop_evaluation|demo|verified_mirror), in_composite BOOL, exclusion_reason TEXT, created_at, archived_at`.
`in_composite` is set at creation with a written reason when false. Application
code refuses updates that change it.

**`tej_nav_snapshots`** — daily closing equity, append-only.
`id, account_id FK, as_of_date DATE, closing_equity NUMERIC(20,8), superseded_by FK NULL, superseded_reason TEXT NULL, entered_at`.
Unique partial index: `(account_id, as_of_date) WHERE superseded_by IS NULL`
enforces exactly one current mark per account-day. Timescale hypertable on
`as_of_date`.

**`tej_cash_flows`** — deposits, withdrawals, prop payouts, fees, transfers.
`id, account_id FK, as_of_date DATE, amount NUMERIC(20,8) signed, flow_type ENUM(deposit|withdrawal|prop_payout|platform_fee|transfer_in|transfer_out), flow_timing ENUM(start_of_day|end_of_day), note TEXT, entered_at`.

Physically separate from `tej_nav_snapshots` so no query can accidentally add
them together.

**`tej_playbook_setups`** — user's five setups.
`id, tag, name, description, is_active BOOL, retired_at NULL`.

**`tej_trades`** — closed round trips.
`id, account_id FK, setup_id FK NULL, instrument, direction ENUM(long|short), entry_price, exit_price, initial_stop, target_price NULL, position_size, risk_amount, gross_pnl, costs, session ENUM(asia|london|london_ny|new_york|late_ny), htf_aligned BOOL, thesis TEXT, review TEXT, execution_grade ENUM(A|B|C|D) NULL, state_of_mind ENUM(calm|rushed|frustrated|overconfident|tilted) NULL, rule_compliant BOOL, breach_note TEXT NULL, mae_r NUMERIC, mfe_r NUMERIC, opened_at, closed_at, one_sentence_takeaway TEXT`.

R-multiple is computed on read; never stored user-typed. A trade with NULL
`risk_amount` is flagged incomplete and excluded from expectancy calculations.

**`tej_journal_entries`** — daily notes independent of trades.
`id, entry_date DATE, body TEXT, tags TEXT[], created_at`.

### 4.2 Policy tables

**`tej_policy_limits`** — versioned risk limits.
`id, limit_type ENUM(risk_per_trade|concurrent_open_risk|daily_loss|weekly_loss|monthly_loss|drawdown_killswitch|asset_class_concentration|risk_sizing_consistency|avg_loser_vs_1r|rule_compliance_rate), threshold NUMERIC, unit ENUM(pct|r|abs), effective_from DATE, effective_to DATE NULL, committed_action TEXT, created_at`.

Append-only. Latest row per `limit_type` with NULL `effective_to` is the
current version.

**`tej_policy_amendments`** — audit trail of every change.
`id, previous_limit_id FK, new_limit_id FK, reason TEXT, is_override_during_drawdown BOOL, created_at`.

**`tej_limit_breaches`** — evaluated nightly and on-demand.
`id, limit_id FK, breached_on DATE, observed_value NUMERIC, threshold_value NUMERIC, note TEXT, resolved_on DATE NULL`.

**`tej_policy_document`** — free-text sections of the written IPS.
`id, section ENUM(mandate|method|time_horizon|position_sizing|correlation|stop_discipline|news_policy|leverage|valuation|custody|amendment_procedure|review_cadence), body TEXT, updated_at`.

### 4.3 Correction and audit

**`tej_corrections_ledger`** — every supersede across every table.
`id, table_name, row_id UUID, superseded_by_row_id UUID, reason TEXT, corrected_at`.

Populated by database triggers OR application-layer hooks (chosen at
implementation time; both are acceptable, provided coverage is complete).

### 4.4 Derived / computed

**`tej_metric_snapshots`** — frozen daily tearsheet.
`id, as_of_date DATE, scope ENUM(composite|per_account), account_id FK NULL, metrics JSONB, ledger_hash CHAR(64), computed_at`.

`ledger_hash` = SHA-256 over the concatenated primary keys and mutation
timestamps of every row that fed this snapshot, in stable order. Answers "what
did the tearsheet say on 3 March?" and — as a side effect — is exactly the
integrity token a third-party verifier will ask for.

**`tej_daily_returns`** — Timescale continuous aggregate derived from
`tej_nav_snapshots` and `tej_cash_flows`. Backing view for the equity curve.

**`tej_broker_reconciliations`** — nightly diff broker equity vs rebuilt-from-trades equity.
`id, account_id FK, as_of_date DATE, broker_equity NUMERIC, rebuilt_equity NUMERIC, delta NUMERIC, status ENUM(ok|discrepancy|unexplained), note TEXT`.

### 4.5 Settings

**`tej_settings`** — singleton row.
`id (=1), starting_capital, record_start_date, base_currency, risk_free_rate, trading_days_per_year, minimum_acceptable_return, benchmark_sharpe, confidence_level, strategy_variants_tested INT`.

The `strategy_variants_tested` field feeds Deflated Sharpe — explained in the
UI per Product Brief §4.11.

**`tej_targets`** — user-declared targets for the scorecard.
`id, metric_name, target_value, unit`.

---

## 5. Screens (Product Brief §4, verbatim contract)

Twelve pages under `frontend/src/pages/`. Field labels, placeholders and rules
are copied verbatim from the Product Brief; the microcopy is doing work per
§4's explicit note.

| # | Route | Page | Notes |
|---|---|---|---|
| 1 | `/` | Today | Daily mark form + correction mode + missed-days banner + empty state |
| 2 | `/trades/new` | Trade Entry | Two-part: thesis (before) + outcome (after). Enrichment queue for incomplete imports. |
| 3 | `/ledger` | Ledger | Year heatmap. Green/red squares, empty outlines for missing marks. Discipline-streak counter. |
| 4 | `/performance` | Performance | Top 4 headline figures → verdict band → collapsible metric groups → charts (equity + drawdown, top-5 DD table, rolling 63-day Sharpe) |
| 5 | `/monthly` | Monthly Returns | Year×month grid, YTD column, stats below, click-through to month |
| 6 | `/attribution` | Edge Attribution | Grouped by setup / asset / session / HTF / DOW. Verdict column. Concentration warning. Discipline comparison card. |
| 7 | `/policy` | Risk Policy | Live monitor (top) + written IPS (bottom). Amendment flow with drawdown block. |
| 8 | `/accounts` | Accounts & Capital | Account list, capital movements log, prop section, running totals |
| 9 | `/audit` | Audit Trail | Corrections, supersedes, policy amendments, overrides — filterable, exportable |
| 10 | `/tearsheet/:month` | Monthly Tearsheet | One-page factsheet w/ required commentary box |
| 11 | `/settings` | Settings | Starting capital, RFR, benchmark, variants-tested, targets |
| 12 | `/share/:token` | Allocator View | Read-only, shareable, expiring. Journal + emotional-state hidden. |

Rules for every screen (routing to §7 of Product Brief for the full text):

- Every metric shown carries its N.
- Verdict band is prominent on Performance and Tearsheet.
- Never nag more than once about missed days.
- Correction mode reveals the log entry the correction will create before save.
- Policy amendment during drawdown is blocked with a modal offering "override
  and log it" as the only way through.

---

## 6. `core/` — the honest metric engine

Pure functions, no I/O, no config access. Every function takes a pandas
`Series` (or DataFrame for multi-column cases) and returns a scalar or a
`dataclass`. This makes the exact same code runnable in a notebook against a
backtest, against a broker CSV, or against the live ledger — the property that
makes the eventual verifier hand-off cheap.

### 6.1 `core/returns.py`

- `daily_twr(nav: Series, flows: Series, timing: FlowTiming) -> Series`
- `composite_twr(accounts: dict[account_id, tuple[nav, flows]]) -> Series`
  Weighted by beginning-of-day value per account. Rule R4.
- `reconcile(broker_equity: Series, rebuilt_equity: Series) -> ReconResult`
- `detect_anomalies(nav: Series, flows: Series) -> list[Anomaly]`
  Flags: return > 3× daily limit, large deposit + large return same day, mark
  on a market-holiday for the primary instrument.

### 6.2 `core/metrics.py`

Every metric enumerated in Product Brief §5:

Returns — cumulative TWR, CAGR (calendar-annualised), annualised from daily,
average daily, % positive days, avg up day, avg down day, best day, worst day,
total net P&L, net external flows.

Risk — annualised vol, downside deviation, MDD, current DD, longest DD (days),
current days under water, Ulcer Index, VaR 95%, CVaR 95%, skew, excess
kurtosis, top-5 drawdowns (depth, duration, recovery date).

Risk-adjusted — Sharpe, Sortino, Calmar (MAR), Sterling, Burke, Omega,
Gain-to-Pain, Tail ratio, Ulcer Performance Index, Recovery Factor.

Benchmark-conditional — beta, alpha, correlation, R², tracking error,
Information Ratio, upside capture, downside capture.

### 6.3 `core/stats.py`

- `sharpe_t_stat(returns) -> float`
- `probabilistic_sharpe_ratio(returns, benchmark_sharpe=0.0)`
  — Bailey & López de Prado (2012). Accounts for sample length, skew, kurtosis.
- `min_trl(returns, benchmark_sharpe, confidence=0.95) -> int`
- `deflated_sharpe(returns, trials_tested, benchmark_sharpe=0.0)`
  — Bailey & López de Prado (2014). Corrects for selection bias under multiple
  testing. Reads `strategy_variants_tested` from Settings.
- `sharpe_ci(returns, alpha=0.05) -> tuple[float, float]`

### 6.4 `core/trades.py`

- `expectancy_r(trades) -> RiskMultiple`
- `payoff_ratio(trades) -> float`
- `profit_factor(trades) -> float`
- `mae_mfe_stats(trades) -> MAEMFEStats`
- `top_n_concentration(trades, n=3) -> ConcentrationStats`
- `compliance_gap_significance(trades) -> PValue`
  Welch's t-test on expectancy of compliant vs non-compliant trades.
- `streaks(trades) -> Streaks`

### 6.5 `core/attribution.py`

`grouped_stats(trades, by: Literal["setup", "asset", "session", "htf", "dow"])`
returns rows with all trade-level stats + verdict tag drawn from a fixed rule
set:

| Condition | Verdict |
|---|---|
| N < 20 | `not_enough` |
| expectancy > 0.15R | `working` |
| expectancy in (0, 0.15R] | `marginal` |
| expectancy ≤ 0 | `retire` |

### 6.6 `core/verdict.py`

Given a computed metric snapshot and the current N, produces the plain-English
verdict for the Performance and Tearsheet screens. Template drawn verbatim from
Product Brief §4.4 example:

> *"At your observed consistency you need roughly {days_needed} days of data
> before 'my Sharpe beats {threshold}' survives scrutiny. You have {n_days}.
> That's about {years_remaining} more years. Do not raise capital on these
> numbers."*

Templates for other regimes (edge > threshold, PSR > 0.95, MinTRL met, etc.)
included.

### 6.7 Testing

`tests/core/` — one file per module. Every metric has:

- A hand-computed numeric fixture (known series → known value).
- A property test where applicable (TWR invariant to deposits, MDD ≥ current
  DD, PSR monotone in N for fixed distribution, MinTRL formula matches
  published paper example).

Target: ≥37 tests to fulfil the "37-test parity" commitment in Architecture §2.

---

## 7. Ingestion

`ingest/base.py`:

```python
class BrokerAdapter(Protocol):
    name: str
    def fetch_equity(self, since: date) -> pd.Series: ...
    def fetch_closed_trades(self, since: date) -> list[CanonicalTrade]: ...
    def fetch_flows(self, since: date) -> list[CanonicalFlow]: ...
```

Adapters:

1. **`ingest/csv_import.py`** — fully working. Upload a broker CSV, map columns
   once per broker in the UI, mapping persisted per account. Imported trades
   arrive without setup / risk / grades and go into an "enrichment queue" —
   Rule R7 for trade data.
2. **`ingest/mt5_adapter.py`** — interface + stub. Uses `MetaTrader5` Python
   package on a Windows VM; documented in README. Raises `NotConfiguredError`
   until credentials provided.
3. **`ingest/bybit_adapter.py`** — interface + stub. Uses Bybit v5 REST:
   `/v5/account/wallet-balance` for equity, `/v5/position/closed-pnl` for
   trades. Read-only API key, IP-allowlisted. Raises `NotConfiguredError`.
4. **`ingest/darwinex_adapter.py`** — interface + stub. Documented as
   highest-priority-to-wire post-v1 since it is the record allocators will
   verify (Operating Plan §Phase 1). Raises `NotConfiguredError`.

Idempotency at the adapter boundary: every canonical trade or flow has a
`(account_id, external_id)` uniqueness constraint. Re-running a sync is a
no-op.

---

## 8. Nightly close (Temporal, per Architecture §5)

Workflow `nightly_close` scheduled at 22:05 GST.

```
22:05  fetch marks + trades + flows from every configured adapter (activity/adapter, retry 5×)
22:10  reconcile broker equity vs rebuilt-from-trades → tej_broker_reconciliations
22:12  rebuild return series + detect_anomalies() → anomalies table
22:14  evaluate policy limits → tej_limit_breaches rows
22:15  compute_all() → freeze tej_metric_snapshot with ledger_hash
22:20  Telegram: ONE message — P&L, drawdown vs kill-switch, breaches, anomalies, tomorrow's tier-1 calendar
```

Activities are thin wrappers around `core/` functions (Architecture §5's
constraint — the same code runs in the notebook and in the workflow).

Worker lives at `backend/app/workflows/worker.py`. Docker service `worker`.
Requires a Temporal server; `docker-compose.yml` includes an optional
`temporal` service commented out with a note explaining why it's not on by
default (memory cost on Oracle free tier).

---

## 9. Alerts

`alerts/telegram.py` — one function `send_alert(kind, payload)`. `kind` is
`nightly | immediate | weekly | monthly | data_quality`. Never sends more than
one message per day for the same `kind`. Reuses THE DESK bot credentials if
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set; otherwise no-op with a
log line.

Immediate alerts (interrupts): drawdown kill-switch breached, monthly loss
breached, single-day loss > 2× daily limit. That is the entire list — anything
else waits for the nightly digest per Brief §6.

---

## 10. AI layer

Architecture §6 constraint restated: **no LLM ever produces a number that is
published.** LLMs work on the reflective side, not the ledger side.

- **`ai/qdrant_search.py`** — embed `thesis`, `review`, journal bodies into
  Qdrant. Query "trades where I noted hesitation before entry" → returns trade
  IDs → the API joins these back to R-multiples. Requires Qdrant URL and
  embedding-model creds. Ships as interface with `NotConfiguredError` stub.

- **`ai/commentary.py`** — takes a computed monthly tearsheet + that month's
  journal entries, drafts commentary. Constraint: the model receives numbers
  as inputs and may only reference them, never compute them. Prompt template
  is a fixture in the module.

- **`ai/pattern_detect.py`** — statistical tests first (expectancy conditional
  on day-of-week, prior-day outcome, session, hold time, hours since last
  trade), with multiple-comparison correction (Benjamini-Hochberg FDR at
  q=0.10). LLM only phrases the survivors in English. Follows the template of
  `core/trades.compliance_gap_significance`.

- **`ai/pretrade_check.py`** — takes user's written thesis + their playbook
  definition, asks the one question the checklist implies but the user skipped.
  Advisory, non-blocking, never sizes.

All four ship with stubbed backends returning "not configured — set
`LLM_API_KEY` in env" until keys are set. This keeps v1 runnable without any
AI credentials.

---

## 11. Exports (Product Brief §7)

- Monthly tearsheet PDF — `export/tearsheet_pdf.py`, stub uses Playwright /
  Chromium print-to-pdf if installed, else generates HTML and returns a
  "install Chromium to enable PDF export" notice.
- Full daily return series as CSV.
- Full trade log as CSV.
- Full audit trail as CSV.
- DDQ pack as a single ZIP: strategy description, policy document, performance
  history, attribution, correction log. Skeleton included; template text
  follows ILPA DDQ 2.0 section headings.

---

## 12. Frontend integration into existing `trading-journal/frontend`

Precisely one change to the existing app.

Add a nav item labelled `TEJ Capital ↗` that opens `/tej-capital/` in a new
browser tab (`window.open(url, "_blank", "noopener")`). Placed as the last
item in the existing sidebar / top-nav (wherever the existing nav lives —
implementation-time detail).

No routes, no state, no data flow shared. The two frontends never speak.

`/tej-capital/` is served by the TEJ CAPITAL `web` container (nginx in
`docker-compose.yml`) and reverse-proxied by Caddy in front. In local dev, it
runs on port 5174 (existing trading-journal frontend uses 5173) and the nav
link points there.

---

## 13. Deployment (Architecture §7)

`tej-capital/docker-compose.yml`:

- `postgres` — `timescale/timescaledb-ha:pg16`
- `api` — FastAPI via uvicorn, 2 workers
- `worker` — Temporal worker (optional; requires `temporal` service enabled)
- `web` — nginx serving Vite build
- `caddy` — TLS termination + single-user basic auth

Target host: Oracle Cloud free tier. Broker keys required to be read-only and
IP-allowlisted — documented in README as a hard requirement, not a
recommendation. Nightly `pg_dump` to object storage with 90-day retention
included as a cron entry in the `caddy` container (documented, not
automatically enabled).

---

## 14. Testing strategy

- **`core/`** — pytest, ≥37 unit tests as per §6.7. Uses hand-computed
  fixtures.
- **API** — smoke tests only per route. Not the primary test surface; the
  business logic lives in `core/`.
- **DB migrations** — one round-trip test per Alembic revision (up → down → up).
- **Frontend** — one Playwright happy-path: open Today, enter a mark, see it
  appear on the Ledger. Beyond that, ship without frontend tests in v1.

Coverage target: `core/` at 90%+, everything else uncovered acceptable in v1.
Product Brief non-goals are met by concentrating tests where the invariants
live.

---

## 15. What ships in the first commit

The scaffold as described. In particular:

- All 9 milestones' files, models, routes and screens exist.
- Everything runs on `docker compose up`.
- Every stubbed integration (Temporal, Telegram, Qdrant, LLM, non-CSV brokers,
  PDF export) either no-ops silently or returns a clear "not configured"
  response. Tests pass without any external credentials.
- Nav link in existing `trading-journal/frontend` is included in the same PR.
- Alembic migration is a single "initial schema" revision creating every
  `tej_*` table.

The commit that follows the scaffold (post-user-review, out of scope for this
spec) is expected to wire the Temporal worker and start the daily-mark habit.

---

## 16. Known risks (on the record)

1. **Scope-vs-habit tension.** The Product Brief §10 predicts this scope kills
   the project by never getting the daily mark habit. User overrode with the
   scope decision documented at §0. Building the scaffold does not remove this
   risk; only entering marks every evening does.

2. **Placeholders as adoption theatre.** Screens that render but do nothing
   (empty Ledger, empty Attribution) can create a false sense of progress. The
   Empty States (Brief §4.1) are written to say so plainly — this must be
   preserved through implementation.

3. **Deflated Sharpe requires trial count honesty.** The user must enter
   `strategy_variants_tested` accurately in Settings for DSR to mean anything.
   The Settings screen microcopy explains this; enforcement is behavioural, not
   technical.

4. **CSV import is only as clean as the broker's export.** The enrichment
   queue exists to make gaps visible. No amount of code fixes a broker CSV that
   is missing the risk amount.

5. **Ledger hash trust boundary.** SHA-256 over row PKs and mutation timestamps
   assumes the DB itself is not tampered with. That is a physical-security
   assumption; documented in README, not enforced in code.

---

## 17. Non-goals restated

- No mobile app.
- No trading against the ledger (this is not an OMS).
- No multi-account trader onboarding (the schema supports it — the UI is
  single-user).
- No account sharing / social feed / leaderboards.
- No back-testing framework (the metric engine is `core/`; a backtest can call
  it, but no backtester ships).

---

## 18. Open items for the implementation-plan step

Deferred to `writing-plans`, not decided here:

- Exact ORM shape (async SQLAlchemy 2.0 vs sync; both viable).
- Exact frontend state layer (TanStack Query is the obvious choice given
  BuildFactory's convention, but the trading-journal frontend does not use
  it — implementer chooses).
- Playwright test scaffold vs Cypress.
- Alembic autogenerate vs hand-written first revision.
- Which specific charting library (existing `frontend/` uses recharts; carrying
  it into `tej-capital/frontend` is the default).
- Environment variable naming scheme.
- CI wiring (GitHub Actions already exists on this repo — mirror its style).

---

## 19. Sources

- Product Brief (in-conversation, 2026-08-16)
- Architecture doc (in-conversation, 2026-08-16)
- 4-Year Operating Plan (in-conversation, 2026-08-16)
- Bailey & López de Prado (2012), *The Sharpe Ratio Efficient Frontier*, Journal of Risk 15(2)
- Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*, Journal of Portfolio Management 40(5)
- Product Brief cross-references: §2 (rules), §4 (screens), §5 (metrics), §6 (alerts), §7 (exports), §9 (milestones), §10 (failure mode)
- Architecture cross-references: §2 (layers), §4 (ingestion), §5 (nightly), §6 (AI), §7 (deployment)
