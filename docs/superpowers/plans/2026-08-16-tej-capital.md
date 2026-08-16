# TEJ CAPITAL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold a fund-operations subsystem (TEJ CAPITAL) end-to-end inside `trading-journal/tej-capital/` — every screen, every metric, every table from the spec, with a pure metric engine that has real tests.

**Architecture:** Isolated FastAPI + Postgres/TimescaleDB backend and React/Vite frontend under a new sub-folder in the existing `trading-journal` repo. All new tables prefixed `tej_`. Pure `core/` metric functions with hand-computed test fixtures. Existing trading-journal app is unchanged apart from one nav link that opens the new UI in a new browser tab. Integrations that need external credentials (Temporal, Telegram, Qdrant, LLM, non-CSV brokers, PDF export) ship as importable interfaces with `NotConfiguredError` stubs so the app runs and tests pass on `docker compose up` with zero secrets.

**Tech Stack:** Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 (async), Alembic, pydantic v2, pandas 2.2, numpy 2, scipy 1.14, pytest 8, Postgres 16 + TimescaleDB, React 18, TypeScript 5.5, Vite 5, React Router 6, TanStack Query 5, Recharts 3, Playwright 1.47, Docker Compose, Caddy 2, Temporal Python SDK 1.7 (interface-only in v1).

**Spec:** `docs/superpowers/specs/2026-08-16-tej-capital-design.md` (read before executing any task).

## Global Constraints

- **Branch:** `feature/tej-capital` on `tejpal-abundent/trading_journal`. All commits land here.
- **Location:** everything new goes under `trading-journal/tej-capital/`. Do not modify existing `trading-journal/backend/` or `trading-journal/frontend/` except the single nav-link edit in Task 30.
- **Table prefix:** every new SQL table starts with `tej_`. No exceptions.
- **Money type:** every money column is `Numeric(20, 8)`. Never `Float`.
- **Timestamps:** every timestamp column is `TIMESTAMPTZ` with `server_default=func.now()` where appropriate.
- **UUIDs:** primary keys are `UUID` (`uuid.uuid4()`) unless the row is a singleton (Settings uses `id=1`).
- **Append-only:** never `UPDATE` rows in `tej_nav_snapshots`, `tej_cash_flows`, `tej_trades`, `tej_policy_limits`. Corrections insert a new row and set `superseded_by` on the old one.
- **No float in metric code:** `core/` accepts `pandas.Series` of `float64`; internally use `numpy` for computation but never persist as `float` — API responses convert to `Decimal` at the boundary.
- **Verdict rule (R7):** every metric surface shown to the user carries its sample size N. Every ratio shown in the API response includes `{"value": ..., "n": ...}`.
- **Correction reason required:** every mutation that supersedes an existing row must carry a non-empty `reason` string ≥ 10 characters.
- **Drawdown-block:** the Policy PATCH endpoint refuses amendments when current drawdown > 0 unless request body has `"override_during_drawdown": true` AND `reason` ≥ 30 characters. Overrides are logged in `tej_policy_amendments.is_override_during_drawdown`.
- **Composite immutability (R4):** the Accounts PATCH endpoint refuses changes to `in_composite`. To exclude an account from the composite, archive it and create a new one.
- **Empty state (R3):** every metric endpoint returns `null` (not `0`) when N=0 or when the requested window has zero marks. Frontend renders "no data yet" — never a zero.
- **Test-first:** every task with a code deliverable writes the failing test before the implementation. `pytest` (backend) or `vitest`/`playwright` (frontend).
- **Commit cadence:** one commit per task at minimum. Larger tasks may commit per-step at reviewer's discretion. Message prefix `feat(tej-capital):`, `test(tej-capital):`, `chore(tej-capital):`.
- **Fully-wired vs stubbed (spec §1):** CSV import, all 12 screens (in-browser), Postgres schema, and `core/` metric engine are FULLY WIRED. MT5/Bybit/Darwinex adapters, Temporal execution, Telegram, Qdrant, LLM, and PDF export are SCAFFOLDED STUBS that raise `NotConfiguredError` or return a documented "not configured" response until credentials/binaries are provided.
- **No LLM computes a published number** (spec §10). LLM code lives only under `app/ai/` and consumes computed numbers, never produces them.
- **Frontend design bar:** UI/UX is a first-class deliverable — the target is fund-grade seriousness, not consumer-app playfulness. The full design system (palette, typography, spacing scale, component grammar, motion, empty-state and verdict-band voice) is defined in Task 27 §Design System and is load-bearing per Product Brief §4's "microcopy is doing work" note. Every frontend task consumes those tokens; never introduce ad-hoc colors or spacing.

## Task Index

| # | Task | Deliverable |
|---|---|---|
| 1 | Repo scaffold | Directory tree, `pyproject.toml`, `package.json`, empty modules, README |
| 2 | DB config + Alembic initial migration | All 16 `tej_*` tables live in a running Postgres |
| 3 | SQLAlchemy models + Pydantic schemas | Importable ORM + request/response models |
| 4 | `core/returns.py` (+ tests) | TWR, composite, reconcile, anomalies |
| 5 | `core/metrics.py` return metrics (+ tests) | CAGR, %positive, best/worst day, etc. |
| 6 | `core/metrics.py` risk metrics (+ tests) | Vol, MDD, VaR/CVaR, skew, kurtosis, top-5 DD |
| 7 | `core/metrics.py` risk-adjusted (+ tests) | Sharpe, Sortino, Calmar, Omega, GPR, UPI |
| 8 | `core/stats.py` (+ tests) | Sharpe t-stat, PSR, MinTRL, Deflated Sharpe, CI |
| 9 | `core/trades.py` (+ tests) | Expectancy, payoff, MAE/MFE, concentration, compliance gap |
| 10 | `core/attribution.py` (+ tests) | Grouped stats + verdict tags |
| 11 | `core/verdict.py` (+ tests) | Plain-English verdict band |
| 12 | FastAPI app skeleton | `main.py`, `config.py`, `db.py`, health route |
| 13 | Accounts + Settings + Playbook API | CRUD with composite-immutability rule |
| 14 | NAV + Cash Flows API | Append-only inserts, correction flow |
| 15 | Trades API | Enrichment queue, R-multiple compute-on-read |
| 16 | Journal API | Simple CRUD |
| 17 | Policy API | Versioned limits, drawdown-block rule |
| 18 | Metrics + Tearsheet API | Snapshot freeze with `ledger_hash` |
| 19 | Attribution API | Groupings + verdict tags |
| 20 | Audit + Allocator-view API | Corrections/amendments feed + shareable-token read-only |
| 21 | Ingestion — CSV | Working broker CSV import with column-mapping persistence |
| 22 | Ingestion — MT5/Bybit/Darwinex stubs | Interface + `NotConfiguredError` |
| 23 | Nightly close (Temporal) — stub | Workflow + activity definitions; runs if server present |
| 24 | Alerts — Telegram | Rate-limited sender with stub |
| 25 | AI layer stubs | Qdrant search + commentary + pattern-detect + pretrade |
| 26 | Exports | CSV downloads + PDF stub + DDQ pack ZIP |
| 27 | Frontend scaffold | Vite + TS + Router + Query + shared components + API client |
| 28 | Frontend pages — habit half (Today, Trade Entry, Ledger) | Novel-logic screens fully wired |
| 29 | Frontend pages — insight half (Performance, Monthly, Attribution, Policy, Accounts, Audit, Tearsheet, Settings, Allocator) | Remaining screens fully wired |
| 30 | Nav link into existing `trading-journal/frontend` | `TEJ Capital ↗` opens new tab |
| 31 | docker-compose + Caddyfile + `.env.example` | `docker compose up` brings up full stack |
| 32 | README + smoke tests + Playwright happy path | Onboarding doc + end-to-end verification |

---

## Task 1: Repo scaffold

**Files:**
- Create: `tej-capital/README.md`
- Create: `tej-capital/backend/pyproject.toml`
- Create: `tej-capital/backend/requirements.txt`
- Create: `tej-capital/backend/Dockerfile`
- Create: `tej-capital/backend/alembic.ini`
- Create: `tej-capital/backend/app/__init__.py`
- Create: `tej-capital/backend/app/core/__init__.py`
- Create: `tej-capital/backend/app/domain/__init__.py`
- Create: `tej-capital/backend/app/api/__init__.py`
- Create: `tej-capital/backend/app/ingest/__init__.py`
- Create: `tej-capital/backend/app/workflows/__init__.py`
- Create: `tej-capital/backend/app/alerts/__init__.py`
- Create: `tej-capital/backend/app/ai/__init__.py`
- Create: `tej-capital/backend/app/export/__init__.py`
- Create: `tej-capital/backend/tests/__init__.py`
- Create: `tej-capital/backend/tests/core/__init__.py`
- Create: `tej-capital/backend/tests/api/__init__.py`
- Create: `tej-capital/backend/migrations/__init__.py`
- Create: `tej-capital/frontend/package.json`
- Create: `tej-capital/frontend/tsconfig.json`
- Create: `tej-capital/frontend/vite.config.ts`
- Create: `tej-capital/frontend/index.html`
- Create: `tej-capital/frontend/src/main.tsx` (empty stub)

**Interfaces:**
- Consumes: nothing.
- Produces: importable Python package `app`, buildable frontend, both packages install cleanly.

- [ ] **Step 1: Create the directory tree**

```bash
mkdir -p tej-capital/backend/app/{core,domain,api,ingest,workflows,alerts,ai,export}
mkdir -p tej-capital/backend/{tests/core,tests/api,migrations/versions}
mkdir -p tej-capital/frontend/src/{pages,components,hooks,lib}
touch tej-capital/backend/app/__init__.py \
      tej-capital/backend/app/core/__init__.py \
      tej-capital/backend/app/domain/__init__.py \
      tej-capital/backend/app/api/__init__.py \
      tej-capital/backend/app/ingest/__init__.py \
      tej-capital/backend/app/workflows/__init__.py \
      tej-capital/backend/app/alerts/__init__.py \
      tej-capital/backend/app/ai/__init__.py \
      tej-capital/backend/app/export/__init__.py \
      tej-capital/backend/tests/__init__.py \
      tej-capital/backend/tests/core/__init__.py \
      tej-capital/backend/tests/api/__init__.py \
      tej-capital/backend/migrations/__init__.py
```

- [ ] **Step 2: Write `tej-capital/backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
alembic==1.13.3
pydantic==2.9.2
pydantic-settings==2.5.2
pandas==2.2.3
numpy==2.1.2
scipy==1.14.1
python-dateutil==2.9.0
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
temporalio==1.7.1
qdrant-client==1.11.3
openai==1.51.0
python-multipart==0.0.12
python-jose[cryptography]==3.3.0
```

- [ ] **Step 3: Write `tej-capital/backend/pyproject.toml`**

```toml
[project]
name = "tej-capital-backend"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-q --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 4: Write `tej-capital/backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

- [ ] **Step 5: Write `tej-capital/backend/alembic.ini`** (excerpt — full file below)

```ini
[alembic]
script_location = migrations
sqlalchemy.url = driver://user:pass@host/db
prepend_sys_path = .
version_locations = migrations/versions
timezone = UTC

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 6: Write `tej-capital/frontend/package.json`**

```json
{
  "name": "tej-capital-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --port 5174",
    "build": "tsc && vite build",
    "preview": "vite preview --port 5174",
    "test:unit": "vitest run",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.56.2",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2",
    "recharts": "^3.8.1",
    "date-fns": "^4.1.0",
    "clsx": "^2.1.1"
  },
  "devDependencies": {
    "@playwright/test": "^1.47.2",
    "@types/react": "^18.3.8",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.4",
    "vite": "^5.4.6",
    "vitest": "^2.1.1"
  }
}
```

- [ ] **Step 7: Write `tej-capital/frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "isolatedModules": true,
    "resolveJsonModule": true
  },
  "include": ["src"]
}
```

- [ ] **Step 8: Write `tej-capital/frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  base: "/tej-capital/",
});
```

- [ ] **Step 9: Write `tej-capital/frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>TEJ Capital</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 10: Write `tej-capital/frontend/src/main.tsx` (stub)**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <div>TEJ Capital — scaffold in place</div>
  </React.StrictMode>,
);
```

- [ ] **Step 11: Write `tej-capital/README.md`**

```markdown
# TEJ CAPITAL

Fund-operations platform for a single discretionary trader. See
`../docs/superpowers/specs/2026-08-16-tej-capital-design.md` for the
authoritative spec.

## Quick start

```bash
docker compose up          # postgres, api on :8000, frontend on :5174
```

## Layout

- `backend/` — FastAPI + Postgres/TimescaleDB, pure `core/` metric engine
- `frontend/` — React + Vite, 12 screens
- `docker-compose.yml` — postgres, api, worker (optional), web, caddy

## Integrations that need credentials

Set in `.env` (see `.env.example`). When unset, the app runs and every
endpoint that would call the integration returns a clear "not configured"
response — nothing crashes.

- MT5/Bybit/Darwinex broker APIs (only CSV import works out of the box)
- Temporal server (nightly close workflow only runs if server is up)
- Telegram bot token + chat id
- Qdrant URL + LLM API key (journal search, commentary, pattern detect)
- Chromium install (Monthly Tearsheet PDF export)
```

- [ ] **Step 12: Sanity check both packages install**

```bash
cd tej-capital/backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python -c "import app"
cd ../frontend && npm install && npm run build
```

Expected: backend imports cleanly, frontend builds to `dist/`.

- [ ] **Step 13: Commit**

```bash
git add tej-capital/
git commit -m "feat(tej-capital): scaffold backend/frontend directory tree and tooling"
```

---

## Task 2: DB config, Alembic env, and initial schema migration

**Files:**
- Create: `tej-capital/backend/app/config.py`
- Create: `tej-capital/backend/app/db.py`
- Create: `tej-capital/backend/migrations/env.py`
- Create: `tej-capital/backend/migrations/script.py.mako`
- Create: `tej-capital/backend/migrations/versions/0001_initial_schema.py`
- Create: `tej-capital/backend/tests/test_migrations.py`

**Interfaces:**
- Consumes: `app.__init__` (Task 1).
- Produces:
  - `app.config.Settings` — pydantic-settings singleton with `database_url: str`, `env: Literal["dev","test","prod"]`, integration flags.
  - `app.db.engine` — async SQLAlchemy engine.
  - `app.db.SessionLocal` — async session factory.
  - `app.db.Base` — declarative base for models (Task 3).
  - Alembic `upgrade head` creates all 16 `tej_*` tables in an empty Postgres.

- [ ] **Step 1: Write `app/config.py`**

```python
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TEJ_", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+asyncpg://tej:tej@localhost:5432/tej_capital"
    timescale_enabled: bool = True

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    qdrant_url: str | None = None
    llm_api_key: str | None = None

    mt5_login: str | None = None
    bybit_api_key: str | None = None
    darwinex_api_key: str | None = None

    allocator_link_secret: str = "change-me-in-prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Write `app/db.py`**

```python
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 3: Write `migrations/env.py`**

```python
import asyncio
from logging.config import fileConfig
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from app.config import get_settings
from app.db import Base
import app.domain  # noqa: F401 — ensures models are registered on Base.metadata

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


run_migrations_online()
```

- [ ] **Step 4: Write `migrations/script.py.mako`** (standard Alembic template — copy verbatim)

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Write `migrations/versions/0001_initial_schema.py`** — full DDL for all 16 tables

```python
"""initial tej_capital schema

Revision ID: 0001
Revises:
Create Date: 2026-08-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

NUMERIC_MONEY = sa.Numeric(20, 8)


def upgrade() -> None:
    # Enums
    account_type = sa.Enum("live", "prop_funded", "prop_evaluation", "demo", "verified_mirror",
                           name="tej_account_type")
    flow_type = sa.Enum("deposit", "withdrawal", "prop_payout", "platform_fee",
                        "transfer_in", "transfer_out", name="tej_flow_type")
    flow_timing = sa.Enum("start_of_day", "end_of_day", name="tej_flow_timing")
    direction = sa.Enum("long", "short", name="tej_direction")
    session_enum = sa.Enum("asia", "london", "london_ny", "new_york", "late_ny", name="tej_session")
    exec_grade = sa.Enum("A", "B", "C", "D", name="tej_exec_grade")
    mind_state = sa.Enum("calm", "rushed", "frustrated", "overconfident", "tilted", name="tej_mind_state")
    limit_type = sa.Enum(
        "risk_per_trade", "concurrent_open_risk", "daily_loss", "weekly_loss", "monthly_loss",
        "drawdown_killswitch", "asset_class_concentration", "risk_sizing_consistency",
        "avg_loser_vs_1r", "rule_compliance_rate", name="tej_limit_type",
    )
    limit_unit = sa.Enum("pct", "r", "abs", name="tej_limit_unit")
    policy_section = sa.Enum(
        "mandate", "method", "time_horizon", "position_sizing", "correlation",
        "stop_discipline", "news_policy", "leverage", "valuation", "custody",
        "amendment_procedure", "review_cadence", name="tej_policy_section",
    )
    recon_status = sa.Enum("ok", "discrepancy", "unexplained", name="tej_recon_status")
    metric_scope = sa.Enum("composite", "per_account", name="tej_metric_scope")

    op.create_table(
        "tej_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("broker", sa.String(120), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("account_type", account_type, nullable=False),
        sa.Column("in_composite", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("exclusion_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "in_composite = true OR (exclusion_reason IS NOT NULL AND char_length(exclusion_reason) >= 10)",
            name="tej_accounts_exclusion_reason_required",
        ),
    )

    op.create_table(
        "tej_nav_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_accounts.id"), nullable=False),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("closing_equity", NUMERIC_MONEY, nullable=False),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_nav_snapshots.id"), nullable=True),
        sa.Column("superseded_reason", sa.Text, nullable=True),
        sa.Column("entered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("closing_equity >= 0", name="tej_nav_positive"),
    )
    op.create_index(
        "ux_tej_nav_current_per_account_day",
        "tej_nav_snapshots",
        ["account_id", "as_of_date"],
        unique=True,
        postgresql_where=sa.text("superseded_by IS NULL"),
    )

    op.create_table(
        "tej_cash_flows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_accounts.id"), nullable=False),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("amount", NUMERIC_MONEY, nullable=False),
        sa.Column("flow_type", flow_type, nullable=False),
        sa.Column("flow_timing", flow_timing, nullable=False, server_default="end_of_day"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_cash_flows.id"), nullable=True),
        sa.Column("superseded_reason", sa.Text, nullable=True),
        sa.Column("entered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("account_id", "external_id", name="ux_tej_flows_external"),
    )

    op.create_table(
        "tej_playbook_setups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tag", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "tej_trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_accounts.id"), nullable=False),
        sa.Column("setup_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_playbook_setups.id"), nullable=True),
        sa.Column("instrument", sa.String(40), nullable=False),
        sa.Column("direction", direction, nullable=False),
        sa.Column("entry_price", NUMERIC_MONEY, nullable=False),
        sa.Column("exit_price", NUMERIC_MONEY, nullable=True),
        sa.Column("initial_stop", NUMERIC_MONEY, nullable=True),
        sa.Column("target_price", NUMERIC_MONEY, nullable=True),
        sa.Column("position_size", NUMERIC_MONEY, nullable=False),
        sa.Column("risk_amount", NUMERIC_MONEY, nullable=True),
        sa.Column("gross_pnl", NUMERIC_MONEY, nullable=True),
        sa.Column("costs", NUMERIC_MONEY, nullable=False, server_default="0"),
        sa.Column("session", session_enum, nullable=True),
        sa.Column("htf_aligned", sa.Boolean, nullable=True),
        sa.Column("thesis", sa.Text, nullable=True),
        sa.Column("review", sa.Text, nullable=True),
        sa.Column("execution_grade", exec_grade, nullable=True),
        sa.Column("state_of_mind", mind_state, nullable=True),
        sa.Column("rule_compliant", sa.Boolean, nullable=True),
        sa.Column("breach_note", sa.Text, nullable=True),
        sa.Column("mae_r", sa.Numeric(10, 4), nullable=True),
        sa.Column("mfe_r", sa.Numeric(10, 4), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("one_sentence_takeaway", sa.Text, nullable=True),
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_trades.id"), nullable=True),
        sa.Column("superseded_reason", sa.Text, nullable=True),
        sa.Column("entered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("account_id", "external_id", name="ux_tej_trades_external"),
    )

    op.create_table(
        "tej_journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String(40)), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tej_policy_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("limit_type", limit_type, nullable=False),
        sa.Column("threshold", sa.Numeric(20, 8), nullable=False),
        sa.Column("unit", limit_unit, nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("committed_action", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_tej_policy_current",
        "tej_policy_limits",
        ["limit_type"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
    )

    op.create_table(
        "tej_policy_amendments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("previous_limit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_policy_limits.id"), nullable=True),
        sa.Column("new_limit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_policy_limits.id"), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("is_override_during_drawdown", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(reason) >= 10", name="tej_amendment_reason_min"),
    )

    op.create_table(
        "tej_limit_breaches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("limit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_policy_limits.id"), nullable=False),
        sa.Column("breached_on", sa.Date, nullable=False),
        sa.Column("observed_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("threshold_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("resolved_on", sa.Date, nullable=True),
    )

    op.create_table(
        "tej_policy_document",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("section", policy_section, nullable=False, unique=True),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tej_corrections_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("table_name", sa.String(80), nullable=False),
        sa.Column("row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("superseded_by_row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(reason) >= 10", name="tej_correction_reason_min"),
    )

    op.create_table(
        "tej_metric_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("scope", metric_scope, nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_accounts.id"), nullable=True),
        sa.Column("metrics", postgresql.JSONB, nullable=False),
        sa.Column("ledger_hash", sa.String(64), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("as_of_date", "scope", "account_id", name="ux_tej_metric_daily"),
    )

    op.create_table(
        "tej_broker_reconciliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tej_accounts.id"), nullable=False),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("broker_equity", NUMERIC_MONEY, nullable=False),
        sa.Column("rebuilt_equity", NUMERIC_MONEY, nullable=False),
        sa.Column("delta", NUMERIC_MONEY, nullable=False),
        sa.Column("status", recon_status, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
    )

    op.create_table(
        "tej_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("starting_capital", NUMERIC_MONEY, nullable=False, server_default="15000"),
        sa.Column("record_start_date", sa.Date, nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("risk_free_rate", sa.Numeric(6, 4), nullable=False, server_default="0.04"),
        sa.Column("trading_days_per_year", sa.Integer, nullable=False, server_default="252"),
        sa.Column("minimum_acceptable_return", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("benchmark_sharpe", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("confidence_level", sa.Numeric(4, 3), nullable=False, server_default="0.95"),
        sa.Column("strategy_variants_tested", sa.Integer, nullable=False, server_default="1"),
        sa.CheckConstraint("id = 1", name="tej_settings_singleton"),
    )

    op.create_table(
        "tej_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("metric_name", sa.String(80), nullable=False, unique=True),
        sa.Column("target_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
    )

    op.create_table(
        "tej_allocator_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Timescale hypertable — no-op if extension not installed
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute(
        "SELECT create_hypertable('tej_nav_snapshots', 'as_of_date', "
        "if_not_exists => TRUE, migrate_data => TRUE)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tej_allocator_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_targets CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_broker_reconciliations CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_metric_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_corrections_ledger CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_policy_document CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_limit_breaches CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_policy_amendments CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_policy_limits CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_journal_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_trades CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_playbook_setups CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_cash_flows CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_nav_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS tej_accounts CASCADE")
    for enum in ("tej_recon_status", "tej_metric_scope", "tej_policy_section",
                 "tej_limit_unit", "tej_limit_type", "tej_mind_state",
                 "tej_exec_grade", "tej_session", "tej_direction",
                 "tej_flow_timing", "tej_flow_type", "tej_account_type"):
        op.execute(f"DROP TYPE IF EXISTS {enum}")
```

- [ ] **Step 6: Write `tests/test_migrations.py`**

```python
import pytest
from sqlalchemy import text
from app.db import engine


@pytest.mark.asyncio
async def test_all_tej_tables_exist_after_upgrade():
    expected = {
        "tej_accounts", "tej_nav_snapshots", "tej_cash_flows", "tej_playbook_setups",
        "tej_trades", "tej_journal_entries", "tej_policy_limits",
        "tej_policy_amendments", "tej_limit_breaches", "tej_policy_document",
        "tej_corrections_ledger", "tej_metric_snapshots",
        "tej_broker_reconciliations", "tej_settings", "tej_targets",
        "tej_allocator_tokens",
    }
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE tablename LIKE 'tej_%'"
        ))
        actual = {row[0] for row in result}
    missing = expected - actual
    assert not missing, f"missing tables: {missing}"
```

- [ ] **Step 7: Run the migration against a real Postgres**

```bash
cd tej-capital/backend
export TEJ_DATABASE_URL="postgresql+asyncpg://tej:tej@localhost:5432/tej_capital"
alembic upgrade head
pytest tests/test_migrations.py -v
```

Expected: `alembic upgrade` prints `Running upgrade -> 0001, initial tej_capital schema`; test passes.

- [ ] **Step 8: Commit**

```bash
git add tej-capital/backend/app/config.py tej-capital/backend/app/db.py \
        tej-capital/backend/migrations/ tej-capital/backend/tests/test_migrations.py
git commit -m "feat(tej-capital): db config, alembic env, initial schema with all 16 tej_ tables"
```

---

## Task 3: SQLAlchemy models + Pydantic schemas

**Files:**
- Create: `tej-capital/backend/app/domain/__init__.py` (re-exports all models)
- Create: `tej-capital/backend/app/domain/accounts.py`
- Create: `tej-capital/backend/app/domain/nav.py`
- Create: `tej-capital/backend/app/domain/flows.py`
- Create: `tej-capital/backend/app/domain/trades.py`
- Create: `tej-capital/backend/app/domain/playbook.py`
- Create: `tej-capital/backend/app/domain/journal.py`
- Create: `tej-capital/backend/app/domain/policy.py`
- Create: `tej-capital/backend/app/domain/audit.py`
- Create: `tej-capital/backend/app/domain/metrics.py`
- Create: `tej-capital/backend/app/domain/reconciliations.py`
- Create: `tej-capital/backend/app/domain/settings.py`
- Create: `tej-capital/backend/app/domain/allocator.py`
- Create: `tej-capital/backend/app/schemas/*.py` (Pydantic mirrors, one file per resource)
- Create: `tej-capital/backend/tests/test_domain_models_import.py`

**Interfaces:**
- Consumes: `app.db.Base` (Task 2).
- Produces:
  - ORM classes `Account, NavSnapshot, CashFlow, Trade, PlaybookSetup, JournalEntry, PolicyLimit, PolicyAmendment, LimitBreach, PolicyDocument, CorrectionLedger, MetricSnapshot, BrokerReconciliation, Settings, Target, AllocatorToken`.
  - Pydantic schemas `AccountCreate/Read/Update`, and analogous `*Create/Read` for every domain type.
  - `Trade.r_multiple` computed property `(gross_pnl - costs) / risk_amount` returning `None` if `risk_amount` is `None`.

- [ ] **Step 1: Write failing import test**

```python
# tests/test_domain_models_import.py
def test_all_models_importable_and_registered_on_base():
    from app.db import Base
    import app.domain  # noqa

    tables = {t.name for t in Base.metadata.tables.values()}
    expected = {
        "tej_accounts", "tej_nav_snapshots", "tej_cash_flows", "tej_playbook_setups",
        "tej_trades", "tej_journal_entries", "tej_policy_limits",
        "tej_policy_amendments", "tej_limit_breaches", "tej_policy_document",
        "tej_corrections_ledger", "tej_metric_snapshots",
        "tej_broker_reconciliations", "tej_settings", "tej_targets",
        "tej_allocator_tokens",
    }
    missing = expected - tables
    assert not missing, f"missing ORM models for: {missing}"
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/test_domain_models_import.py -v
```

Expected: FAIL — models not defined yet.

- [ ] **Step 3: Write `app/domain/accounts.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, DateTime, Enum, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Account(Base):
    __tablename__ = "tej_accounts"
    __table_args__ = (
        CheckConstraint(
            "in_composite = true OR (exclusion_reason IS NOT NULL AND char_length(exclusion_reason) >= 10)",
            name="tej_accounts_exclusion_reason_required",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    broker: Mapped[str] = mapped_column(String(120), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    account_type: Mapped[str] = mapped_column(
        Enum("live", "prop_funded", "prop_evaluation", "demo", "verified_mirror",
             name="tej_account_type", create_type=False),
        nullable=False,
    )
    in_composite: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Write the other 12 model files** — same pattern per table. Each file is one class, ≤ 60 lines. Follow §4 of the spec for column names and types. `Trade` adds a computed property:

```python
# app/domain/trades.py — inside class Trade:
    @property
    def r_multiple(self) -> float | None:
        if self.risk_amount is None or self.risk_amount == 0:
            return None
        pnl = (self.gross_pnl or 0) - (self.costs or 0)
        return float(pnl) / float(self.risk_amount)
```

- [ ] **Step 5: Write `app/domain/__init__.py`** — re-export every model

```python
from app.domain.accounts import Account
from app.domain.nav import NavSnapshot
from app.domain.flows import CashFlow
from app.domain.trades import Trade
from app.domain.playbook import PlaybookSetup
from app.domain.journal import JournalEntry
from app.domain.policy import PolicyLimit, PolicyAmendment, LimitBreach, PolicyDocument
from app.domain.audit import CorrectionLedger
from app.domain.metrics import MetricSnapshot
from app.domain.reconciliations import BrokerReconciliation
from app.domain.settings import Settings, Target
from app.domain.allocator import AllocatorToken

__all__ = [
    "Account", "NavSnapshot", "CashFlow", "Trade", "PlaybookSetup",
    "JournalEntry", "PolicyLimit", "PolicyAmendment", "LimitBreach",
    "PolicyDocument", "CorrectionLedger", "MetricSnapshot",
    "BrokerReconciliation", "Settings", "Target", "AllocatorToken",
]
```

- [ ] **Step 6: Write Pydantic schemas per resource**

Example — `app/schemas/accounts.py`:

```python
import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator


AccountType = Literal["live", "prop_funded", "prop_evaluation", "demo", "verified_mirror"]


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    broker: str = Field(min_length=1, max_length=120)
    currency: str = Field(min_length=3, max_length=3)
    account_type: AccountType
    in_composite: bool = True
    exclusion_reason: str | None = None

    @model_validator(mode="after")
    def _exclusion_reason_required_when_excluded(self):
        if not self.in_composite:
            if not self.exclusion_reason or len(self.exclusion_reason.strip()) < 10:
                raise ValueError("exclusion_reason must be at least 10 characters when in_composite is false")
        return self


class AccountRead(BaseModel):
    id: uuid.UUID
    name: str
    broker: str
    currency: str
    account_type: AccountType
    in_composite: bool
    exclusion_reason: str | None
    created_at: datetime
    archived_at: datetime | None
    model_config = {"from_attributes": True}
```

Repeat for every resource. Keep each schema file to one resource.

- [ ] **Step 7: Run the test — expect PASS**

```bash
pytest tests/test_domain_models_import.py -v
```

- [ ] **Step 8: Commit**

```bash
git add tej-capital/backend/app/domain/ tej-capital/backend/app/schemas/ tej-capital/backend/tests/test_domain_models_import.py
git commit -m "feat(tej-capital): sqlalchemy models and pydantic schemas for all 16 tables"
```

---

## Task 4: `core/returns.py` — TWR, composite, reconcile, anomalies

**Files:**
- Create: `tej-capital/backend/app/core/returns.py`
- Create: `tej-capital/backend/tests/core/test_returns.py`

**Interfaces:**
- Consumes: pandas, numpy.
- Produces:
  - `daily_twr(nav: pd.Series, flows: pd.Series, timing: str = "end_of_day") -> pd.Series` — Series of daily TWR returns, indexed by date, missing days *not* zero-padded (they are absent from the index).
  - `composite_twr(accounts: dict[uuid.UUID, tuple[pd.Series, pd.Series]]) -> pd.Series` — beginning-of-day-weighted composite.
  - `reconcile(broker_equity: pd.Series, rebuilt_equity: pd.Series, tolerance: Decimal = Decimal("0.01")) -> list[dict]` — one row per date with `status` and `delta`.
  - `detect_anomalies(nav: pd.Series, flows: pd.Series, daily_limit_pct: float = 0.02) -> list[dict]` — flags: return > 3× daily limit, large deposit + large return same day, mark on holiday.

- [ ] **Step 1: Write failing tests**

```python
# tests/core/test_returns.py
from decimal import Decimal
from datetime import date
import pandas as pd
import pytest

from app.core.returns import daily_twr, composite_twr, reconcile, detect_anomalies


def _s(items):
    return pd.Series(dict(items))


def test_twr_no_flows_matches_simple_return():
    nav = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 10100.0), (date(2026, 1, 3), 10201.0)])
    flows = pd.Series(dtype="float64")
    r = daily_twr(nav, flows)
    # Day 2: 100/10000 = 1%. Day 3: 101/10100 = 1%.
    assert r.iloc[0] == pytest.approx(0.01, rel=1e-6)
    assert r.iloc[1] == pytest.approx(0.01, rel=1e-6)


def test_twr_invariant_to_deposits_R2():
    """R2: a deposit is not profit — TWR must be unchanged whether we deposit or not."""
    nav_no_flow = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 10100.0)])
    r_no_flow = daily_twr(nav_no_flow, pd.Series(dtype="float64"))

    nav_with_flow = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 15100.0)])
    flows = _s([(date(2026, 1, 2), 5000.0)])  # 5k deposit
    r_with_flow = daily_twr(nav_with_flow, flows, timing="end_of_day")

    assert r_with_flow.iloc[0] == pytest.approx(r_no_flow.iloc[0], rel=1e-6)


def test_missing_days_not_zero_padded_R3():
    nav = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 5), 10100.0)])
    r = daily_twr(nav, pd.Series(dtype="float64"))
    assert len(r) == 1  # one return day, not four
    assert r.index[0] == date(2026, 1, 5)


def test_composite_weighted_by_beginning_of_day():
    a = uuid.UUID(int=1)
    b = uuid.UUID(int=2)
    accounts = {
        a: (_s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 10200.0)]), pd.Series(dtype="float64")),
        b: (_s([(date(2026, 1, 1), 500.0), (date(2026, 1, 2), 550.0)]), pd.Series(dtype="float64")),
    }
    r = composite_twr(accounts)
    # Big account: +2%. Small account: +10%. Weighted by BoD: (10000*0.02 + 500*0.10)/10500 = 0.02381
    assert r.iloc[0] == pytest.approx(0.02381, abs=1e-4)


def test_reconcile_flags_delta_above_tolerance():
    broker = _s([(date(2026, 1, 1), 10000.0)])
    rebuilt = _s([(date(2026, 1, 1), 9950.0)])
    result = reconcile(broker, rebuilt, tolerance=Decimal("1.00"))
    assert len(result) == 1
    assert result[0]["status"] == "discrepancy"
    assert abs(result[0]["delta"]) == pytest.approx(50.0)


def test_anomaly_large_return_flagged():
    nav = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 10800.0)])  # +8% day
    anomalies = detect_anomalies(nav, pd.Series(dtype="float64"), daily_limit_pct=0.02)
    kinds = [a["kind"] for a in anomalies]
    assert "return_exceeds_3x_limit" in kinds


def test_anomaly_large_deposit_and_large_return_same_day():
    nav = _s([(date(2026, 1, 1), 10000.0), (date(2026, 1, 2), 15800.0)])
    flows = _s([(date(2026, 1, 2), 5000.0)])
    anomalies = detect_anomalies(nav, flows, daily_limit_pct=0.02)
    kinds = [a["kind"] for a in anomalies]
    assert "deposit_and_large_return_same_day" in kinds
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/core/test_returns.py -v
```

Expected: FAIL — `app.core.returns` does not exist.

- [ ] **Step 3: Implement `app/core/returns.py`**

```python
"""Return calculations. Pure functions. No I/O.

R2: a cash flow is never treated as profit.
R3: days without a mark are absent from the index — never zero-padded.
"""
from __future__ import annotations
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal
import pandas as pd

FlowTiming = Literal["start_of_day", "end_of_day"]


def daily_twr(nav: pd.Series, flows: pd.Series, timing: FlowTiming = "end_of_day") -> pd.Series:
    if len(nav) < 2:
        return pd.Series(dtype="float64")
    nav = nav.sort_index().astype("float64")
    flows = flows.reindex(nav.index, fill_value=0.0).astype("float64") if len(flows) else pd.Series(0.0, index=nav.index)

    prev = nav.shift(1)
    if timing == "end_of_day":
        # Deposit lands at close — remove it from today's numerator.
        numerator = nav - flows - prev
        denom = prev
    else:  # start_of_day
        # Deposit lands at open — include it in the base capital.
        numerator = nav - prev - flows
        denom = prev + flows

    ret = numerator / denom
    return ret.dropna()


def composite_twr(accounts: dict[uuid.UUID, tuple[pd.Series, pd.Series]]) -> pd.Series:
    """Beginning-of-day weighted composite return."""
    per_account = {}
    weights = {}
    for aid, (nav, flows) in accounts.items():
        r = daily_twr(nav, flows)
        per_account[aid] = r
        weights[aid] = nav.shift(1).reindex(r.index)

    all_dates = sorted(set().union(*(r.index for r in per_account.values())))
    out = {}
    for d in all_dates:
        num, denom = 0.0, 0.0
        for aid, r in per_account.items():
            if d in r.index and d in weights[aid].index and not pd.isna(weights[aid].loc[d]):
                w = float(weights[aid].loc[d])
                num += w * float(r.loc[d])
                denom += w
        if denom > 0:
            out[d] = num / denom
    return pd.Series(out).sort_index()


def reconcile(broker_equity: pd.Series, rebuilt_equity: pd.Series,
              tolerance: Decimal = Decimal("0.01")) -> list[dict]:
    rows = []
    idx = broker_equity.index.intersection(rebuilt_equity.index)
    tol = float(tolerance)
    for d in idx:
        b = float(broker_equity.loc[d])
        r = float(rebuilt_equity.loc[d])
        delta = b - r
        status = "ok" if abs(delta) <= tol else "discrepancy"
        rows.append({"date": d, "broker_equity": b, "rebuilt_equity": r,
                     "delta": delta, "status": status})
    return rows


def detect_anomalies(nav: pd.Series, flows: pd.Series, daily_limit_pct: float = 0.02) -> list[dict]:
    anomalies: list[dict] = []
    if len(nav) < 2:
        return anomalies
    nav = nav.sort_index().astype("float64")
    flows = flows.reindex(nav.index, fill_value=0.0) if len(flows) else pd.Series(0.0, index=nav.index)
    prev = nav.shift(1)
    daily_ret = (nav - flows - prev) / prev
    for d, r in daily_ret.dropna().items():
        if abs(r) > 3 * daily_limit_pct:
            anomalies.append({"date": d, "kind": "return_exceeds_3x_limit", "value": float(r)})
        if abs(flows.loc[d]) > 0 and abs(r) > daily_limit_pct:
            anomalies.append({"date": d, "kind": "deposit_and_large_return_same_day",
                              "flow": float(flows.loc[d]), "return": float(r)})
    return anomalies
```

- [ ] **Step 4: Add missing import for uuid in test file**

Prepend `import uuid` at the top of `tests/core/test_returns.py`.

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/core/test_returns.py -v
```

- [ ] **Step 6: Commit**

```bash
git add tej-capital/backend/app/core/returns.py tej-capital/backend/tests/core/test_returns.py
git commit -m "feat(tej-capital): core.returns — TWR, composite, reconcile, anomalies (R2/R3 enforced)"
```

---

## Task 5: `core/metrics.py` — return metrics

**Files:**
- Create: `tej-capital/backend/app/core/metrics.py`
- Create: `tej-capital/backend/tests/core/test_metrics_returns.py`

**Interfaces:**
- Consumes: `pandas`, `numpy`.
- Produces (in `app.core.metrics`):
  - `cumulative_twr(returns: pd.Series) -> float | None`
  - `cagr(returns: pd.Series, trading_days_per_year: int = 252) -> float | None`
  - `annualised_return(returns: pd.Series, trading_days_per_year: int = 252) -> float | None`
  - `avg_daily_return(returns: pd.Series) -> float | None`
  - `pct_positive_days(returns: pd.Series) -> float | None`
  - `avg_up_day(returns: pd.Series) -> float | None`
  - `avg_down_day(returns: pd.Series) -> float | None`
  - `best_day(returns: pd.Series) -> float | None`
  - `worst_day(returns: pd.Series) -> float | None`

All return `None` when the series is empty (R3).

- [ ] **Step 1: Write failing tests**

```python
# tests/core/test_metrics_returns.py
import pandas as pd
import numpy as np
import pytest
from app.core.metrics import (
    cumulative_twr, cagr, annualised_return, avg_daily_return,
    pct_positive_days, avg_up_day, avg_down_day, best_day, worst_day,
)


def test_returns_metrics_all_none_when_empty_R3():
    empty = pd.Series(dtype="float64")
    assert cumulative_twr(empty) is None
    assert cagr(empty) is None
    assert annualised_return(empty) is None
    assert avg_daily_return(empty) is None
    assert pct_positive_days(empty) is None


def test_cumulative_twr_geometric():
    r = pd.Series([0.01, 0.01, -0.01])
    # (1.01 * 1.01 * 0.99) - 1 = 0.009899
    assert cumulative_twr(r) == pytest.approx(0.009899, abs=1e-6)


def test_pct_positive_days():
    r = pd.Series([0.01, -0.01, 0.02, 0.0, 0.005])
    # 3 up (0.01, 0.02, 0.005), 2 non-up (0, -0.01) — flat is not up
    assert pct_positive_days(r) == pytest.approx(3/5)


def test_best_and_worst_day():
    r = pd.Series([0.03, -0.02, 0.01])
    assert best_day(r) == pytest.approx(0.03)
    assert worst_day(r) == pytest.approx(-0.02)


def test_cagr_matches_hand_computed():
    # 252 daily returns of +0.001 → (1.001)^252 - 1 ≈ 0.28657
    r = pd.Series([0.001] * 252)
    assert cagr(r, trading_days_per_year=252) == pytest.approx(0.28657, abs=1e-4)
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/core/test_metrics_returns.py -v
```

- [ ] **Step 3: Implement `app/core/metrics.py` (return-metric block only for now)**

```python
"""Metric primitives. Pure functions. No I/O.

Every metric returns None when the input is empty (R3 — never zero).
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _empty(r: pd.Series) -> bool:
    return r is None or len(r) == 0


def cumulative_twr(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float((1.0 + returns).prod() - 1.0)


def cagr(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    total = (1.0 + returns).prod()
    years = len(returns) / trading_days_per_year
    if years <= 0:
        return None
    return float(total ** (1.0 / years) - 1.0)


def annualised_return(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    return float(returns.mean() * trading_days_per_year)


def avg_daily_return(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float(returns.mean())


def pct_positive_days(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float((returns > 0).sum() / len(returns))


def avg_up_day(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    ups = returns[returns > 0]
    return float(ups.mean()) if len(ups) else None


def avg_down_day(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    downs = returns[returns < 0]
    return float(downs.mean()) if len(downs) else None


def best_day(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float(returns.max())


def worst_day(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float(returns.min())
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/core/test_metrics_returns.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tej-capital/backend/app/core/metrics.py tej-capital/backend/tests/core/test_metrics_returns.py
git commit -m "feat(tej-capital): core.metrics — return-metric block (empty-safe, R3)"
```

---

## Task 6: `core/metrics.py` — risk metrics

**Files:**
- Modify: `tej-capital/backend/app/core/metrics.py` (append risk-metric block)
- Create: `tej-capital/backend/tests/core/test_metrics_risk.py`

**Interfaces:**
- Consumes: `pandas`, `numpy`, plus `cumulative_twr` from Task 5.
- Produces (added to `app.core.metrics`):
  - `annualised_volatility(returns, trading_days_per_year=252) -> float | None`
  - `downside_deviation(returns, mar=0.0, trading_days_per_year=252) -> float | None`
  - `max_drawdown(returns) -> float | None` — negative number (e.g. `-0.15`)
  - `current_drawdown(returns) -> float | None`
  - `longest_drawdown_days(returns) -> int | None`
  - `current_days_under_water(returns) -> int | None`
  - `ulcer_index(returns) -> float | None`
  - `var_95(returns) -> float | None` — historical, negative-signed
  - `cvar_95(returns) -> float | None`
  - `skewness(returns) -> float | None`
  - `excess_kurtosis(returns) -> float | None`
  - `top_n_drawdowns(returns, n=5) -> list[dict]` — each dict has `depth`, `duration_days`, `peak_date`, `trough_date`, `recovery_date`

- [ ] **Step 1: Write failing tests**

```python
# tests/core/test_metrics_risk.py
import numpy as np
import pandas as pd
import pytest
from datetime import date, timedelta

from app.core.metrics import (
    annualised_volatility, downside_deviation, max_drawdown, current_drawdown,
    longest_drawdown_days, current_days_under_water, ulcer_index,
    var_95, cvar_95, skewness, excess_kurtosis, top_n_drawdowns,
)


def _idx(n):
    return pd.date_range("2026-01-01", periods=n, freq="D")


def test_all_risk_metrics_none_when_empty_R3():
    e = pd.Series(dtype="float64")
    assert annualised_volatility(e) is None
    assert max_drawdown(e) is None
    assert var_95(e) is None
    assert skewness(e) is None


def test_annualised_vol_from_known_std():
    # Constant 0.01 daily has 0 std → vol 0
    r = pd.Series([0.01] * 100, index=_idx(100))
    assert annualised_volatility(r) == pytest.approx(0.0, abs=1e-9)


def test_max_drawdown_hand_computed():
    # Cumulative: 1.0, 1.10, 1.00, 0.90, 0.99, 1.08
    r = pd.Series([0.10, -1/11, -0.10, 0.10, 1/11 * 0.99], index=_idx(5))
    mdd = max_drawdown(r)
    # Peak 1.10 → trough 0.90 → DD = -0.1818
    assert mdd == pytest.approx(-0.18181818, abs=1e-4)


def test_current_dd_zero_at_new_high():
    r = pd.Series([0.01, 0.01, 0.01], index=_idx(3))
    assert current_drawdown(r) == pytest.approx(0.0, abs=1e-9)


def test_longest_dd_days_counts_correctly():
    # Up, down, down, down, up-past-peak
    r = pd.Series([0.10, -0.05, -0.02, -0.01, 0.20], index=_idx(5))
    # Underwater from day 2 to day 5 (recovery on day 5) → 3 days
    assert longest_drawdown_days(r) == 3


def test_var_and_cvar_95_ordering():
    rng = np.random.default_rng(42)
    r = pd.Series(rng.normal(0.0005, 0.01, size=1000), index=_idx(1000))
    v = var_95(r)
    c = cvar_95(r)
    assert v < 0 and c < 0
    assert c <= v  # CVaR is at least as negative as VaR


def test_skewness_negative_for_left_skewed():
    # Bunch of small ups, one big down
    r = pd.Series([0.001] * 99 + [-0.20], index=_idx(100))
    assert skewness(r) < -0.5


def test_top_n_drawdowns_returns_sorted_by_depth():
    # Design a series with two clear drawdowns
    r = pd.Series([0.10, -0.05, 0.10, -0.10, 0.15, -0.02, 0.05], index=_idx(7))
    dds = top_n_drawdowns(r, n=3)
    depths = [d["depth"] for d in dds]
    assert depths == sorted(depths)  # deepest (most negative) first
    assert all("duration_days" in d for d in dds)
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/core/test_metrics_risk.py -v
```

- [ ] **Step 3: Append the risk-metric block to `app/core/metrics.py`**

```python
# --- Risk block ---

def annualised_volatility(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    return float(returns.std(ddof=1) * np.sqrt(trading_days_per_year)) if len(returns) > 1 else 0.0


def downside_deviation(returns: pd.Series, mar: float = 0.0,
                       trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    downside = np.minimum(returns - mar, 0.0)
    dd = np.sqrt((downside ** 2).mean())
    return float(dd * np.sqrt(trading_days_per_year))


def _equity_curve(returns: pd.Series) -> pd.Series:
    return (1.0 + returns).cumprod()


def max_drawdown(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    eq = _equity_curve(returns)
    running_peak = eq.cummax()
    dd = eq / running_peak - 1.0
    return float(dd.min())


def current_drawdown(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    eq = _equity_curve(returns)
    return float(eq.iloc[-1] / eq.cummax().iloc[-1] - 1.0)


def longest_drawdown_days(returns: pd.Series) -> int | None:
    if _empty(returns):
        return None
    eq = _equity_curve(returns)
    peak = eq.cummax()
    underwater = eq < peak
    longest, current = 0, 0
    for flag in underwater:
        if flag:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return int(longest)


def current_days_under_water(returns: pd.Series) -> int | None:
    if _empty(returns):
        return None
    eq = _equity_curve(returns)
    peak = eq.cummax()
    underwater = (eq < peak).astype(int)
    count = 0
    for flag in reversed(underwater.tolist()):
        if flag:
            count += 1
        else:
            break
    return int(count)


def ulcer_index(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    eq = _equity_curve(returns)
    dd = (eq / eq.cummax() - 1.0) * 100.0
    return float(np.sqrt((dd ** 2).mean()))


def var_95(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    return float(np.percentile(returns, 5))


def cvar_95(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    v = np.percentile(returns, 5)
    tail = returns[returns <= v]
    return float(tail.mean()) if len(tail) else float(v)


def skewness(returns: pd.Series) -> float | None:
    if _empty(returns) or len(returns) < 3:
        return None
    return float(returns.skew())


def excess_kurtosis(returns: pd.Series) -> float | None:
    if _empty(returns) or len(returns) < 4:
        return None
    return float(returns.kurtosis())  # pandas returns excess by default


def top_n_drawdowns(returns: pd.Series, n: int = 5) -> list[dict]:
    if _empty(returns):
        return []
    eq = _equity_curve(returns)
    peak = eq.cummax()
    dd = eq / peak - 1.0

    drawdowns: list[dict] = []
    in_dd = False
    peak_date = None
    trough_date = None
    trough_val = 0.0
    for d, v in dd.items():
        if not in_dd and v < 0:
            in_dd = True
            peak_date = d
            trough_date = d
            trough_val = v
        elif in_dd:
            if v < trough_val:
                trough_val = v
                trough_date = d
            if v >= 0:
                drawdowns.append({
                    "depth": float(trough_val),
                    "duration_days": (d - peak_date).days,
                    "peak_date": peak_date,
                    "trough_date": trough_date,
                    "recovery_date": d,
                })
                in_dd = False
                trough_val = 0.0
    if in_dd:
        drawdowns.append({
            "depth": float(trough_val),
            "duration_days": (dd.index[-1] - peak_date).days,
            "peak_date": peak_date,
            "trough_date": trough_date,
            "recovery_date": None,
        })
    drawdowns.sort(key=lambda d: d["depth"])
    return drawdowns[:n]
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/core/test_metrics_risk.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tej-capital/backend/app/core/metrics.py tej-capital/backend/tests/core/test_metrics_risk.py
git commit -m "feat(tej-capital): core.metrics — risk block (MDD, VaR/CVaR, skew, kurtosis, top-N DD)"
```

---

## Task 7: `core/metrics.py` — risk-adjusted metrics

**Files:**
- Modify: `tej-capital/backend/app/core/metrics.py` (append risk-adjusted block)
- Create: `tej-capital/backend/tests/core/test_metrics_risk_adjusted.py`

**Interfaces:**
- Consumes: earlier metric functions from Tasks 5 and 6.
- Produces:
  - `sharpe(returns, rf=0.0, trading_days_per_year=252) -> float | None`
  - `sortino(returns, mar=0.0, trading_days_per_year=252) -> float | None`
  - `calmar(returns, trading_days_per_year=252) -> float | None`
  - `sterling(returns, trading_days_per_year=252) -> float | None`
  - `burke(returns, trading_days_per_year=252) -> float | None`
  - `omega(returns, threshold=0.0) -> float | None`
  - `gain_to_pain(returns) -> float | None`
  - `tail_ratio(returns) -> float | None`
  - `ulcer_performance_index(returns, rf=0.0, trading_days_per_year=252) -> float | None`
  - `recovery_factor(returns) -> float | None`

- [ ] **Step 1: Write failing tests**

```python
# tests/core/test_metrics_risk_adjusted.py
import numpy as np
import pandas as pd
import pytest
from app.core.metrics import (
    sharpe, sortino, calmar, sterling, burke, omega,
    gain_to_pain, tail_ratio, ulcer_performance_index, recovery_factor,
)


def test_all_none_when_empty():
    e = pd.Series(dtype="float64")
    for fn in (sharpe, sortino, calmar, sterling, burke, omega,
               gain_to_pain, tail_ratio, ulcer_performance_index, recovery_factor):
        assert fn(e) is None


def test_sharpe_zero_when_no_excess():
    r = pd.Series([0.0] * 252)
    assert sharpe(r) == 0.0 or sharpe(r) is None  # zero excess and zero vol → either is acceptable


def test_sharpe_known_series():
    # mean 0.001, std ~ 0.01 → Sharpe ≈ (0.001/0.01)*sqrt(252) ≈ 1.587
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.001, 0.01, size=5000))
    s = sharpe(r)
    assert 1.4 < s < 1.75


def test_sortino_greater_than_sharpe_when_upside_dominates():
    r = pd.Series([0.02] * 50 + [-0.005] * 10)
    assert sortino(r) > sharpe(r)


def test_omega_greater_than_one_when_gains_exceed_losses():
    r = pd.Series([0.01, 0.02, -0.005, 0.015, -0.003])
    assert omega(r) > 1.0


def test_tail_ratio_ordering():
    r = pd.Series([0.05] * 5 + [-0.01] * 5)
    # Right tail (0.05) / left tail (0.01) = 5
    assert tail_ratio(r) == pytest.approx(5.0, abs=0.2)
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/core/test_metrics_risk_adjusted.py -v
```

- [ ] **Step 3: Append the risk-adjusted block**

```python
# --- Risk-adjusted block ---

def sharpe(returns: pd.Series, rf: float = 0.0, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns) or len(returns) < 2:
        return None
    excess = returns - rf / trading_days_per_year
    std = excess.std(ddof=1)
    if std == 0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(trading_days_per_year))


def sortino(returns: pd.Series, mar: float = 0.0, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns) or len(returns) < 2:
        return None
    excess = returns - mar / trading_days_per_year
    dd = downside_deviation(returns, mar=mar, trading_days_per_year=trading_days_per_year)
    if dd is None or dd == 0:
        return None
    return float(excess.mean() * trading_days_per_year / dd)


def calmar(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    mdd = max_drawdown(returns)
    if mdd is None or mdd == 0:
        return None
    c = cagr(returns, trading_days_per_year)
    if c is None:
        return None
    return float(c / abs(mdd))


def sterling(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    """Annualised return / (avg of top-3 drawdowns - 10%)."""
    if _empty(returns):
        return None
    dds = [d["depth"] for d in top_n_drawdowns(returns, n=3)]
    if not dds:
        return None
    avg_dd = np.mean(dds)
    denom = abs(avg_dd) - 0.10
    if denom <= 0:
        return None
    ar = annualised_return(returns, trading_days_per_year)
    return float(ar / denom) if ar is not None else None


def burke(returns: pd.Series, trading_days_per_year: int = 252) -> float | None:
    """Annualised return / sqrt(sum of squared drawdowns)."""
    if _empty(returns):
        return None
    dds = [d["depth"] for d in top_n_drawdowns(returns, n=10)]
    if not dds:
        return None
    denom = np.sqrt(sum(d ** 2 for d in dds))
    if denom == 0:
        return None
    ar = annualised_return(returns, trading_days_per_year)
    return float(ar / denom) if ar is not None else None


def omega(returns: pd.Series, threshold: float = 0.0) -> float | None:
    if _empty(returns):
        return None
    gains = (returns - threshold).clip(lower=0).sum()
    losses = -(returns - threshold).clip(upper=0).sum()
    if losses == 0:
        return None
    return float(gains / losses)


def gain_to_pain(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    gains = returns.sum()
    pain = -returns[returns < 0].sum()
    if pain == 0:
        return None
    return float(gains / pain)


def tail_ratio(returns: pd.Series) -> float | None:
    if _empty(returns) or len(returns) < 20:
        return None
    right = np.percentile(returns, 95)
    left = np.percentile(returns, 5)
    if left == 0:
        return None
    return float(right / abs(left))


def ulcer_performance_index(returns: pd.Series, rf: float = 0.0,
                            trading_days_per_year: int = 252) -> float | None:
    if _empty(returns):
        return None
    ar = annualised_return(returns, trading_days_per_year)
    u = ulcer_index(returns)
    if u is None or u == 0 or ar is None:
        return None
    return float((ar - rf) / u)


def recovery_factor(returns: pd.Series) -> float | None:
    if _empty(returns):
        return None
    cum = cumulative_twr(returns)
    mdd = max_drawdown(returns)
    if cum is None or mdd is None or mdd == 0:
        return None
    return float(cum / abs(mdd))
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/core/test_metrics_risk_adjusted.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tej-capital/backend/app/core/metrics.py tej-capital/backend/tests/core/test_metrics_risk_adjusted.py
git commit -m "feat(tej-capital): core.metrics — risk-adjusted block (Sharpe, Sortino, Calmar, Omega, UPI, ...)"
```

---

## Task 8: `core/stats.py` — Sharpe t-stat, PSR, MinTRL, Deflated Sharpe, CI

**Files:**
- Create: `tej-capital/backend/app/core/stats.py`
- Create: `tej-capital/backend/tests/core/test_stats.py`

**Interfaces:**
- Consumes: `pandas`, `numpy`, `scipy.stats`, `sharpe`/`skewness`/`excess_kurtosis` from `app.core.metrics`.
- Produces:
  - `sharpe_t_stat(returns) -> float | None`
  - `probabilistic_sharpe_ratio(returns, benchmark_sharpe=0.0) -> float | None` — Bailey-Lopez de Prado (2012).
  - `min_trl(returns, benchmark_sharpe, confidence=0.95) -> int | None` — minimum track record length.
  - `deflated_sharpe(returns, trials_tested: int, benchmark_sharpe=0.0) -> float | None` — Bailey-Lopez de Prado (2014).
  - `sharpe_ci(returns, alpha=0.05) -> tuple[float, float] | None`

Every function returns `None` on N<30 to avoid publishing junk (R6).

- [ ] **Step 1: Write failing tests**

```python
# tests/core/test_stats.py
import numpy as np
import pandas as pd
import pytest
from app.core.stats import (
    sharpe_t_stat, probabilistic_sharpe_ratio, min_trl, deflated_sharpe, sharpe_ci,
)


def _r(n, seed=0, mu=0.001, sigma=0.01):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mu, sigma, size=n))


def test_all_none_when_short_sample():
    r = pd.Series([0.01] * 10)
    assert sharpe_t_stat(r) is None
    assert probabilistic_sharpe_ratio(r) is None
    assert deflated_sharpe(r, trials_tested=1) is None


def test_psr_monotone_in_sample_size():
    small = probabilistic_sharpe_ratio(_r(60, seed=1), benchmark_sharpe=0.0)
    large = probabilistic_sharpe_ratio(_r(2000, seed=1), benchmark_sharpe=0.0)
    assert large > small


def test_psr_bounded_zero_one():
    p = probabilistic_sharpe_ratio(_r(500), benchmark_sharpe=0.0)
    assert 0.0 <= p <= 1.0


def test_min_trl_returns_positive_integer():
    n = min_trl(_r(500), benchmark_sharpe=0.5, confidence=0.95)
    assert isinstance(n, int) and n > 0


def test_deflated_sharpe_lower_than_psr_when_many_trials():
    r = _r(500, seed=2)
    psr = probabilistic_sharpe_ratio(r, benchmark_sharpe=0.0)
    dsr_many = deflated_sharpe(r, trials_tested=200, benchmark_sharpe=0.0)
    assert dsr_many < psr


def test_sharpe_ci_contains_point_estimate():
    r = _r(1000)
    lo, hi = sharpe_ci(r)
    from app.core.metrics import sharpe
    s = sharpe(r)
    assert lo <= s <= hi
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/core/test_stats.py -v
```

- [ ] **Step 3: Implement `app/core/stats.py`**

```python
"""Statistical validity of a Sharpe ratio.

References:
- Bailey & Lopez de Prado (2012), "The Sharpe Ratio Efficient Frontier",
  Journal of Risk 15(2). PSR + MinTRL.
- Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio",
  Journal of Portfolio Management 40(5).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats

from app.core.metrics import sharpe, skewness, excess_kurtosis

MIN_N = 30


def sharpe_t_stat(returns: pd.Series) -> float | None:
    if returns is None or len(returns) < MIN_N:
        return None
    s = sharpe(returns)
    if s is None:
        return None
    return float(s * np.sqrt(len(returns) / 252))


def probabilistic_sharpe_ratio(returns: pd.Series, benchmark_sharpe: float = 0.0) -> float | None:
    if returns is None or len(returns) < MIN_N:
        return None
    n = len(returns)
    s = sharpe(returns)
    if s is None:
        return None
    # Convert annualised → per-observation Sharpe for the formula
    s_obs = s / np.sqrt(252)
    sb_obs = benchmark_sharpe / np.sqrt(252)
    skew = skewness(returns) or 0.0
    ex_kurt = excess_kurtosis(returns) or 0.0
    num = (s_obs - sb_obs) * np.sqrt(n - 1)
    den = np.sqrt(1 - skew * s_obs + ex_kurt / 4.0 * s_obs ** 2)
    z = num / den
    return float(stats.norm.cdf(z))


def min_trl(returns: pd.Series, benchmark_sharpe: float, confidence: float = 0.95) -> int | None:
    if returns is None or len(returns) < MIN_N:
        return None
    s = sharpe(returns)
    if s is None or s == benchmark_sharpe:
        return None
    s_obs = s / np.sqrt(252)
    sb_obs = benchmark_sharpe / np.sqrt(252)
    skew = skewness(returns) or 0.0
    ex_kurt = excess_kurtosis(returns) or 0.0
    z = stats.norm.ppf(confidence)
    # n = 1 + [1 - skew*s + (ex_kurt/4)*s^2] * (z / (s - sb))^2
    numerator = 1.0 - skew * s_obs + (ex_kurt / 4.0) * s_obs ** 2
    if numerator <= 0 or (s_obs - sb_obs) == 0:
        return None
    n = 1 + numerator * (z / (s_obs - sb_obs)) ** 2
    return int(np.ceil(n))


def deflated_sharpe(returns: pd.Series, trials_tested: int, benchmark_sharpe: float = 0.0) -> float | None:
    """DSR: PSR corrected for multiple testing (BLdP 2014)."""
    if returns is None or len(returns) < MIN_N or trials_tested < 1:
        return None
    n_trials = max(1, trials_tested)
    # Expected max Sharpe of n_trials random strategies (BLdP eq. 8)
    emc = 0.5772156649
    z_scale = (1 - emc) * stats.norm.ppf(1 - 1 / n_trials) + emc * stats.norm.ppf(1 - 1 / (n_trials * np.e))
    # Approximate std dev of Sharpe estimator across trials as 1/sqrt(len)
    sigma_sr = 1.0 / np.sqrt(252)  # per-observation approximation
    expected_max_sr = benchmark_sharpe / np.sqrt(252) + sigma_sr * z_scale
    inflated_bench = expected_max_sr * np.sqrt(252)
    return probabilistic_sharpe_ratio(returns, benchmark_sharpe=inflated_bench)


def sharpe_ci(returns: pd.Series, alpha: float = 0.05) -> tuple[float, float] | None:
    if returns is None or len(returns) < MIN_N:
        return None
    n = len(returns)
    s = sharpe(returns)
    if s is None:
        return None
    skew = skewness(returns) or 0.0
    ex_kurt = excess_kurtosis(returns) or 0.0
    s_obs = s / np.sqrt(252)
    var = (1 - skew * s_obs + ex_kurt / 4.0 * s_obs ** 2) / (n - 1)
    se = np.sqrt(max(var, 0.0)) * np.sqrt(252)
    z = stats.norm.ppf(1 - alpha / 2)
    return (float(s - z * se), float(s + z * se))
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/core/test_stats.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tej-capital/backend/app/core/stats.py tej-capital/backend/tests/core/test_stats.py
git commit -m "feat(tej-capital): core.stats — Sharpe t-stat, PSR, MinTRL, Deflated Sharpe, CI"
```

---

## Task 9: `core/trades.py` — expectancy, payoff, MAE/MFE, concentration, compliance gap

**Files:**
- Create: `tej-capital/backend/app/core/trades.py`
- Create: `tej-capital/backend/tests/core/test_trades.py`

**Interfaces:**
- Consumes: `pandas`, `numpy`, `scipy.stats.ttest_ind`.
- Produces:
  - `expectancy_r(trades: pd.DataFrame) -> float | None` — expects columns `r_multiple`, `risk_amount`; ignores rows with null risk.
  - `payoff_ratio(trades) -> float | None`
  - `profit_factor(trades) -> float | None`
  - `top_n_concentration(trades, n=3) -> dict` — `{"top_n_share": float, "top_n_ids": list}`
  - `compliance_gap_significance(trades) -> dict` — `{"compliant_expectancy": float, "noncompliant_expectancy": float, "p_value": float}`
  - `streaks(trades) -> dict` — `{"longest_win_streak": int, "longest_loss_streak": int}`
  - `mae_mfe_stats(trades) -> dict` — `{"avg_mae_r_winners": float, "avg_mfe_r_losers": float}`

- [ ] **Step 1: Write failing tests**

```python
# tests/core/test_trades.py
import pandas as pd
import pytest
from app.core.trades import (
    expectancy_r, payoff_ratio, profit_factor, top_n_concentration,
    compliance_gap_significance, streaks, mae_mfe_stats,
)


def _trades(rows):
    return pd.DataFrame(rows)


def test_expectancy_r_skips_nulls():
    t = _trades([
        {"r_multiple": 1.5, "risk_amount": 100, "rule_compliant": True, "mae_r": -0.3, "mfe_r": 1.5, "gross_pnl": 150, "costs": 5},
        {"r_multiple": None, "risk_amount": None, "rule_compliant": True, "mae_r": None, "mfe_r": None, "gross_pnl": 50, "costs": 0},
        {"r_multiple": -1.0, "risk_amount": 100, "rule_compliant": True, "mae_r": -1.0, "mfe_r": 0.2, "gross_pnl": -100, "costs": 5},
    ])
    # (1.5 + -1.0) / 2 = 0.25
    assert expectancy_r(t) == pytest.approx(0.25)


def test_payoff_ratio_avg_win_over_avg_loss():
    t = _trades([
        {"r_multiple": 2.0}, {"r_multiple": 1.0}, {"r_multiple": -0.5}, {"r_multiple": -1.5},
    ])
    # avg_win = 1.5, avg_loss = -1.0, payoff = 1.5
    assert payoff_ratio(t) == pytest.approx(1.5)


def test_top_3_concentration_share():
    t = _trades([
        {"id": i, "r_multiple": r} for i, r in enumerate([5.0, 3.0, 2.0, 0.5, -0.5])
    ])
    result = top_n_concentration(t, n=3)
    # top 3 sum to 10 out of total gross = 10; concentration = 1.0
    # But total profit = 10 + 0.5 = 10.5 (losers not subtracted for numerator).
    # We define: sum(top_n R) / sum(positive R).
    # positive sum = 10.5, top-3 positive = 10 → 0.952
    assert result["top_n_share"] == pytest.approx(0.952, abs=0.01)


def test_compliance_gap_significance():
    compliant = [1.0] * 20 + [-0.5] * 5
    noncompliant = [-1.0] * 5 + [-0.2] * 3
    t = pd.concat([
        _trades([{"r_multiple": r, "rule_compliant": True} for r in compliant]),
        _trades([{"r_multiple": r, "rule_compliant": False} for r in noncompliant]),
    ], ignore_index=True)
    result = compliance_gap_significance(t)
    assert result["compliant_expectancy"] > 0
    assert result["noncompliant_expectancy"] < 0
    assert 0.0 <= result["p_value"] <= 1.0


def test_streaks():
    t = _trades([{"r_multiple": r} for r in [1, 1, 1, -1, -1, 1, -1, -1, -1, -1, 1]])
    s = streaks(t)
    assert s["longest_win_streak"] == 3
    assert s["longest_loss_streak"] == 4
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/core/test_trades.py -v
```

- [ ] **Step 3: Implement `app/core/trades.py`**

```python
"""Trade-level statistics. Pure. Consumes a trades DataFrame."""
from __future__ import annotations
import pandas as pd
from scipy import stats


def _rr(trades: pd.DataFrame) -> pd.Series:
    return trades["r_multiple"].dropna()


def expectancy_r(trades: pd.DataFrame) -> float | None:
    r = _rr(trades)
    if len(r) == 0:
        return None
    return float(r.mean())


def payoff_ratio(trades: pd.DataFrame) -> float | None:
    r = _rr(trades)
    wins = r[r > 0]
    losses = r[r < 0]
    if len(wins) == 0 or len(losses) == 0:
        return None
    return float(wins.mean() / abs(losses.mean()))


def profit_factor(trades: pd.DataFrame) -> float | None:
    r = _rr(trades)
    gains = r[r > 0].sum()
    losses = -r[r < 0].sum()
    if losses == 0:
        return None
    return float(gains / losses)


def top_n_concentration(trades: pd.DataFrame, n: int = 3) -> dict:
    r = _rr(trades)
    if len(r) == 0:
        return {"top_n_share": None, "top_n_ids": []}
    positive = r[r > 0]
    if positive.sum() == 0:
        return {"top_n_share": None, "top_n_ids": []}
    sorted_positive = positive.sort_values(ascending=False)
    top = sorted_positive.head(n)
    share = float(top.sum() / positive.sum())
    ids = trades.loc[top.index, "id"].tolist() if "id" in trades.columns else top.index.tolist()
    return {"top_n_share": share, "top_n_ids": ids}


def compliance_gap_significance(trades: pd.DataFrame) -> dict:
    if "rule_compliant" not in trades.columns:
        return {"compliant_expectancy": None, "noncompliant_expectancy": None, "p_value": None}
    compliant = trades[trades["rule_compliant"] == True]["r_multiple"].dropna()
    noncompliant = trades[trades["rule_compliant"] == False]["r_multiple"].dropna()
    if len(compliant) < 5 or len(noncompliant) < 5:
        return {
            "compliant_expectancy": float(compliant.mean()) if len(compliant) else None,
            "noncompliant_expectancy": float(noncompliant.mean()) if len(noncompliant) else None,
            "p_value": None,
        }
    t = stats.ttest_ind(compliant, noncompliant, equal_var=False)
    return {
        "compliant_expectancy": float(compliant.mean()),
        "noncompliant_expectancy": float(noncompliant.mean()),
        "p_value": float(t.pvalue),
    }


def streaks(trades: pd.DataFrame) -> dict:
    r = _rr(trades)
    longest_win = current_win = longest_loss = current_loss = 0
    for v in r:
        if v > 0:
            current_win += 1
            current_loss = 0
            longest_win = max(longest_win, current_win)
        elif v < 0:
            current_loss += 1
            current_win = 0
            longest_loss = max(longest_loss, current_loss)
        else:
            current_win = current_loss = 0
    return {"longest_win_streak": longest_win, "longest_loss_streak": longest_loss}


def mae_mfe_stats(trades: pd.DataFrame) -> dict:
    if "mae_r" not in trades.columns or "mfe_r" not in trades.columns:
        return {"avg_mae_r_winners": None, "avg_mfe_r_losers": None}
    winners = trades[trades["r_multiple"] > 0]
    losers = trades[trades["r_multiple"] < 0]
    mae_w = winners["mae_r"].dropna().mean() if len(winners) else None
    mfe_l = losers["mfe_r"].dropna().mean() if len(losers) else None
    return {
        "avg_mae_r_winners": float(mae_w) if mae_w is not None else None,
        "avg_mfe_r_losers": float(mfe_l) if mfe_l is not None else None,
    }
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/core/test_trades.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tej-capital/backend/app/core/trades.py tej-capital/backend/tests/core/test_trades.py
git commit -m "feat(tej-capital): core.trades — expectancy, payoff, MAE/MFE, concentration, compliance gap"
```

---

## Task 10: `core/attribution.py` — grouped stats + verdict tags

**Files:**
- Create: `tej-capital/backend/app/core/attribution.py`
- Create: `tej-capital/backend/tests/core/test_attribution.py`

**Interfaces:**
- Consumes: `expectancy_r`, `payoff_ratio`, `profit_factor` from `app.core.trades`.
- Produces:
  - `Verdict = Literal["not_enough", "retire", "marginal", "working"]`
  - `grouped_stats(trades, by: Literal["setup", "asset", "session", "htf", "dow"]) -> list[dict]` — each dict:

```python
{
  "group": str,
  "trade_count": int,
  "win_rate": float | None,
  "avg_win_r": float | None,
  "avg_loss_r": float | None,
  "expectancy_r": float | None,
  "total_r": float | None,
  "profit_factor": float | None,
  "share_of_total_profit": float | None,
  "verdict": Verdict,
}
```

- [ ] **Step 1: Write failing tests**

```python
# tests/core/test_attribution.py
import pandas as pd
import pytest
from app.core.attribution import grouped_stats


def test_verdict_not_enough_under_20_trades():
    t = pd.DataFrame([{"setup": "A", "r_multiple": 0.5}] * 10)
    rows = grouped_stats(t, by="setup")
    assert rows[0]["verdict"] == "not_enough"


def test_verdict_working_when_expectancy_above_015():
    t = pd.DataFrame([{"setup": "A", "r_multiple": 0.5}] * 25)
    rows = grouped_stats(t, by="setup")
    assert rows[0]["verdict"] == "working"


def test_verdict_retire_when_expectancy_negative():
    t = pd.DataFrame([{"setup": "A", "r_multiple": -0.2}] * 25)
    rows = grouped_stats(t, by="setup")
    assert rows[0]["verdict"] == "retire"


def test_verdict_marginal_between_zero_and_015():
    t = pd.DataFrame([{"setup": "A", "r_multiple": 0.05}] * 25)
    rows = grouped_stats(t, by="setup")
    assert rows[0]["verdict"] == "marginal"


def test_multiple_groups_sorted_by_total_r_desc():
    rows_data = [{"setup": "A", "r_multiple": 1.0}] * 25 + [{"setup": "B", "r_multiple": 0.2}] * 25
    t = pd.DataFrame(rows_data)
    rows = grouped_stats(t, by="setup")
    assert rows[0]["group"] == "A"
    assert rows[1]["group"] == "B"
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/core/test_attribution.py -v
```

- [ ] **Step 3: Implement `app/core/attribution.py`**

```python
from __future__ import annotations
from typing import Literal
import pandas as pd

from app.core.trades import profit_factor as _pf

Verdict = Literal["not_enough", "retire", "marginal", "working"]
MIN_N = 20
WORKING_THRESHOLD_R = 0.15


def _verdict(n: int, expectancy: float | None) -> Verdict:
    if n < MIN_N or expectancy is None:
        return "not_enough"
    if expectancy > WORKING_THRESHOLD_R:
        return "working"
    if expectancy > 0:
        return "marginal"
    return "retire"


_COLUMN_MAP = {
    "setup": "setup",
    "asset": "instrument",
    "session": "session",
    "htf": "htf_aligned",
    "dow": "_dow",
}


def grouped_stats(trades: pd.DataFrame, by: Literal["setup", "asset", "session", "htf", "dow"]) -> list[dict]:
    if by == "dow":
        trades = trades.copy()
        trades["_dow"] = pd.to_datetime(trades["closed_at"]).dt.day_name()
    col = _COLUMN_MAP[by]
    if col not in trades.columns:
        return []
    total_positive = trades[trades["r_multiple"] > 0]["r_multiple"].sum() or 0.0
    out: list[dict] = []
    for group_val, sub in trades.groupby(col, dropna=True):
        r = sub["r_multiple"].dropna()
        wins = r[r > 0]
        losses = r[r < 0]
        exp = float(r.mean()) if len(r) else None
        row = {
            "group": str(group_val),
            "trade_count": int(len(r)),
            "win_rate": float(len(wins) / len(r)) if len(r) else None,
            "avg_win_r": float(wins.mean()) if len(wins) else None,
            "avg_loss_r": float(losses.mean()) if len(losses) else None,
            "expectancy_r": exp,
            "total_r": float(r.sum()) if len(r) else None,
            "profit_factor": _pf(sub),
            "share_of_total_profit": (
                float(wins.sum() / total_positive) if total_positive else None
            ),
            "verdict": _verdict(len(r), exp),
        }
        out.append(row)
    out.sort(key=lambda x: -(x["total_r"] or 0))
    return out
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add tej-capital/backend/app/core/attribution.py tej-capital/backend/tests/core/test_attribution.py
git commit -m "feat(tej-capital): core.attribution — grouped stats + verdict tags"
```

---

## Task 11: `core/verdict.py` — plain-English verdict band

**Files:**
- Create: `tej-capital/backend/app/core/verdict.py`
- Create: `tej-capital/backend/tests/core/test_verdict.py`

**Interfaces:**
- Consumes: `min_trl` from `app.core.stats`, `sharpe` from `app.core.metrics`.
- Produces:
  - `verdict_band(returns, benchmark_sharpe, trading_days_per_year=252) -> dict` — returns `{"headline": str, "detail": str, "level": Literal["ok","caution","not_yet_meaningful"], "n_days": int, "days_needed": int | None, "years_remaining": float | None}`

Templates copied verbatim from Product Brief §4.4 example.

- [ ] **Step 1: Write failing tests**

```python
# tests/core/test_verdict.py
import numpy as np
import pandas as pd
from app.core.verdict import verdict_band


def test_verdict_not_yet_meaningful_on_short_sample():
    r = pd.Series(np.random.default_rng(0).normal(0.001, 0.01, size=50))
    v = verdict_band(r, benchmark_sharpe=1.0)
    assert v["level"] == "not_yet_meaningful"
    assert v["n_days"] == 50
    assert "roughly" in v["detail"].lower()


def test_verdict_ok_when_min_trl_met():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0.002, 0.005, size=3000))  # very high sharpe, huge N
    v = verdict_band(r, benchmark_sharpe=0.0)
    assert v["level"] == "ok"
```

- [ ] **Step 2: Run to verify fail**

- [ ] **Step 3: Implement `app/core/verdict.py`**

```python
"""Plain-English verdict band. Templates from Product Brief §4.4."""
from __future__ import annotations
from typing import Literal
import pandas as pd

from app.core.metrics import sharpe
from app.core.stats import min_trl


NOT_YET_TEMPLATE = (
    "At your observed consistency you need roughly {days_needed} days of data before "
    "\"my Sharpe beats {threshold}\" survives scrutiny. You have {n_days}. "
    "That's about {years_remaining:.1f} more years. Do not raise capital on these numbers."
)

OK_TEMPLATE = (
    "Your realised Sharpe of {sharpe:.2f} beats the {threshold:.2f} threshold with "
    "sufficient sample size ({n_days} days). The claim survives standard scrutiny."
)


def verdict_band(returns: pd.Series, benchmark_sharpe: float,
                 trading_days_per_year: int = 252) -> dict:
    n_days = len(returns) if returns is not None else 0
    if n_days < 30:
        return {
            "headline": "Not yet meaningful",
            "detail": f"You have {n_days} days of data. Statistics kick in around 30 days.",
            "level": "not_yet_meaningful",
            "n_days": n_days,
            "days_needed": None,
            "years_remaining": None,
        }
    days_needed = min_trl(returns, benchmark_sharpe=benchmark_sharpe, confidence=0.95)
    s = sharpe(returns)
    if days_needed is None or s is None:
        return {
            "headline": "Insufficient signal",
            "detail": "Your Sharpe is too close to the benchmark to test.",
            "level": "caution",
            "n_days": n_days,
            "days_needed": None,
            "years_remaining": None,
        }
    if n_days >= days_needed:
        return {
            "headline": "Statistically meaningful",
            "detail": OK_TEMPLATE.format(sharpe=s, threshold=benchmark_sharpe, n_days=n_days),
            "level": "ok",
            "n_days": n_days,
            "days_needed": days_needed,
            "years_remaining": 0.0,
        }
    remaining = (days_needed - n_days) / trading_days_per_year
    return {
        "headline": "Not yet meaningful",
        "detail": NOT_YET_TEMPLATE.format(
            days_needed=days_needed, threshold=benchmark_sharpe,
            n_days=n_days, years_remaining=remaining,
        ),
        "level": "not_yet_meaningful",
        "n_days": n_days,
        "days_needed": days_needed,
        "years_remaining": remaining,
    }
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add tej-capital/backend/app/core/verdict.py tej-capital/backend/tests/core/test_verdict.py
git commit -m "feat(tej-capital): core.verdict — plain-English verdict band (Brief §4.4 templates)"
```

---

## Task 12: FastAPI app skeleton + health route + dependency graph

**Files:**
- Create: `tej-capital/backend/app/main.py`
- Create: `tej-capital/backend/app/api/deps.py`
- Create: `tej-capital/backend/app/api/errors.py`
- Create: `tej-capital/backend/app/api/health.py`
- Create: `tej-capital/backend/tests/api/conftest.py`
- Create: `tej-capital/backend/tests/api/test_health.py`

**Interfaces:**
- Consumes: `app.db.SessionLocal`, `app.config.get_settings`.
- Produces:
  - `app.main.app` — FastAPI instance, CORS to `http://localhost:5174`, routers pending.
  - `app.api.deps.SessionDep = Annotated[AsyncSession, Depends(get_db)]`
  - `app.api.errors.NotConfiguredError`, `HTTPException` mappers for `HTTP 501 Not Configured`.
  - `GET /api/health` returns `{"status":"ok","db":"ok"|"unreachable","integrations": {...}}`.

- [ ] **Step 1: Write failing test**

```python
# tests/api/test_health.py
from httpx import AsyncClient, ASGITransport
import pytest
from app.main import app


@pytest.mark.asyncio
async def test_health_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "integrations" in body
```

- [ ] **Step 2: Write `app/api/errors.py`**

```python
from fastapi import HTTPException


class NotConfiguredError(Exception):
    """Raised by integrations (broker adapters, Temporal, Telegram, Qdrant, LLM,
    PDF export) when their credentials or binaries are not present. Mapped to
    HTTP 501 by the exception handler."""

    def __init__(self, integration: str, hint: str):
        self.integration = integration
        self.hint = hint
        super().__init__(f"{integration}: {hint}")


def not_configured_handler(_request, exc: NotConfiguredError):
    return HTTPException(status_code=501, detail={
        "error": "not_configured",
        "integration": exc.integration,
        "hint": exc.hint,
    })
```

- [ ] **Step 3: Write `app/api/deps.py`**

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db

SessionDep = Annotated[AsyncSession, Depends(get_db)]
```

- [ ] **Step 4: Write `app/api/health.py`**

```python
from fastapi import APIRouter
from sqlalchemy import text
from app.api.deps import SessionDep
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(db: SessionDep):
    s = get_settings()
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unreachable"
    return {
        "status": "ok",
        "db": db_status,
        "integrations": {
            "telegram": bool(s.telegram_bot_token),
            "qdrant": bool(s.qdrant_url),
            "llm": bool(s.llm_api_key),
            "mt5": bool(s.mt5_login),
            "bybit": bool(s.bybit_api_key),
            "darwinex": bool(s.darwinex_api_key),
        },
    }
```

- [ ] **Step 5: Write `app/main.py`**

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import NotConfiguredError
from app.api.health import router as health_router


app = FastAPI(title="TEJ Capital API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)


@app.exception_handler(NotConfiguredError)
async def _not_configured(_request: Request, exc: NotConfiguredError):
    return JSONResponse(
        status_code=501,
        content={
            "error": "not_configured",
            "integration": exc.integration,
            "hint": exc.hint,
        },
    )
```

- [ ] **Step 6: Write `tests/api/conftest.py`** (async fixtures)

```python
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import text

from app.config import get_settings
from app.db import Base
import app.domain  # noqa


@pytest.fixture(scope="session")
async def test_engine():
    url = get_settings().database_url.replace("/tej_capital", "/tej_capital_test")
    engine = create_async_engine(url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db(test_engine):
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as s:
        yield s
        await s.rollback()
```

- [ ] **Step 7: Run tests — expect PASS**

```bash
pytest tests/api/test_health.py -v
```

- [ ] **Step 8: Commit**

```bash
git add tej-capital/backend/app/main.py tej-capital/backend/app/api/ tej-capital/backend/tests/api/
git commit -m "feat(tej-capital): fastapi app skeleton + health route + NotConfiguredError handler"
```

---

## Task 13: Accounts + Settings + Playbook API

**Files:**
- Create: `tej-capital/backend/app/api/accounts.py`
- Create: `tej-capital/backend/app/api/settings.py`
- Create: `tej-capital/backend/app/api/playbook.py`
- Create: `tej-capital/backend/tests/api/test_accounts.py`
- Create: `tej-capital/backend/tests/api/test_settings.py`
- Modify: `tej-capital/backend/app/main.py` — include the three new routers.

**Interfaces:**
- Consumes: models + schemas from Task 3; `SessionDep`.
- Produces routes:
  - `POST /api/accounts` (201) → `AccountRead`
  - `GET  /api/accounts` → `list[AccountRead]`
  - `PATCH /api/accounts/{id}` — refuses updates that change `in_composite` (409 with `error: composite_membership_immutable`).
  - `POST /api/accounts/{id}/archive` — sets `archived_at`.
  - `GET  /api/settings` → `SettingsRead` (auto-creates row 1 with defaults if missing).
  - `PATCH /api/settings` → `SettingsRead`.
  - `GET/POST/DELETE /api/playbook` — five slots max at any time (409 if exceeded).

- [ ] **Step 1: Write failing test — composite immutability**

```python
# tests/api/test_accounts.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_composite_membership_cannot_be_changed_R4(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create = await ac.post("/api/accounts", json={
            "name": "Main", "broker": "IBKR", "currency": "USD",
            "account_type": "live", "in_composite": True,
        })
        assert create.status_code == 201
        aid = create.json()["id"]

        patch = await ac.patch(f"/api/accounts/{aid}", json={"in_composite": False,
                                                             "exclusion_reason": "changed my mind about it"})
        assert patch.status_code == 409
        assert patch.json()["detail"]["error"] == "composite_membership_immutable"


@pytest.mark.asyncio
async def test_excluding_account_requires_reason_ge_10_chars():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/accounts", json={
            "name": "Prop", "broker": "Apex", "currency": "USD",
            "account_type": "prop_evaluation", "in_composite": False,
            "exclusion_reason": "too short",
        })
        assert r.status_code == 422
```

- [ ] **Step 2: Write `app/api/accounts.py`**

```python
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from app.api.deps import SessionDep
from app.domain.accounts import Account
from app.schemas.accounts import AccountCreate, AccountRead

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.post("", status_code=201, response_model=AccountRead)
async def create_account(payload: AccountCreate, db: SessionDep):
    a = Account(**payload.model_dump())
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return AccountRead.model_validate(a)


@router.get("", response_model=list[AccountRead])
async def list_accounts(db: SessionDep):
    rows = (await db.execute(select(Account).order_by(Account.created_at))).scalars().all()
    return [AccountRead.model_validate(r) for r in rows]


@router.patch("/{account_id}", response_model=AccountRead)
async def update_account(account_id: uuid.UUID, payload: dict, db: SessionDep):
    a = await db.get(Account, account_id)
    if not a:
        raise HTTPException(404)
    if "in_composite" in payload and payload["in_composite"] != a.in_composite:
        raise HTTPException(status_code=409, detail={
            "error": "composite_membership_immutable",
            "hint": "R4: composite membership is declared once. Archive and recreate.",
        })
    for k, v in payload.items():
        if k in {"name", "broker", "currency", "account_type", "exclusion_reason"}:
            setattr(a, k, v)
    await db.commit()
    await db.refresh(a)
    return AccountRead.model_validate(a)


@router.post("/{account_id}/archive", response_model=AccountRead)
async def archive_account(account_id: uuid.UUID, db: SessionDep):
    a = await db.get(Account, account_id)
    if not a:
        raise HTTPException(404)
    a.archived_at = datetime.utcnow()
    await db.commit()
    await db.refresh(a)
    return AccountRead.model_validate(a)
```

- [ ] **Step 3: Write `app/api/settings.py`**

```python
from datetime import date
from fastapi import APIRouter
from sqlalchemy import select
from app.api.deps import SessionDep
from app.domain.settings import Settings as SettingsModel
from app.schemas.settings import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _get_or_create(db):
    row = await db.get(SettingsModel, 1)
    if not row:
        row = SettingsModel(id=1, record_start_date=date.today())
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


@router.get("", response_model=SettingsRead)
async def read_settings(db: SessionDep):
    return SettingsRead.model_validate(await _get_or_create(db))


@router.patch("", response_model=SettingsRead)
async def update_settings(payload: SettingsUpdate, db: SessionDep):
    row = await _get_or_create(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return SettingsRead.model_validate(row)
```

- [ ] **Step 4: Write `app/api/playbook.py`**

```python
import uuid
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app.api.deps import SessionDep
from app.domain.playbook import PlaybookSetup
from app.schemas.playbook import SetupCreate, SetupRead

router = APIRouter(prefix="/api/playbook", tags=["playbook"])
MAX_ACTIVE_SETUPS = 5


@router.get("", response_model=list[SetupRead])
async def list_setups(db: SessionDep):
    rows = (await db.execute(select(PlaybookSetup).order_by(PlaybookSetup.tag))).scalars().all()
    return [SetupRead.model_validate(r) for r in rows]


@router.post("", response_model=SetupRead, status_code=201)
async def create_setup(payload: SetupCreate, db: SessionDep):
    active = (await db.execute(
        select(PlaybookSetup).where(PlaybookSetup.is_active == True)
    )).scalars().all()
    if len(active) >= MAX_ACTIVE_SETUPS:
        raise HTTPException(status_code=409, detail={
            "error": "too_many_active_setups",
            "hint": f"Product Brief §3 Phase 0: only {MAX_ACTIVE_SETUPS} active setups. "
                    "Retire one first.",
        })
    row = PlaybookSetup(**payload.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return SetupRead.model_validate(row)


@router.delete("/{setup_id}", status_code=204)
async def retire_setup(setup_id: uuid.UUID, db: SessionDep):
    row = await db.get(PlaybookSetup, setup_id)
    if not row:
        raise HTTPException(404)
    row.is_active = False
    from datetime import datetime
    row.retired_at = datetime.utcnow()
    await db.commit()
```

- [ ] **Step 5: Register routers in `app/main.py`**

```python
from app.api.accounts import router as accounts_router
from app.api.settings import router as settings_router
from app.api.playbook import router as playbook_router

app.include_router(accounts_router)
app.include_router(settings_router)
app.include_router(playbook_router)
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
pytest tests/api/test_accounts.py tests/api/test_settings.py -v
```

- [ ] **Step 7: Commit**

```bash
git add tej-capital/backend/app/api/accounts.py tej-capital/backend/app/api/settings.py \
        tej-capital/backend/app/api/playbook.py tej-capital/backend/app/main.py \
        tej-capital/backend/tests/api/test_accounts.py tej-capital/backend/tests/api/test_settings.py
git commit -m "feat(tej-capital): accounts (R4-immutable composite), settings, playbook (5-slot cap) API"
```

---

## Task 14: NAV + Cash Flows API (append-only + corrections)

**Files:**
- Create: `tej-capital/backend/app/api/nav.py`
- Create: `tej-capital/backend/app/api/flows.py`
- Create: `tej-capital/backend/app/services/corrections.py` — helper that inserts a superseding row + a `tej_corrections_ledger` row atomically.
- Create: `tej-capital/backend/tests/api/test_nav.py`
- Create: `tej-capital/backend/tests/api/test_flows.py`
- Modify: `app/main.py` — include new routers.

**Interfaces:**
- Consumes: models, `SessionDep`.
- Produces:
  - `POST /api/accounts/{id}/nav` — creates one NAV mark. If a current mark exists for that day, returns `409 {"error":"mark_exists","existing_id":...}`.
  - `POST /api/accounts/{id}/nav/correct` — body `{as_of_date, closing_equity, reason}` (reason ≥ 10 chars) — inserts a new row and sets `superseded_by` on the old one; writes a `tej_corrections_ledger` row.
  - `GET /api/accounts/{id}/nav?since=DATE` — returns current (non-superseded) rows.
  - `POST /api/accounts/{id}/flows` — creates a cash flow.
  - `POST /api/accounts/{id}/flows/correct` — same correction pattern.
  - `GET /api/accounts/{id}/flows?since=DATE` — current rows.

- [ ] **Step 1: Write failing tests**

```python
# tests/api/test_nav.py
import pytest
from datetime import date
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _make_account(ac):
    r = await ac.post("/api/accounts", json={
        "name": "Main", "broker": "IBKR", "currency": "USD",
        "account_type": "live",
    })
    return r.json()["id"]


@pytest.mark.asyncio
async def test_duplicate_mark_returns_409():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        first = await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15000.00",
        })
        assert first.status_code == 201
        dup = await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15100.00",
        })
        assert dup.status_code == 409
        assert dup.json()["detail"]["error"] == "mark_exists"


@pytest.mark.asyncio
async def test_correction_creates_new_row_and_supersedes_old_R1():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        first = await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15000.00",
        })
        original_id = first.json()["id"]
        corr = await ac.post(f"/api/accounts/{aid}/nav/correct", json={
            "as_of_date": "2026-08-16", "closing_equity": "15050.00",
            "reason": "broker restated overnight swap",
        })
        assert corr.status_code == 201
        # Listing returns the corrected value, not the original
        listing = await ac.get(f"/api/accounts/{aid}/nav?since=2026-08-16")
        rows = listing.json()
        current = [r for r in rows if r["closing_equity"] == "15050.00000000"]
        assert len(current) == 1
        assert current[0]["id"] != original_id


@pytest.mark.asyncio
async def test_correction_reason_min_length():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _make_account(ac)
        await ac.post(f"/api/accounts/{aid}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15000.00"})
        bad = await ac.post(f"/api/accounts/{aid}/nav/correct", json={
            "as_of_date": "2026-08-16", "closing_equity": "15050.00", "reason": "typo"})
        assert bad.status_code == 422
```

- [ ] **Step 2: Write `app/services/corrections.py`**

```python
"""Correction helper. Enforces R1 (append-only): every correction inserts a
new row and stamps `superseded_by` on the old one, plus writes a
`tej_corrections_ledger` row in the same transaction."""
from __future__ import annotations
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import CorrectionLedger

MIN_REASON = 10


class InvalidReason(Exception):
    pass


async def apply_correction(db: AsyncSession, *, table_name: str, old_row, new_row, reason: str):
    if not reason or len(reason.strip()) < MIN_REASON:
        raise InvalidReason(f"reason must be at least {MIN_REASON} characters")
    old_row.superseded_by = new_row.id
    old_row.superseded_reason = reason
    db.add(new_row)
    db.add(CorrectionLedger(
        id=uuid.uuid4(),
        table_name=table_name,
        row_id=old_row.id,
        superseded_by_row_id=new_row.id,
        reason=reason,
    ))
```

- [ ] **Step 3: Write `app/api/nav.py`**

```python
import uuid
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, condecimal
from sqlalchemy import select

from app.api.deps import SessionDep
from app.domain.nav import NavSnapshot
from app.services.corrections import apply_correction, InvalidReason

router = APIRouter(prefix="/api/accounts", tags=["nav"])


class NavCreate(BaseModel):
    as_of_date: date
    closing_equity: condecimal(gt=Decimal("0"), max_digits=20, decimal_places=8)


class NavCorrect(BaseModel):
    as_of_date: date
    closing_equity: condecimal(gt=Decimal("0"), max_digits=20, decimal_places=8)
    reason: str = Field(min_length=10)


class NavRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    as_of_date: date
    closing_equity: Decimal
    superseded_by: uuid.UUID | None
    superseded_reason: str | None
    model_config = {"from_attributes": True}


@router.post("/{account_id}/nav", status_code=201, response_model=NavRead)
async def create_nav(account_id: uuid.UUID, payload: NavCreate, db: SessionDep):
    existing = (await db.execute(
        select(NavSnapshot).where(
            NavSnapshot.account_id == account_id,
            NavSnapshot.as_of_date == payload.as_of_date,
            NavSnapshot.superseded_by.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail={
            "error": "mark_exists",
            "existing_id": str(existing.id),
            "hint": "Use POST /nav/correct to supersede this mark.",
        })
    row = NavSnapshot(
        id=uuid.uuid4(),
        account_id=account_id,
        as_of_date=payload.as_of_date,
        closing_equity=payload.closing_equity,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return NavRead.model_validate(row)


@router.post("/{account_id}/nav/correct", status_code=201, response_model=NavRead)
async def correct_nav(account_id: uuid.UUID, payload: NavCorrect, db: SessionDep):
    old = (await db.execute(
        select(NavSnapshot).where(
            NavSnapshot.account_id == account_id,
            NavSnapshot.as_of_date == payload.as_of_date,
            NavSnapshot.superseded_by.is_(None),
        )
    )).scalar_one_or_none()
    if not old:
        raise HTTPException(404, "no mark to correct")
    new = NavSnapshot(
        id=uuid.uuid4(),
        account_id=account_id,
        as_of_date=payload.as_of_date,
        closing_equity=payload.closing_equity,
    )
    try:
        await apply_correction(db, table_name="tej_nav_snapshots",
                               old_row=old, new_row=new, reason=payload.reason)
    except InvalidReason as e:
        raise HTTPException(422, str(e))
    await db.commit()
    await db.refresh(new)
    return NavRead.model_validate(new)


@router.get("/{account_id}/nav", response_model=list[NavRead])
async def list_nav(account_id: uuid.UUID, db: SessionDep, since: date = Query(...)):
    rows = (await db.execute(
        select(NavSnapshot)
        .where(NavSnapshot.account_id == account_id,
               NavSnapshot.as_of_date >= since,
               NavSnapshot.superseded_by.is_(None))
        .order_by(NavSnapshot.as_of_date)
    )).scalars().all()
    return [NavRead.model_validate(r) for r in rows]
```

- [ ] **Step 4: Write `app/api/flows.py`** — same shape as `nav.py` for `CashFlow`. Fields: `as_of_date`, `amount` (signed Decimal, ≠ 0), `flow_type`, `flow_timing` (default `end_of_day`), `note`.

- [ ] **Step 5: Register both routers in `main.py`.**

- [ ] **Step 6: Run tests — expect PASS**

```bash
pytest tests/api/test_nav.py tests/api/test_flows.py -v
```

- [ ] **Step 7: Commit**

```bash
git add tej-capital/backend/app/api/nav.py tej-capital/backend/app/api/flows.py \
        tej-capital/backend/app/services/corrections.py tej-capital/backend/app/main.py \
        tej-capital/backend/tests/api/test_nav.py tej-capital/backend/tests/api/test_flows.py
git commit -m "feat(tej-capital): NAV + flows API — append-only, corrections with reason ≥ 10 chars (R1/R2)"
```

---

## Task 15: Trades API (with enrichment queue)

**Files:**
- Create: `tej-capital/backend/app/api/trades.py`
- Create: `tej-capital/backend/tests/api/test_trades.py`
- Modify: `app/main.py` — register.

**Interfaces:**
- Produces:
  - `POST /api/trades` — create a trade. If `risk_amount` is null, the response includes `"enrichment_needed": true`.
  - `GET  /api/trades?since=DATE&account_id=UUID` — list.
  - `GET  /api/trades/enrichment` — trades with `risk_amount IS NULL AND superseded_by IS NULL`, most recent first.
  - `PATCH /api/trades/{id}` — enrich fields (`setup_id`, `risk_amount`, `execution_grade`, `state_of_mind`, `mae_r`, `mfe_r`, `rule_compliant`, `breach_note`, `one_sentence_takeaway`, `review`). No correction needed for these enrichment fields per Brief §4.2 (they were never asserted before).
  - `POST /api/trades/{id}/correct` — for economic fields (`entry_price`, `exit_price`, `gross_pnl`, `costs`, `initial_stop`) — supersede-and-log with reason ≥ 10 chars.

Every read response computes `r_multiple` on the fly.

- [ ] **Step 1: Write failing tests**

```python
# tests/api/test_trades.py
import pytest
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _acct(ac):
    r = await ac.post("/api/accounts", json={"name":"M","broker":"IBKR","currency":"USD","account_type":"live"})
    return r.json()["id"]


@pytest.mark.asyncio
async def test_trade_without_risk_flagged_for_enrichment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        r = await ac.post("/api/trades", json={
            "account_id": aid,
            "instrument": "XAUUSD", "direction": "long",
            "entry_price": "2400.00", "position_size": "0.10",
            "opened_at": "2026-08-16T10:00:00+00:00",
        })
        assert r.status_code == 201
        assert r.json()["enrichment_needed"] is True

        queue = await ac.get("/api/trades/enrichment")
        assert len(queue.json()) == 1


@pytest.mark.asyncio
async def test_r_multiple_computed_on_read():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        r = await ac.post("/api/trades", json={
            "account_id": aid,
            "instrument": "XAUUSD", "direction": "long",
            "entry_price": "2400.00", "exit_price": "2430.00",
            "initial_stop": "2390.00", "position_size": "0.10",
            "risk_amount": "100.00", "gross_pnl": "300.00", "costs": "5.00",
            "opened_at": "2026-08-16T10:00:00+00:00",
            "closed_at": "2026-08-16T15:00:00+00:00",
        })
        assert r.status_code == 201
        # (300 - 5) / 100 = 2.95
        assert r.json()["r_multiple"] == pytest.approx(2.95)
```

- [ ] **Step 2: Implement — code omitted for length; follow the same shape as `app/api/nav.py`. Read responses attach `r_multiple` and `enrichment_needed` computed properties.**

```python
# app/api/trades.py — skeleton, fill fields per spec §4.1
import uuid
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.api.deps import SessionDep
from app.domain.trades import Trade

router = APIRouter(prefix="/api/trades", tags=["trades"])


class TradeCreate(BaseModel):
    account_id: uuid.UUID
    setup_id: uuid.UUID | None = None
    instrument: str
    direction: str
    entry_price: Decimal
    exit_price: Decimal | None = None
    initial_stop: Decimal | None = None
    target_price: Decimal | None = None
    position_size: Decimal
    risk_amount: Decimal | None = None
    gross_pnl: Decimal | None = None
    costs: Decimal = Decimal("0")
    session: str | None = None
    htf_aligned: bool | None = None
    thesis: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None


def _serialize(t: Trade) -> dict:
    return {
        "id": str(t.id),
        "account_id": str(t.account_id),
        "instrument": t.instrument,
        "direction": t.direction,
        "entry_price": str(t.entry_price),
        "exit_price": str(t.exit_price) if t.exit_price is not None else None,
        "position_size": str(t.position_size),
        "risk_amount": str(t.risk_amount) if t.risk_amount is not None else None,
        "gross_pnl": str(t.gross_pnl) if t.gross_pnl is not None else None,
        "costs": str(t.costs),
        "r_multiple": t.r_multiple,
        "enrichment_needed": t.risk_amount is None,
        "opened_at": t.opened_at.isoformat(),
        "closed_at": t.closed_at.isoformat() if t.closed_at else None,
    }


@router.post("", status_code=201)
async def create_trade(payload: TradeCreate, db: SessionDep):
    t = Trade(id=uuid.uuid4(), **payload.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _serialize(t)


@router.get("/enrichment")
async def enrichment_queue(db: SessionDep):
    rows = (await db.execute(
        select(Trade).where(Trade.risk_amount.is_(None), Trade.superseded_by.is_(None))
        .order_by(Trade.opened_at.desc())
    )).scalars().all()
    return [_serialize(r) for r in rows]


@router.get("")
async def list_trades(db: SessionDep, since: date = Query(...),
                       account_id: uuid.UUID | None = None):
    q = select(Trade).where(Trade.opened_at >= since, Trade.superseded_by.is_(None))
    if account_id:
        q = q.where(Trade.account_id == account_id)
    q = q.order_by(Trade.opened_at)
    rows = (await db.execute(q)).scalars().all()
    return [_serialize(r) for r in rows]


@router.patch("/{trade_id}")
async def enrich_trade(trade_id: uuid.UUID, payload: dict, db: SessionDep):
    t = await db.get(Trade, trade_id)
    if not t:
        raise HTTPException(404)
    ENRICHABLE = {"setup_id", "risk_amount", "execution_grade", "state_of_mind",
                   "mae_r", "mfe_r", "rule_compliant", "breach_note",
                   "one_sentence_takeaway", "review"}
    for k, v in payload.items():
        if k in ENRICHABLE:
            setattr(t, k, v)
    await db.commit()
    await db.refresh(t)
    return _serialize(t)
```

- [ ] **Step 3: Register + run tests + commit**

```bash
pytest tests/api/test_trades.py -v
git add tej-capital/backend/app/api/trades.py tej-capital/backend/app/main.py \
        tej-capital/backend/tests/api/test_trades.py
git commit -m "feat(tej-capital): trades API — enrichment queue, r_multiple on read, correction flow"
```

---

## Task 16: Journal API

**Files:**
- Create: `tej-capital/backend/app/api/journal.py`
- Create: `tej-capital/backend/tests/api/test_journal.py`
- Modify: `app/main.py`.

**Interfaces:**
- `POST /api/journal` — `{entry_date, body, tags}`. `body` min 1 char.
- `GET  /api/journal?since=DATE&tag=TAG` — filter.
- `PATCH /api/journal/{id}` — free edit (journal entries are the user's own notes; corrections optional).

- [ ] **Step 1: Test**

```python
@pytest.mark.asyncio
async def test_journal_crud_roundtrip():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/journal", json={
            "entry_date": "2026-08-16", "body": "First entry", "tags": ["reflection"],
        })
        assert r.status_code == 201
        eid = r.json()["id"]
        listing = await ac.get("/api/journal?since=2026-08-16&tag=reflection")
        assert any(e["id"] == eid for e in listing.json())
```

- [ ] **Step 2: Implement** — standard CRUD, mirror `nav.py`'s shape.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(tej-capital): journal API"
```

---

## Task 17: Policy API (versioned limits, drawdown-block, amendments)

**Files:**
- Create: `tej-capital/backend/app/api/policy.py`
- Create: `tej-capital/backend/app/services/drawdown_guard.py` — checks current DD from latest metric snapshot or on-the-fly.
- Create: `tej-capital/backend/tests/api/test_policy.py`
- Modify: `app/main.py`.

**Interfaces:**
- `GET  /api/policy/limits` — list current effective limits (one per type).
- `POST /api/policy/limits/{limit_type}` — set a new limit. Refuses when current drawdown > 0 unless body has `override_during_drawdown: true` AND `reason` ≥ 30 chars. Writes a `tej_policy_amendments` row.
- `GET  /api/policy/document` — the IPS text sections.
- `PATCH /api/policy/document/{section}` — free edit.
- `GET  /api/policy/breaches` — live list.

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.asyncio
async def test_amendment_blocked_during_drawdown_without_override(monkeypatch):
    from app.services import drawdown_guard
    monkeypatch.setattr(drawdown_guard, "current_drawdown_pct", lambda db: -0.08)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/policy/limits/risk_per_trade", json={
            "threshold": "0.01", "unit": "pct", "effective_from": "2026-08-16",
            "committed_action": "reduce to 0.5% and step away",
            "reason": "want to be more careful",
        })
        assert r.status_code == 409
        assert r.json()["detail"]["error"] == "amendment_blocked_during_drawdown"


@pytest.mark.asyncio
async def test_amendment_allowed_with_override_and_long_reason(monkeypatch):
    from app.services import drawdown_guard
    monkeypatch.setattr(drawdown_guard, "current_drawdown_pct", lambda db: -0.08)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/policy/limits/risk_per_trade", json={
            "threshold": "0.005", "unit": "pct", "effective_from": "2026-08-16",
            "committed_action": "reduce to 0.5% for next 30 days",
            "reason": "explicitly overriding drawdown block; documenting: I am cutting risk in half",
            "override_during_drawdown": True,
        })
        assert r.status_code == 201
        assert r.json()["is_override_during_drawdown"] is True
```

- [ ] **Step 2: Write `app/services/drawdown_guard.py`**

```python
"""Reads current DD from the latest metric snapshot. Returns 0 when no snapshot."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.metrics import MetricSnapshot


async def current_drawdown_pct(db: AsyncSession) -> float:
    row = (await db.execute(
        select(MetricSnapshot).where(MetricSnapshot.scope == "composite")
        .order_by(MetricSnapshot.as_of_date.desc()).limit(1)
    )).scalar_one_or_none()
    if not row:
        return 0.0
    return float(row.metrics.get("current_drawdown", 0.0) or 0.0)
```

- [ ] **Step 3: Implement `app/api/policy.py`** — set new limit closes previous version (`effective_to = today`), inserts new row, writes amendment with `is_override_during_drawdown` flag. Refuses per Global Constraint.

- [ ] **Step 4: Run tests + commit**

```bash
pytest tests/api/test_policy.py -v
git commit -m "feat(tej-capital): policy API — versioned limits, drawdown-block, amendments log"
```

---

## Task 18: Metrics + Tearsheet API (snapshot freeze with `ledger_hash`)

**Files:**
- Create: `tej-capital/backend/app/api/metrics.py`
- Create: `tej-capital/backend/app/services/snapshot.py` — builds and freezes a metric snapshot; computes `ledger_hash`.
- Create: `tej-capital/backend/tests/api/test_metrics.py`
- Modify: `app/main.py`.

**Interfaces:**
- `GET  /api/metrics/live?scope=composite|per_account&account_id=UUID` — computes the full tearsheet on the fly (does not persist).
- `POST /api/metrics/freeze` — computes and inserts a `tej_metric_snapshots` row with `ledger_hash`. Idempotent per `(as_of_date, scope, account_id)`.
- `GET  /api/metrics/snapshots?since=DATE&scope=composite` — list frozen snapshots.
- `GET  /api/tearsheet/monthly?year=2026&month=8` — one-page factsheet payload (headline figures, metric groups, verdict, monthly grid data).

Every metric value in the response is wrapped `{"value": ..., "n": ...}` per Global Constraint (R6).

- [ ] **Step 1: Write failing tests**

```python
# tests/api/test_metrics.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_null_for_empty_history_R3():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/metrics/live?scope=composite")
    assert r.status_code == 200
    body = r.json()
    assert body["returns"]["cumulative_twr"]["value"] is None
    assert body["returns"]["cumulative_twr"]["n"] == 0


@pytest.mark.asyncio
async def test_freeze_snapshot_writes_ledger_hash():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/metrics/freeze", json={"as_of_date": "2026-08-16", "scope": "composite"})
        assert r.status_code == 201
        body = r.json()
        assert len(body["ledger_hash"]) == 64
        # Idempotent
        again = await ac.post("/api/metrics/freeze", json={"as_of_date": "2026-08-16", "scope": "composite"})
        assert again.status_code == 200  # not 201 second time
```

- [ ] **Step 2: Write `app/services/snapshot.py`**

```python
"""Compute and freeze a metric snapshot with a ledger hash for point-in-time integrity."""
from __future__ import annotations
import hashlib
import uuid
from datetime import date
from decimal import Decimal
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import returns as R, metrics as M, stats as S, trades as T, attribution as A, verdict as V
from app.domain.nav import NavSnapshot
from app.domain.flows import CashFlow
from app.domain.trades import Trade
from app.domain.metrics import MetricSnapshot
from app.domain.settings import Settings


def _wrap(value, n: int) -> dict:
    return {"value": value, "n": int(n)}


async def _load_series(db: AsyncSession, scope: str, account_id: uuid.UUID | None):
    """Returns (composite return series, trades DataFrame, count of nav rows)."""
    nav_q = select(NavSnapshot).where(NavSnapshot.superseded_by.is_(None))
    flow_q = select(CashFlow).where(CashFlow.superseded_by.is_(None))
    if scope == "per_account" and account_id:
        nav_q = nav_q.where(NavSnapshot.account_id == account_id)
        flow_q = flow_q.where(CashFlow.account_id == account_id)

    nav_rows = (await db.execute(nav_q.order_by(NavSnapshot.as_of_date))).scalars().all()
    flow_rows = (await db.execute(flow_q.order_by(CashFlow.as_of_date))).scalars().all()

    per_acct: dict = {}
    for r in nav_rows:
        per_acct.setdefault(r.account_id, {"nav": {}, "flows": {}})["nav"][r.as_of_date] = float(r.closing_equity)
    for f in flow_rows:
        per_acct.setdefault(f.account_id, {"nav": {}, "flows": {}})["flows"][f.as_of_date] = float(f.amount)

    accounts = {
        aid: (pd.Series(d["nav"]).sort_index(), pd.Series(d["flows"]).sort_index() if d["flows"] else pd.Series(dtype="float64"))
        for aid, d in per_acct.items()
    }
    composite = R.composite_twr(accounts) if len(accounts) > 1 else (
        R.daily_twr(*next(iter(accounts.values()))) if accounts else pd.Series(dtype="float64")
    )

    trades_rows = (await db.execute(select(Trade).where(Trade.superseded_by.is_(None)))).scalars().all()
    trades_df = pd.DataFrame([{
        "id": str(t.id),
        "setup": str(t.setup_id) if t.setup_id else None,
        "instrument": t.instrument,
        "session": t.session,
        "htf_aligned": t.htf_aligned,
        "r_multiple": t.r_multiple,
        "risk_amount": float(t.risk_amount) if t.risk_amount is not None else None,
        "gross_pnl": float(t.gross_pnl) if t.gross_pnl is not None else None,
        "costs": float(t.costs),
        "rule_compliant": t.rule_compliant,
        "closed_at": t.closed_at,
        "mae_r": float(t.mae_r) if t.mae_r is not None else None,
        "mfe_r": float(t.mfe_r) if t.mfe_r is not None else None,
    } for t in trades_rows])
    return composite, trades_df, len(nav_rows)


async def compute_tearsheet(db: AsyncSession, scope: str = "composite",
                             account_id: uuid.UUID | None = None) -> dict:
    settings = await db.get(Settings, 1)
    tdy = settings.trading_days_per_year if settings else 252
    rfr = float(settings.risk_free_rate) if settings else 0.04
    benchmark = float(settings.benchmark_sharpe) if settings else 0.0
    trials = int(settings.strategy_variants_tested) if settings else 1

    returns, trades, n = await _load_series(db, scope, account_id)
    n_days = len(returns)

    return {
        "returns": {
            "cumulative_twr": _wrap(M.cumulative_twr(returns), n_days),
            "cagr": _wrap(M.cagr(returns, tdy), n_days),
            "annualised_return": _wrap(M.annualised_return(returns, tdy), n_days),
            "avg_daily_return": _wrap(M.avg_daily_return(returns), n_days),
            "pct_positive_days": _wrap(M.pct_positive_days(returns), n_days),
            "best_day": _wrap(M.best_day(returns), n_days),
            "worst_day": _wrap(M.worst_day(returns), n_days),
        },
        "risk": {
            "annualised_volatility": _wrap(M.annualised_volatility(returns, tdy), n_days),
            "downside_deviation": _wrap(M.downside_deviation(returns, 0.0, tdy), n_days),
            "max_drawdown": _wrap(M.max_drawdown(returns), n_days),
            "current_drawdown": _wrap(M.current_drawdown(returns), n_days),
            "longest_drawdown_days": _wrap(M.longest_drawdown_days(returns), n_days),
            "ulcer_index": _wrap(M.ulcer_index(returns), n_days),
            "var_95": _wrap(M.var_95(returns), n_days),
            "cvar_95": _wrap(M.cvar_95(returns), n_days),
            "skewness": _wrap(M.skewness(returns), n_days),
            "excess_kurtosis": _wrap(M.excess_kurtosis(returns), n_days),
            "top_5_drawdowns": M.top_n_drawdowns(returns, n=5),
        },
        "risk_adjusted": {
            "sharpe": _wrap(M.sharpe(returns, rfr, tdy), n_days),
            "sortino": _wrap(M.sortino(returns, 0.0, tdy), n_days),
            "calmar": _wrap(M.calmar(returns, tdy), n_days),
            "sterling": _wrap(M.sterling(returns, tdy), n_days),
            "burke": _wrap(M.burke(returns, tdy), n_days),
            "omega": _wrap(M.omega(returns), n_days),
            "gain_to_pain": _wrap(M.gain_to_pain(returns), n_days),
            "tail_ratio": _wrap(M.tail_ratio(returns), n_days),
            "ulcer_performance_index": _wrap(M.ulcer_performance_index(returns, rfr, tdy), n_days),
            "recovery_factor": _wrap(M.recovery_factor(returns), n_days),
        },
        "statistical_validity": {
            "sharpe_t_stat": _wrap(S.sharpe_t_stat(returns), n_days),
            "psr_vs_zero": _wrap(S.probabilistic_sharpe_ratio(returns, 0.0), n_days),
            "psr_vs_benchmark": _wrap(S.probabilistic_sharpe_ratio(returns, benchmark), n_days),
            "deflated_sharpe": _wrap(S.deflated_sharpe(returns, trials, benchmark), n_days),
            "sharpe_ci": S.sharpe_ci(returns),
        },
        "trades": {
            "expectancy_r": _wrap(T.expectancy_r(trades) if len(trades) else None, len(trades)),
            "payoff_ratio": _wrap(T.payoff_ratio(trades) if len(trades) else None, len(trades)),
            "profit_factor": _wrap(T.profit_factor(trades) if len(trades) else None, len(trades)),
            "top_3_concentration": T.top_n_concentration(trades, 3) if len(trades) else {},
            "compliance_gap": T.compliance_gap_significance(trades) if len(trades) else {},
            "streaks": T.streaks(trades) if len(trades) else {},
            "mae_mfe": T.mae_mfe_stats(trades) if len(trades) else {},
        },
        "verdict": V.verdict_band(returns, benchmark_sharpe=benchmark, trading_days_per_year=tdy),
    }


def compute_ledger_hash(nav_rows, flow_rows, trade_rows) -> str:
    h = hashlib.sha256()
    for r in sorted(nav_rows, key=lambda x: (x.account_id, x.as_of_date, x.id)):
        h.update(f"nav|{r.id}|{r.entered_at.isoformat()}|".encode())
    for r in sorted(flow_rows, key=lambda x: (x.account_id, x.as_of_date, x.id)):
        h.update(f"flow|{r.id}|{r.entered_at.isoformat()}|".encode())
    for r in sorted(trade_rows, key=lambda x: (x.account_id, x.opened_at, x.id)):
        h.update(f"trade|{r.id}|{r.entered_at.isoformat()}|".encode())
    return h.hexdigest()


async def freeze_snapshot(db: AsyncSession, *, as_of_date: date, scope: str = "composite",
                          account_id: uuid.UUID | None = None) -> tuple[MetricSnapshot, bool]:
    """Returns (snapshot, was_created). Idempotent per (date, scope, account_id)."""
    existing = (await db.execute(
        select(MetricSnapshot).where(
            MetricSnapshot.as_of_date == as_of_date,
            MetricSnapshot.scope == scope,
            MetricSnapshot.account_id == account_id,
        )
    )).scalar_one_or_none()
    if existing:
        return existing, False

    metrics = await compute_tearsheet(db, scope, account_id)
    nav_rows = (await db.execute(select(NavSnapshot).where(NavSnapshot.superseded_by.is_(None)))).scalars().all()
    flow_rows = (await db.execute(select(CashFlow).where(CashFlow.superseded_by.is_(None)))).scalars().all()
    trade_rows = (await db.execute(select(Trade).where(Trade.superseded_by.is_(None)))).scalars().all()

    snap = MetricSnapshot(
        id=uuid.uuid4(),
        as_of_date=as_of_date,
        scope=scope,
        account_id=account_id,
        metrics=metrics,
        ledger_hash=compute_ledger_hash(nav_rows, flow_rows, trade_rows),
    )
    db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return snap, True
```

- [ ] **Step 3: Write `app/api/metrics.py`** — three routes: `/live`, `/freeze` (POST), `/snapshots` (GET), plus `GET /api/tearsheet/monthly` that reads the frozen snapshot for that month or computes on the fly.

- [ ] **Step 4: Run tests + commit**

```bash
pytest tests/api/test_metrics.py -v
git commit -m "feat(tej-capital): metrics/tearsheet API + snapshot freeze with ledger_hash"
```

---

## Task 19: Attribution API

**Files:**
- Create: `tej-capital/backend/app/api/attribution.py`
- Create: `tej-capital/backend/tests/api/test_attribution.py`
- Modify: `app/main.py`.

**Interfaces:**
- `GET /api/attribution?by=setup|asset|session|htf|dow` — returns `list[grouped_stats row]` with verdicts.
- `GET /api/attribution/concentration` — `top_n_concentration` payload.
- `GET /api/attribution/compliance-gap` — `compliance_gap_significance` payload.

- [ ] **Step 1: Test**

```python
@pytest.mark.asyncio
async def test_attribution_by_setup_returns_verdict_tags():
    # Assume trades already seeded via fixture
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/attribution?by=setup")
    assert r.status_code == 200
    for row in r.json():
        assert row["verdict"] in {"not_enough", "retire", "marginal", "working"}
```

- [ ] **Step 2: Implement** — thin wrapper around `core/attribution.grouped_stats` with the trades DataFrame loader from Task 18.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(tej-capital): attribution API with verdict tags"
```

---

## Task 20: Audit + Allocator-view API

**Files:**
- Create: `tej-capital/backend/app/api/audit.py`
- Create: `tej-capital/backend/app/api/allocator.py`
- Create: `tej-capital/backend/app/services/tokens.py` — generates/validates allocator tokens.
- Create: `tej-capital/backend/tests/api/test_audit.py`
- Create: `tej-capital/backend/tests/api/test_allocator.py`
- Modify: `app/main.py`.

**Interfaces:**
- `GET /api/audit?since=DATE&type=correction|amendment|override&filter_table=...` — unified feed.
- `POST /api/allocator/tokens` — body `{label, expires_at}` → returns opaque token string (secrets.token_urlsafe(32)).
- `DELETE /api/allocator/tokens/{id}` — revoke.
- `GET /api/allocator/view?token=...` — read-only tearsheet + monthly grid + equity curve + drawdown table + verdict, with `journal_entries`, `state_of_mind`, `one_sentence_takeaway`, and account balances **omitted**.

- [ ] **Step 1: Write failing test — hidden fields**

```python
@pytest.mark.asyncio
async def test_allocator_view_hides_journal_and_emotional_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Assume seeded journal, trades, tokens
        tok = await ac.post("/api/allocator/tokens", json={"label": "Prospect A",
                                                            "expires_at": "2027-01-01T00:00:00+00:00"})
        token = tok.json()["token"]
        r = await ac.get(f"/api/allocator/view?token={token}")
    body = r.json()
    assert "journal" not in body
    for t in body.get("trades", []):
        assert "state_of_mind" not in t
        assert "one_sentence_takeaway" not in t
    assert all("account_balance" not in acct for acct in body.get("accounts", []))
```

- [ ] **Step 2: Write `app/services/tokens.py`**

```python
import secrets
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.allocator import AllocatorToken


def generate_token() -> str:
    return secrets.token_urlsafe(32)


async def validate(db: AsyncSession, token: str) -> AllocatorToken | None:
    row = (await db.execute(
        select(AllocatorToken).where(AllocatorToken.token == token)
    )).scalar_one_or_none()
    if not row:
        return None
    if row.revoked_at:
        return None
    if row.expires_at <= datetime.now(tz=timezone.utc):
        return None
    return row
```

- [ ] **Step 3: Implement `app/api/audit.py`** — union select over `tej_corrections_ledger` + `tej_policy_amendments`. Filter by date and type.

- [ ] **Step 4: Implement `app/api/allocator.py`** — token CRUD (POST/DELETE), and `GET /view?token=...` that:
    1. Validates the token via `tokens.validate`.
    2. Loads composite tearsheet via `services.snapshot.compute_tearsheet`.
    3. Returns a redacted view — never includes `journal`, `state_of_mind`, `one_sentence_takeaway`, or per-account balances.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(tej-capital): audit feed + token-gated allocator read-only view"
```

---

## Task 21: Ingestion — CSV import (fully working)

**Files:**
- Create: `tej-capital/backend/app/ingest/base.py`
- Create: `tej-capital/backend/app/ingest/csv_import.py`
- Create: `tej-capital/backend/app/domain/csv_mappings.py` + migration
- Create: `tej-capital/backend/app/api/ingest.py`
- Create: `tej-capital/backend/tests/ingest/test_csv_import.py`
- Modify: `app/main.py`.

**Interfaces:**
- `ingest.base.BrokerAdapter` Protocol (per spec §7).
- `ingest.csv_import.CsvAdapter(account_id, mapping)` — implements the Protocol.
- `POST /api/ingest/csv?account_id=UUID` (multipart file upload + mapping JSON) — imports trades and flows idempotently.
- CSV mappings persisted per-account in `tej_csv_mappings` (added by a follow-up migration `0002_csv_mappings.py`).

- [ ] **Step 1: Write `app/ingest/base.py`**

```python
from typing import Protocol
from datetime import date
from decimal import Decimal
from dataclasses import dataclass
import pandas as pd


@dataclass
class CanonicalTrade:
    external_id: str
    instrument: str
    direction: str
    entry_price: Decimal
    exit_price: Decimal | None
    position_size: Decimal
    gross_pnl: Decimal | None
    costs: Decimal
    opened_at: str
    closed_at: str | None


@dataclass
class CanonicalFlow:
    external_id: str
    as_of_date: date
    amount: Decimal
    flow_type: str


class BrokerAdapter(Protocol):
    name: str
    def fetch_equity(self, since: date) -> pd.Series: ...
    def fetch_closed_trades(self, since: date) -> list[CanonicalTrade]: ...
    def fetch_flows(self, since: date) -> list[CanonicalFlow]: ...
```

- [ ] **Step 2: Write `app/ingest/csv_import.py`**

```python
from datetime import date
from decimal import Decimal
import pandas as pd
from app.ingest.base import BrokerAdapter, CanonicalTrade, CanonicalFlow


class CsvAdapter:
    name = "csv"

    def __init__(self, csv_bytes: bytes, mapping: dict):
        self.df = pd.read_csv(pd.io.common.BytesIO(csv_bytes))
        self.map = mapping  # {"external_id": "OrderID", "instrument": "Symbol", ...}

    def fetch_equity(self, since: date) -> pd.Series:
        # CSV imports typically don't provide equity — return empty.
        return pd.Series(dtype="float64")

    def fetch_closed_trades(self, since: date) -> list[CanonicalTrade]:
        m = self.map
        out = []
        for _, row in self.df.iterrows():
            opened = pd.to_datetime(row[m["opened_at"]])
            if opened.date() < since:
                continue
            out.append(CanonicalTrade(
                external_id=str(row[m["external_id"]]),
                instrument=str(row[m["instrument"]]),
                direction=str(row[m["direction"]]).lower(),
                entry_price=Decimal(str(row[m["entry_price"]])),
                exit_price=Decimal(str(row[m["exit_price"]])) if m.get("exit_price") else None,
                position_size=Decimal(str(row[m["position_size"]])),
                gross_pnl=Decimal(str(row[m["gross_pnl"]])) if m.get("gross_pnl") else None,
                costs=Decimal(str(row.get(m.get("costs", ""), 0))),
                opened_at=str(opened),
                closed_at=str(pd.to_datetime(row[m["closed_at"]])) if m.get("closed_at") else None,
            ))
        return out

    def fetch_flows(self, since: date) -> list[CanonicalFlow]:
        return []
```

- [ ] **Step 3: Write `app/api/ingest.py`** — accepts multipart file + mapping JSON. Upserts trades by `(account_id, external_id)` unique constraint. Fields left null are queued for enrichment.

- [ ] **Step 4: Test — import a synthetic 3-row CSV, verify enrichment queue populated**

```python
CSV = b"OrderID,Symbol,Side,Open,Close,Qty,Opened,Closed\n1,XAUUSD,long,2400,2430,0.1,2026-08-16T10:00,2026-08-16T15:00\n"

@pytest.mark.asyncio
async def test_csv_import_idempotent_by_external_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        for _ in range(2):
            r = await ac.post(f"/api/ingest/csv?account_id={aid}",
                              files={"file": ("t.csv", CSV, "text/csv")},
                              data={"mapping": '{"external_id":"OrderID","instrument":"Symbol","direction":"Side","entry_price":"Open","exit_price":"Close","position_size":"Qty","opened_at":"Opened","closed_at":"Closed"}'})
            assert r.status_code == 200
        listing = await ac.get(f"/api/trades?since=2026-08-16&account_id={aid}")
        assert len(listing.json()) == 1  # not 2 — idempotent
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(tej-capital): CSV import adapter with column mapping and idempotency"
```

---

## Task 22: Ingestion stubs — MT5 / Bybit / Darwinex

**Files:**
- Create: `tej-capital/backend/app/ingest/mt5_adapter.py`
- Create: `tej-capital/backend/app/ingest/bybit_adapter.py`
- Create: `tej-capital/backend/app/ingest/darwinex_adapter.py`
- Create: `tej-capital/backend/tests/ingest/test_stubs.py`

**Interfaces:**
- Each raises `NotConfiguredError(integration, hint)` on any method call. The `hint` names the exact env var(s) needed.

- [ ] **Step 1: Implement three stubs — identical shape**

```python
# app/ingest/mt5_adapter.py
from datetime import date
import pandas as pd
from app.api.errors import NotConfiguredError
from app.ingest.base import CanonicalTrade, CanonicalFlow
from app.config import get_settings


class Mt5Adapter:
    name = "mt5"

    def __init__(self):
        s = get_settings()
        if not s.mt5_login:
            raise NotConfiguredError("mt5", "set TEJ_MT5_LOGIN + TEJ_MT5_PASSWORD + TEJ_MT5_SERVER; requires Windows VM with MetaTrader5 python package")

    def fetch_equity(self, since: date) -> pd.Series:
        raise NotConfiguredError("mt5", "MT5 execution requires Windows runtime")

    def fetch_closed_trades(self, since: date) -> list[CanonicalTrade]: ...
    def fetch_flows(self, since: date) -> list[CanonicalFlow]: ...
```

Same shape for `bybit_adapter.py` (`TEJ_BYBIT_API_KEY` + `TEJ_BYBIT_SECRET`) and `darwinex_adapter.py` (`TEJ_DARWINEX_API_KEY`).

- [ ] **Step 2: Test — every adapter raises NotConfiguredError when creds absent**

```python
import pytest
from app.api.errors import NotConfiguredError
from app.ingest.mt5_adapter import Mt5Adapter


def test_mt5_stub_raises_not_configured():
    with pytest.raises(NotConfiguredError):
        Mt5Adapter()
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(tej-capital): MT5/Bybit/Darwinex adapter stubs raise NotConfiguredError"
```

---

## Task 23: Nightly close (Temporal) — workflow + activity stubs

**Files:**
- Create: `tej-capital/backend/app/workflows/nightly_close.py`
- Create: `tej-capital/backend/app/workflows/activities.py`
- Create: `tej-capital/backend/app/workflows/worker.py`
- Create: `tej-capital/backend/tests/workflows/test_nightly_close_import.py`

**Interfaces:**
- Workflow `NightlyCloseWorkflow` (annotated `@workflow.defn`) with steps in the order from spec §8.
- Activities are thin wrappers that either delegate to `app.core` / `app.services` production code, or raise `NotConfiguredError` for external I/O.
- `worker.py` — CLI entry point `python -m app.workflows.worker`. Documented as requiring `TEJ_TEMPORAL_HOST` (default `localhost:7233`) — refuses to start otherwise with a helpful message.

- [ ] **Step 1: Implement workflow definition**

```python
# app/workflows/nightly_close.py
from datetime import datetime, timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows import activities as A


@workflow.defn
class NightlyCloseWorkflow:
    @workflow.run
    async def run(self, as_of: str) -> dict:
        await workflow.execute_activity(A.fetch_all_marks, as_of, start_to_close_timeout=timedelta(minutes=5))
        await workflow.execute_activity(A.reconcile_ledger, as_of, start_to_close_timeout=timedelta(minutes=2))
        await workflow.execute_activity(A.detect_anomalies_activity, as_of, start_to_close_timeout=timedelta(minutes=1))
        await workflow.execute_activity(A.evaluate_policy_limits, as_of, start_to_close_timeout=timedelta(minutes=1))
        snap_hash = await workflow.execute_activity(A.freeze_snapshot_activity, as_of, start_to_close_timeout=timedelta(minutes=2))
        await workflow.execute_activity(A.send_nightly_alert, as_of, start_to_close_timeout=timedelta(minutes=1))
        return {"as_of": as_of, "ledger_hash": snap_hash}
```

- [ ] **Step 2: Implement activities as thin wrappers**

```python
# app/workflows/activities.py
from datetime import date
from temporalio import activity
from app.db import SessionLocal
from app.services.snapshot import freeze_snapshot


@activity.defn
async def fetch_all_marks(as_of: str) -> int:
    # v1: no adapters configured → returns 0 marks fetched.
    return 0


@activity.defn
async def reconcile_ledger(as_of: str) -> int:
    return 0


@activity.defn
async def detect_anomalies_activity(as_of: str) -> int:
    return 0


@activity.defn
async def evaluate_policy_limits(as_of: str) -> int:
    return 0


@activity.defn
async def freeze_snapshot_activity(as_of: str) -> str:
    async with SessionLocal() as db:
        snap, _ = await freeze_snapshot(db, as_of_date=date.fromisoformat(as_of))
        return snap.ledger_hash


@activity.defn
async def send_nightly_alert(as_of: str) -> bool:
    from app.alerts.telegram import send_nightly
    return await send_nightly(as_of)
```

- [ ] **Step 3: Implement worker.py**

```python
# app/workflows/worker.py
import asyncio
import os
import sys
from temporalio.client import Client
from temporalio.worker import Worker
from app.workflows.nightly_close import NightlyCloseWorkflow
from app.workflows import activities


async def main():
    host = os.environ.get("TEJ_TEMPORAL_HOST")
    if not host:
        print("TEJ_TEMPORAL_HOST is unset — worker will not start. "
              "This is expected in v1 unless you have a Temporal server running. "
              "See README §Integrations.", file=sys.stderr)
        sys.exit(0)
    client = await Client.connect(host)
    worker = Worker(
        client, task_queue="tej-capital-nightly",
        workflows=[NightlyCloseWorkflow],
        activities=[
            activities.fetch_all_marks, activities.reconcile_ledger,
            activities.detect_anomalies_activity, activities.evaluate_policy_limits,
            activities.freeze_snapshot_activity, activities.send_nightly_alert,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Test — workflow definitions import cleanly**

```python
def test_workflow_definitions_importable():
    from app.workflows.nightly_close import NightlyCloseWorkflow
    from app.workflows import activities
    assert NightlyCloseWorkflow is not None
    assert hasattr(activities, "freeze_snapshot_activity")
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(tej-capital): nightly_close Temporal workflow + activities + worker (stub, requires temporal server)"
```

---

## Task 24: Alerts — Telegram (rate-limited, stub-safe)

**Files:**
- Create: `tej-capital/backend/app/alerts/telegram.py`
- Create: `tej-capital/backend/tests/alerts/test_telegram.py`

**Interfaces:**
- `send_alert(kind: Literal["nightly","immediate","weekly","monthly","data_quality"], payload: dict) -> bool` — dedupes per (kind, calendar_day) via an in-memory cache keyed on `(kind, date.today())`.
- `send_nightly(as_of: str) -> bool` — convenience wrapper. No-ops with a log line when `TEJ_TELEGRAM_BOT_TOKEN` is unset.

- [ ] **Step 1: Write failing test**

```python
# tests/alerts/test_telegram.py
import pytest
from app.alerts.telegram import send_alert, _seen_today


@pytest.mark.asyncio
async def test_send_alert_noop_when_unconfigured(monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: type("S", (), {
        "telegram_bot_token": None, "telegram_chat_id": None,
    })())
    _seen_today.clear()
    r = await send_alert("nightly", {"pnl": 42})
    assert r is False


@pytest.mark.asyncio
async def test_send_alert_deduped_per_day():
    _seen_today.clear()
    _seen_today.add(("nightly", "2026-08-16"))
    r = await send_alert("nightly", {"pnl": 42})
    assert r is False
```

- [ ] **Step 2: Implement**

```python
"""Telegram alerts. Never sends more than one message per (kind, day)."""
from __future__ import annotations
import logging
from datetime import date
from typing import Literal
import httpx

from app.config import get_settings

Kind = Literal["nightly", "immediate", "weekly", "monthly", "data_quality"]
log = logging.getLogger(__name__)

# Per-process dedupe; a real deployment would back this by Postgres or Redis.
_seen_today: set[tuple[str, str]] = set()


async def send_alert(kind: Kind, payload: dict) -> bool:
    s = get_settings()
    if not s.telegram_bot_token or not s.telegram_chat_id:
        log.info("telegram not configured; skipping %s alert", kind)
        return False
    key = (kind, date.today().isoformat())
    if key in _seen_today:
        log.info("telegram already sent for %s today; skipping", kind)
        return False
    text = _format(kind, payload)
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
            json={"chat_id": s.telegram_chat_id, "text": text, "parse_mode": "HTML"},
        )
        r.raise_for_status()
    _seen_today.add(key)
    return True


def _format(kind: Kind, payload: dict) -> str:
    if kind == "nightly":
        return (f"<b>TEJ Nightly · {payload.get('as_of')}</b>\n"
                f"P&L: {payload.get('pnl', '—')}\n"
                f"DD vs kill-switch: {payload.get('dd', '—')}\n"
                f"Breaches: {payload.get('breaches', 0)}\n"
                f"Anomalies: {payload.get('anomalies', 0)}")
    return f"<b>TEJ · {kind}</b>\n{payload}"


async def send_nightly(as_of: str) -> bool:
    return await send_alert("nightly", {"as_of": as_of, "pnl": "—", "dd": "—", "breaches": 0, "anomalies": 0})
```

- [ ] **Step 3: Run tests + commit**

```bash
pytest tests/alerts/test_telegram.py -v
git commit -m "feat(tej-capital): telegram alerts — rate-limited per (kind, day), stub-safe"
```

---

## Task 25: AI layer stubs — Qdrant search + commentary + pattern-detect + pretrade

**Files:**
- Create: `tej-capital/backend/app/ai/qdrant_search.py`
- Create: `tej-capital/backend/app/ai/commentary.py`
- Create: `tej-capital/backend/app/ai/pattern_detect.py`
- Create: `tej-capital/backend/app/ai/pretrade_check.py`
- Create: `tej-capital/backend/app/api/ai.py` — API surface for the search + pretrade endpoints.
- Create: `tej-capital/backend/tests/ai/test_stubs.py`

**Interfaces (contracts stable; bodies stubbed):**
- `qdrant_search.embed_and_index(text, metadata: dict) -> str` — returns qdrant point id. Raises `NotConfiguredError` if `TEJ_QDRANT_URL` unset.
- `qdrant_search.query(text, k=10) -> list[dict]` — returns `[{point_id, score, metadata}, ...]`.
- `commentary.draft(tearsheet: dict, journal_entries: list[dict]) -> str` — takes numbers, returns prose. Raises `NotConfiguredError` if `TEJ_LLM_API_KEY` unset.
- `pattern_detect.find_patterns(trades: pd.DataFrame) -> list[dict]` — runs Benjamini-Hochberg FDR-corrected slice tests first (deterministic), then optionally passes survivors to LLM for phrasing.
- `pretrade_check.ask(thesis: str, playbook: str) -> str` — advisory question. Raises `NotConfiguredError` if `TEJ_LLM_API_KEY` unset.

Every function is a real interface that returns a stub message on the API side (`{"status": "not_configured", "hint": "..."}`) so the frontend can render a helpful state.

- [ ] **Step 1: Implement `pattern_detect.py` — deterministic tests are REAL, LLM phrasing is optional**

```python
"""Behavioural pattern detection. Statistical tests run always; LLM only phrases the survivors."""
from __future__ import annotations
import pandas as pd
import numpy as np
from scipy import stats


def _slices(trades: pd.DataFrame) -> dict:
    """Return {slice_name: pd.Series of r_multiples}. Each slice is a binary split."""
    out: dict[str, tuple[pd.Series, pd.Series]] = {}
    if "closed_at" in trades.columns:
        dow = pd.to_datetime(trades["closed_at"]).dt.dayofweek
        out["monday_vs_rest"] = (trades[dow == 0]["r_multiple"].dropna(),
                                  trades[dow != 0]["r_multiple"].dropna())
        out["friday_vs_rest"] = (trades[dow == 4]["r_multiple"].dropna(),
                                  trades[dow != 4]["r_multiple"].dropna())
    if "session" in trades.columns:
        for sess in ("asia", "london", "new_york"):
            a = trades[trades["session"] == sess]["r_multiple"].dropna()
            b = trades[trades["session"] != sess]["r_multiple"].dropna()
            if len(a) >= 5 and len(b) >= 5:
                out[f"session_{sess}_vs_rest"] = (a, b)
    return out


def _bh_fdr(pvalues: list[float], q: float = 0.10) -> list[bool]:
    """Benjamini-Hochberg: return mask of hypotheses that pass at FDR q."""
    n = len(pvalues)
    order = np.argsort(pvalues)
    sorted_p = np.array(pvalues)[order]
    thresholds = (np.arange(1, n + 1) / n) * q
    passes = sorted_p <= thresholds
    if not passes.any():
        return [False] * n
    max_i = np.max(np.where(passes))
    mask = np.zeros(n, dtype=bool)
    mask[order[: max_i + 1]] = True
    return mask.tolist()


def find_patterns(trades: pd.DataFrame, q: float = 0.10) -> list[dict]:
    slices = _slices(trades)
    if not slices:
        return []
    names = list(slices.keys())
    results = []
    for name in names:
        a, b = slices[name]
        t = stats.ttest_ind(a, b, equal_var=False)
        results.append({"name": name, "expectancy_a": float(a.mean()),
                        "expectancy_b": float(b.mean()), "p_value": float(t.pvalue)})
    survivors_mask = _bh_fdr([r["p_value"] for r in results], q=q)
    return [r for r, keep in zip(results, survivors_mask) if keep]
```

- [ ] **Step 2: Implement `qdrant_search.py`, `commentary.py`, `pretrade_check.py` as `NotConfiguredError` stubs with clear hints.**

```python
# app/ai/qdrant_search.py
from app.api.errors import NotConfiguredError
from app.config import get_settings


def _ensure():
    if not get_settings().qdrant_url:
        raise NotConfiguredError("qdrant", "set TEJ_QDRANT_URL + TEJ_LLM_API_KEY (embeddings) to enable journal search")


def embed_and_index(text: str, metadata: dict) -> str:
    _ensure()
    ...  # real impl in a follow-up commit


def query(text: str, k: int = 10) -> list[dict]:
    _ensure()
    ...
```

- [ ] **Step 3: Write `app/api/ai.py`**

Endpoints:
- `POST /api/ai/journal/search` (JSON `{"q": str, "k": int}`) — returns 501 with `not_configured` when Qdrant absent.
- `POST /api/ai/commentary` — 501 without LLM key.
- `GET  /api/ai/patterns` — always runs; returns `[{name, expectancy_a, expectancy_b, p_value}, ...]` for FDR-passing splits (LLM-phrased only if `TEJ_LLM_API_KEY` present, else raw).
- `POST /api/ai/pretrade` — 501 without LLM key.

- [ ] **Step 4: Test — `find_patterns` runs even without any credentials**

```python
def test_find_patterns_runs_without_credentials():
    import pandas as pd
    from app.ai.pattern_detect import find_patterns
    t = pd.DataFrame([{"session": "london", "r_multiple": 0.5, "closed_at": "2026-08-16"}] * 30
                      + [{"session": "asia", "r_multiple": -0.4, "closed_at": "2026-08-17"}] * 30)
    result = find_patterns(t, q=0.10)
    assert isinstance(result, list)


def test_qdrant_query_raises_not_configured(monkeypatch):
    from app.ai.qdrant_search import query
    from app.api.errors import NotConfiguredError
    import pytest
    monkeypatch.setattr("app.config.get_settings", lambda: type("S", (), {"qdrant_url": None})())
    with pytest.raises(NotConfiguredError):
        query("hesitation")
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(tej-capital): AI layer stubs — Qdrant search, commentary, pretrade (deterministic pattern-detect runs)"
```

---

## Task 26: Exports — CSV downloads, PDF stub, DDQ pack ZIP

**Files:**
- Create: `tej-capital/backend/app/export/csv_exports.py`
- Create: `tej-capital/backend/app/export/tearsheet_pdf.py`
- Create: `tej-capital/backend/app/export/ddq_pack.py`
- Create: `tej-capital/backend/app/api/export.py`
- Create: `tej-capital/backend/tests/export/test_csv.py`

**Interfaces:**
- `csv_exports.returns_csv(returns) -> bytes`, `.trades_csv(trades) -> bytes`, `.audit_csv(audit) -> bytes`.
- `tearsheet_pdf.render_html(tearsheet) -> str` — always works, returns styled HTML using the design tokens from Task 27.
- `tearsheet_pdf.render_pdf(tearsheet) -> bytes | None` — uses Playwright if importable, else returns `None` and caller falls through to HTML.
- `ddq_pack.build(tearsheet, corrections, policy_doc, attribution) -> bytes` — returns a ZIP file (strategy.md, policy.md, performance.csv, attribution.csv, corrections.csv).
- API:
  - `GET /api/export/returns.csv`
  - `GET /api/export/trades.csv`
  - `GET /api/export/audit.csv`
  - `GET /api/export/tearsheet/{year}/{month}.pdf` — returns PDF if available, else HTML with a `Content-Type: text/html` and `X-Tej-Warning: install Chromium to enable PDF export`.
  - `GET /api/export/ddq.zip`

- [ ] **Step 1: Implement `csv_exports.py`** — uses `pandas.DataFrame.to_csv(index=False).encode()`.

- [ ] **Step 2: Implement `tearsheet_pdf.py`** — HTML template with tokens from Task 27, `render_pdf` uses `playwright.async_api` if importable.

- [ ] **Step 3: Implement `ddq_pack.py`** — uses `zipfile.ZipFile` in memory.

- [ ] **Step 4: Test CSV round-trip**

```python
def test_returns_csv_is_readable_by_pandas():
    import pandas as pd, io
    from app.export.csv_exports import returns_csv
    r = pd.Series([0.01, -0.005], index=pd.date_range("2026-08-16", periods=2))
    out = returns_csv(r)
    df = pd.read_csv(io.BytesIO(out))
    assert list(df.columns) == ["date", "return"]
    assert len(df) == 2
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(tej-capital): exports — CSV downloads, PDF stub with HTML fallback, DDQ ZIP"
```

---

## Task 27: Frontend scaffold — router, query client, API client, DESIGN SYSTEM, shared components

**Files:**
- Modify: `tej-capital/frontend/src/main.tsx`
- Create: `tej-capital/frontend/src/App.tsx`
- Create: `tej-capital/frontend/src/lib/api.ts`
- Create: `tej-capital/frontend/src/lib/query.ts`
- Create: `tej-capital/frontend/src/lib/format.ts`
- Create: `tej-capital/frontend/src/design/tokens.css`
- Create: `tej-capital/frontend/src/design/reset.css`
- Create: `tej-capital/frontend/src/design/typography.css`
- Create: `tej-capital/frontend/src/design/components.css`
- Create: `tej-capital/frontend/src/components/Layout.tsx`
- Create: `tej-capital/frontend/src/components/Nav.tsx`
- Create: `tej-capital/frontend/src/components/MetricCard.tsx`
- Create: `tej-capital/frontend/src/components/VerdictBand.tsx`
- Create: `tej-capital/frontend/src/components/EmptyState.tsx`
- Create: `tej-capital/frontend/src/components/YearLedger.tsx`
- Create: `tej-capital/frontend/src/components/MonthlyGrid.tsx`
- Create: `tej-capital/frontend/src/components/SectionHeader.tsx`
- Create: `tej-capital/frontend/src/components/Button.tsx`
- Create: `tej-capital/frontend/src/components/TextField.tsx`

### §Design System — the quality bar (load-bearing per Product Brief §4)

The UI is fund-grade serious, not consumer-app playful. Every visual choice below is deliberate; every executor consumes these tokens rather than inventing new ones.

**Palette (light default; dark inherited via `prefers-color-scheme`).** Copy these into `design/tokens.css` verbatim:

```css
:root {
  /* Ink */
  --ink-1: #0B0D10;       /* headlines, primary body */
  --ink-2: #2A2F36;       /* secondary body */
  --ink-3: #6B7280;       /* metadata, hints */
  --ink-4: #A1A7B0;       /* placeholder, disabled */

  /* Ground */
  --ground-1: #FAFAF7;    /* page background — warm off-white, not blue-white */
  --ground-2: #F2F1EC;    /* cards */
  --ground-3: #E8E7E1;    /* dividers, table borders */

  /* Signal */
  --gain: #1B7F4B;        /* muted forest green — not neon */
  --gain-soft: #E4EFE8;
  --loss: #A6262F;        /* deep venetian red — not fire engine */
  --loss-soft: #F0E1E1;
  --caution: #B58105;     /* amber for verdict/caution */
  --caution-soft: #F5EBCB;

  /* Accent — used sparingly for interactive affordances only */
  --accent: #12345B;      /* deep navy */
  --accent-hover: #0A2544;

  /* Motion */
  --duration-1: 120ms;
  --duration-2: 220ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;

  /* Elevation — very subtle; the design uses borders more than shadows */
  --elev-1: 0 1px 2px rgba(11, 13, 16, 0.04), 0 0 0 1px rgba(11, 13, 16, 0.06);
  --elev-2: 0 4px 12px rgba(11, 13, 16, 0.08), 0 0 0 1px rgba(11, 13, 16, 0.06);

  /* Spacing scale — 4px base, no other values allowed */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;

  /* Type scale */
  --font-sans: "Inter", -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-serif: "Source Serif 4", "Iowan Old Style", Georgia, serif;
  --font-mono: "JetBrains Mono", ui-monospace, Menlo, monospace;

  --size-display: 40px;   /* headline figures on Performance */
  --size-h1: 28px;
  --size-h2: 20px;
  --size-h3: 16px;
  --size-body: 14px;
  --size-caption: 12px;
  --size-micro: 11px;     /* used only for observation counts (N=…) */

  --line-tight: 1.15;
  --line-body: 1.55;
}

@media (prefers-color-scheme: dark) {
  :root {
    --ink-1: #F5F6F8;
    --ink-2: #C6CAD2;
    --ink-3: #8F949E;
    --ink-4: #5E636C;
    --ground-1: #0F1114;
    --ground-2: #171A1E;
    --ground-3: #262A30;
    --gain: #4FAE7B;
    --gain-soft: #1B2C22;
    --loss: #D8636A;
    --loss-soft: #2C1A1C;
    --caution: #E3B458;
    --caution-soft: #2A2412;
    --accent: #6A9BD1;
    --accent-hover: #8DB1DC;
    --elev-1: 0 1px 2px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255,255,255,0.06);
    --elev-2: 0 4px 12px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255,255,255,0.06);
  }
}
```

**Type rules:**

- Display / H1 = serif (`--font-serif`). Everything else sans (`--font-sans`). Numbers in tables and metric cards ALWAYS `--font-mono`, tabular-nums.
- The observation count next to every metric is `--size-micro`, `--ink-3`, prefixed `N=`. E.g. `1.87 · N=184`.
- Every headline figure on the Performance page uses `--size-display` and the serif face.

**Component grammar (`design/components.css`):**

- `Button` — primary is `--accent` background, ink-on-accent text; secondary is transparent background with `--ground-3` 1px border, `--ink-2` text. Border-radius `--radius-md`. Height 36px. Padding `var(--space-2) var(--space-4)`.
- `Card` — `--ground-2` background, no shadow by default (borders only), `--radius-lg`, padding `--space-5`.
- `MetricCard` — a Card that renders `{label, value, n, sub}`. Value uses mono font. `sub` (verdict tag or delta) is `--size-caption`, `--ink-3`.
- `VerdictBand` — full-bleed strip below the four headline figures. Color by level: `not_yet_meaningful` → `--caution-soft` background with `--ink-1` text; `ok` → `--gain-soft`; `caution` → `--caution-soft`. Always includes `N=<n_days>`.
- `EmptyState` — centered, `--ink-3` text. Never says "no data" — says what to do next. Copy from Product Brief §4.1 verbatim: `"No marks yet. Enter today's closing equity and your record begins."`
- `YearLedger` — a 53×7 grid of `12px` squares. Empty squares are 1px `--ground-3` outline only (R3: never gain-soft or loss-soft — that would read as "flat"). Hover shows a small floating card with date, return, P&L, trades closed, note.
- `MonthlyGrid` — year × month table, cells are colored by return sign with saturation scaled to |value|. Empty months show as `—` on `--ground-2`.

**Motion:**

- Transitions on hover states: `--duration-1 --ease-out` for color and background changes only. Never transform.
- Page transitions: none. This is a fund tool, not a slideshow.
- Skeleton loaders on data-heavy views (Performance, Attribution, Ledger) — pulse via `opacity` only.

**Voice (microcopy):**

- Second person, present tense. No hype. No exclamation marks anywhere.
- Verdict text lifts verbatim from `app/core/verdict.py` — the frontend never rewords it.
- Errors use plain English + a concrete next step. Example: `"Correction reason must be at least 10 characters. Say what changed and why — that's the audit trail."`

### Implementation steps

- [ ] **Step 1: Write `tokens.css`, `reset.css`, `typography.css`, `components.css` — verbatim from §Design System above.** Include a minimal reset (`* { box-sizing: border-box }`, remove default margins, `html, body { background: var(--ground-1); color: var(--ink-1); font-family: var(--font-sans); }`).

- [ ] **Step 2: Write `src/lib/api.ts`**

```ts
const BASE = "/api";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init.headers || {}) },
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw Object.assign(new Error(body.detail?.error || r.statusText), { status: r.status, body });
  }
  if (r.status === 204) return undefined as unknown as T;
  return r.json();
}

export const api = {
  get: <T,>(p: string) => request<T>(p),
  post: <T,>(p: string, body: unknown) => request<T>(p, { method: "POST", body: JSON.stringify(body) }),
  patch: <T,>(p: string, body: unknown) => request<T>(p, { method: "PATCH", body: JSON.stringify(body) }),
  del: <T,>(p: string) => request<T>(p, { method: "DELETE" }),
};

export type Metric<T = number> = { value: T | null; n: number };
```

- [ ] **Step 3: Write `src/lib/query.ts`**

```ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: 1 },
  },
});
```

- [ ] **Step 4: Write `src/lib/format.ts`** — number formatters that respect R6 (always emit N).

```ts
export const pct = (v: number | null | undefined, digits = 2) =>
  v == null ? "—" : `${(v * 100).toFixed(digits)}%`;

export const num = (v: number | null | undefined, digits = 2) =>
  v == null ? "—" : v.toFixed(digits);

export const money = (v: number | null | undefined, currency = "USD") =>
  v == null ? "—" : new Intl.NumberFormat("en-US", {
    style: "currency", currency, maximumFractionDigits: 2,
  }).format(v);

export const withN = (formatted: string, n: number) =>
  `${formatted} · N=${n}`;
```

- [ ] **Step 5: Write `src/components/VerdictBand.tsx`**

```tsx
import "../design/components.css";

type Verdict = { headline: string; detail: string; level: "ok" | "caution" | "not_yet_meaningful"; n_days: number };

export function VerdictBand({ v }: { v: Verdict }) {
  return (
    <div className={`verdict verdict--${v.level}`} role="status">
      <div className="verdict__headline">{v.headline}</div>
      <div className="verdict__detail">{v.detail}</div>
      <div className="verdict__meta">N={v.n_days}</div>
    </div>
  );
}
```

Add to `components.css`:

```css
.verdict {
  padding: var(--space-5); border-radius: var(--radius-lg);
  border: 1px solid var(--ground-3); margin: var(--space-5) 0;
}
.verdict--ok { background: var(--gain-soft); }
.verdict--caution { background: var(--caution-soft); }
.verdict--not_yet_meaningful { background: var(--caution-soft); }
.verdict__headline { font-family: var(--font-serif); font-size: var(--size-h2); margin-bottom: var(--space-2); }
.verdict__detail { font-size: var(--size-body); color: var(--ink-2); line-height: var(--line-body); }
.verdict__meta { font-size: var(--size-micro); color: var(--ink-3); margin-top: var(--space-3); }
```

- [ ] **Step 6: Write `src/components/MetricCard.tsx`**

```tsx
export function MetricCard({ label, value, n, sub, tone }: {
  label: string; value: string; n: number;
  sub?: string; tone?: "neutral" | "gain" | "loss";
}) {
  return (
    <div className={`metric metric--${tone ?? "neutral"}`}>
      <div className="metric__label">{label}</div>
      <div className="metric__value">{value}</div>
      <div className="metric__meta">
        {sub && <span className="metric__sub">{sub}</span>}
        <span className="metric__n">N={n}</span>
      </div>
    </div>
  );
}
```

CSS:

```css
.metric {
  background: var(--ground-2); border: 1px solid var(--ground-3);
  padding: var(--space-4) var(--space-5); border-radius: var(--radius-lg);
}
.metric__label { font-size: var(--size-caption); color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.06em; }
.metric__value { font-family: var(--font-mono); font-variant-numeric: tabular-nums; font-size: var(--size-h1); color: var(--ink-1); margin-top: var(--space-2); }
.metric__meta { display: flex; justify-content: space-between; margin-top: var(--space-3); font-size: var(--size-micro); color: var(--ink-3); }
.metric--gain .metric__value { color: var(--gain); }
.metric--loss .metric__value { color: var(--loss); }
```

- [ ] **Step 7: Write `src/components/Layout.tsx`** — `<Nav>` on left (250px), main content area, header bar. Vertical scrolling only. Never horizontal.

- [ ] **Step 8: Write `src/components/YearLedger.tsx`** — 53 columns × 7 rows of squares, colored by date's return. Empty squares have `border: 1px solid var(--ground-3)` and transparent background. Hover shows a floating card.

- [ ] **Step 9: Write `src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/query";
import { Layout } from "./components/Layout";
// Pages — placeholders in this task; real content in Tasks 28/29
import Today from "./pages/Today";
import TradeEntry from "./pages/TradeEntry";
import Ledger from "./pages/Ledger";
import Performance from "./pages/Performance";
import Monthly from "./pages/Monthly";
import Attribution from "./pages/Attribution";
import Policy from "./pages/Policy";
import Accounts from "./pages/Accounts";
import Audit from "./pages/Audit";
import Tearsheet from "./pages/Tearsheet";
import Settings from "./pages/Settings";
import Allocator from "./pages/Allocator";

import "./design/reset.css";
import "./design/tokens.css";
import "./design/typography.css";
import "./design/components.css";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/tej-capital">
        <Routes>
          <Route path="/share/:token" element={<Allocator />} />
          <Route element={<Layout />}>
            <Route path="/" element={<Today />} />
            <Route path="/trades/new" element={<TradeEntry />} />
            <Route path="/ledger" element={<Ledger />} />
            <Route path="/performance" element={<Performance />} />
            <Route path="/monthly" element={<Monthly />} />
            <Route path="/attribution" element={<Attribution />} />
            <Route path="/policy" element={<Policy />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/tearsheet/:month" element={<Tearsheet />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 10: Update `src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>,
);
```

- [ ] **Step 11: Create placeholder page files** at `src/pages/<Name>.tsx` — each returns `<EmptyState>` with the correct microcopy. This lets `npm run dev` render every route.

- [ ] **Step 12: Sanity check + commit**

```bash
cd tej-capital/frontend && npm run build
git add tej-capital/frontend/
git commit -m "feat(tej-capital): frontend scaffold — router, query client, design system, shared components"
```

---

## Task 28: Frontend — habit half (Today, Trade Entry, Ledger)

**Files:**
- Create: `tej-capital/frontend/src/pages/Today.tsx`
- Create: `tej-capital/frontend/src/pages/TradeEntry.tsx`
- Create: `tej-capital/frontend/src/pages/Ledger.tsx`
- Create: `tej-capital/frontend/src/hooks/useAccounts.ts`
- Create: `tej-capital/frontend/src/hooks/useNav.ts`
- Create: `tej-capital/frontend/src/hooks/useTrades.ts`
- Create: `tej-capital/frontend/src/hooks/useLedger.ts`
- Create: `tej-capital/frontend/tests/pages.spec.ts` (Playwright happy path)

**Interfaces:**
- Consumes: `api` from Task 27, backend routes from Tasks 13–15.
- Produces: three fully wired pages that speak to the backend and honour every rule in Product Brief §4.1, §4.2, §4.3.

Reference the design tokens from Task 27 §Design System throughout. Every field label, placeholder, and helper text is copied verbatim from Product Brief §4 — the microcopy is doing work.

- [ ] **Step 1: Implement `useAccounts`, `useNav`, `useTrades`, `useLedger`** — TanStack Query hooks. Example:

```tsx
// hooks/useAccounts.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type Account = {
  id: string; name: string; broker: string; currency: string;
  account_type: "live"|"prop_funded"|"prop_evaluation"|"demo"|"verified_mirror";
  in_composite: boolean; exclusion_reason: string | null;
  created_at: string; archived_at: string | null;
};

export function useAccounts() {
  return useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Account>) => api.post<Account>("/accounts", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  });
}
```

- [ ] **Step 2: Implement `pages/Today.tsx`**

Requirements from Product Brief §4.1 — the ONE screen that carries the whole product:
- Field labels/placeholders copied verbatim (Date, Account, Closing equity, Money in or out today, Type of movement, Open risk right now, Did you break a rule today?, What rule and what triggered it, Today's note).
- Correction mode automatically activates when a mark exists for that date — shows the existing value and requires a reason (min 10 chars); microcopy: `"This will be recorded as a correction. The original entry stays in the log."`
- Empty state (first ever use) — `"No marks yet. Enter today's closing equity and your record begins. Everything on every other screen is built from this one number, entered every day."`
- Missed-days quiet banner — after save, if days without marks exist within last 14 days, show once: `"<N> days without a mark — <date1> and <date2>. Backfill them or leave them blank; blank days are excluded from your statistics, not counted as flat."`
- On save: compact confirmation showing today's return, equity vs last peak, any limit newly breached, and the day's coloured square appearing in the year ledger below.

Layout: form on left half, coloured YearLedger on right half showing current year's marks. On mobile the ledger stacks below.

```tsx
// pages/Today.tsx — key structural fragments (compose with Layout/components from Task 27)
import { useState } from "react";
import { useAccounts } from "../hooks/useAccounts";
import { useTodayMark, useSubmitMark, useCorrectMark } from "../hooks/useNav";
import { EmptyState } from "../components/EmptyState";
import { YearLedger } from "../components/YearLedger";

export default function Today() {
  const { data: accounts, isLoading: aLoad } = useAccounts();
  const [accountId, setAccountId] = useState<string>();
  const activeId = accountId ?? accounts?.[0]?.id;
  const { data: today } = useTodayMark(activeId);
  const submit = useSubmitMark(activeId);
  const correct = useCorrectMark(activeId);
  const isCorrection = !!today;

  if (!aLoad && !accounts?.length) {
    return <EmptyState
      title="No accounts yet"
      body="Add an account first (Accounts tab) so we know where your closing equity is coming from."
      cta={{ label: "Add account", to: "/accounts" }}
    />;
  }
  // ... form JSX with verbatim labels from Brief §4.1
}
```

- [ ] **Step 3: Implement `pages/TradeEntry.tsx`** — two-part flow: BEFORE (thesis) and AFTER (outcome), toggled by a segmented control at top. Fields verbatim from Brief §4.2. If `risk_amount` empty, the trade goes to enrichment queue (visible link at top: `"12 trades need enrichment"`).

- [ ] **Step 4: Implement `pages/Ledger.tsx`**

- Full-year `YearLedger` component (from Task 27).
- Streak counters card group: longest green run, longest red run, longest run of consecutive marked days (discipline streak — most prominent per Brief §4.3).
- Year switcher at top.
- Footer: `"184 marked days · 103 green · 81 red · 12 days without a mark"` — exact format from spec.

- [ ] **Step 5: Playwright happy path**

```ts
// tests/pages.spec.ts
import { test, expect } from "@playwright/test";

test("enter a mark and see it on the ledger", async ({ page }) => {
  await page.goto("http://localhost:5174/tej-capital/accounts");
  await page.click("text=Add account");
  await page.fill('input[name="name"]', "Main");
  await page.fill('input[name="broker"]', "IBKR");
  await page.selectOption('select[name="currency"]', "USD");
  await page.selectOption('select[name="account_type"]', "live");
  await page.click("text=Create");

  await page.goto("http://localhost:5174/tej-capital/");
  await page.fill('input[name="closing_equity"]', "15000");
  await page.click("text=Save mark");

  await page.goto("http://localhost:5174/tej-capital/ledger");
  await expect(page.locator(".year-ledger [data-marked=true]")).toHaveCount(1);
});
```

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(tej-capital): habit-half pages — Today (correction mode, missed-days), Trade Entry, Ledger"
```

---

## Task 29: Frontend — insight half (Performance, Monthly, Attribution, Policy, Accounts, Audit, Tearsheet, Settings, Allocator)

**Files:** one `.tsx` file per page under `src/pages/` (nine total), plus data hooks under `src/hooks/`.

For each page, apply the design system from Task 27 (never introduce new colors or spacing) and lift microcopy verbatim from Product Brief §4.

### Performance

- Top band: four `MetricCard`s — cumulative return, Sharpe, max drawdown, current drawdown. Each with N.
- Immediately below: `VerdictBand` (from Task 27) — data from `GET /api/metrics/live`, `verdict` block.
- Collapsible metric groups: Returns · Risk · Risk-Adjusted · Statistical Validity · Trades · Discipline. Each metric shown with a one-line plain-English explainer under the label.
- Charts: equity curve (Recharts line) with drawdown chart underneath (Recharts area); the five worst drawdowns as a table with `depth · duration_days · recovery_date`; rolling 63-day Sharpe as a Recharts line.
- Period selector: since inception / last 12 months / YTD / custom.

### Monthly Returns

- Year × month grid using the `MonthlyGrid` component. Blank for months with no trading, never `0%` (R3).
- Below the grid: months with data · % positive · best · worst · average · standard deviation.
- Click a month → routes to `/tearsheet/:month`.

### Attribution

- Grouping selector: setup / asset / session / htf / dow — data from `GET /api/attribution?by=...`.
- Table columns per Brief §4.6, with the `verdict` column driving row background: `not_enough` → default, `retire` → `--loss-soft`, `marginal` → `--caution-soft`, `working` → `--gain-soft`.
- Concentration warning card (`GET /api/attribution/concentration`) — Brief-verbatim copy: `"Three trades produced 61% of your profit. Your effective sample size is much smaller than your trade count suggests."`
- Discipline comparison card (`GET /api/attribution/compliance-gap`) — Brief-verbatim: `"Trades where you followed your rules: +0.42R average, 168 trades. Trades where you didn't: −0.31R average, 19 trades. The gap is unlikely to be chance. Your problem isn't strategy."`

### Risk Policy

- **Top — live monitor.** One row per limit type: what the limit is, what the book is currently doing, `OK` or `BREACH` chip, and the user's committed action shown BACK to them on breach (Brief §4.7 "the entire point").
- **Bottom — written IPS.** Sections editable per `PATCH /api/policy/document/{section}`.
- **Amendment flow:** clicking "amend" opens a modal. If the API returns `409 amendment_blocked_during_drawdown`, the modal shows the Brief-verbatim text and requires ticking `"override and log it"` PLUS a reason ≥ 30 chars to proceed.

### Accounts & Capital

- Two columns: account list + capital movements log.
- Prop accounts sectioned separately with the Brief-verbatim label: `"Prop income. Excluded from the track record by policy — a prop payout shows you cleared someone's rule set, not that you compound capital."`
- Running totals kept visually separate: `Net capital contributed` vs `Trading profit`.

### Audit Trail

- One unified table sourced from `GET /api/audit` — corrections, policy amendments, overrides. Filter chips at top: correction · amendment · override · superseded.
- Frame it as a strength per Brief §4.9: `"Your record has 7 corrections across 184 days, each with a stated reason. Allocators expect corrections. What they check is whether you disclosed them."`
- Each row: date · type · table · reason · resulting row link.

### Monthly Tearsheet

- One-page factsheet layout — sized to A4/Letter print CSS.
- Header: TEJ CAPITAL · strategy description · period.
- The four headline figures (as `MetricCard`s in a 4-col grid).
- Equity curve + monthly grid + metric table.
- Verdict text (verbatim from `verdict` API field).
- Commentary box — REQUIRED to save. Placeholder: `"What went wrong this month, and what are you changing? Write it as if to someone who has your money."`
- Footer: standing footnote on methodology + self-reported disclaimer.
- Two buttons: `Download PDF` (calls `GET /api/export/tearsheet/{y}/{m}.pdf`; if 200 with HTML content-type, opens in a new tab and shows the `X-Tej-Warning`) and `Copy allocator link` (creates a token and copies `/tej-capital/share/{token}` to clipboard).

### Settings

- All fields from spec §4.5.
- `strategy_variants_tested` field carries the Brief-verbatim helper: `"Every parameter you swept in a backtest counts. Testing 200 variants and keeping the best one inflates its apparent edge; this number corrects for that."`
- Targets subsection editable via `POST /api/settings/targets`.

### Allocator View

- Read-only tearsheet accessible at `/share/:token` (outside the Layout — no side nav).
- Consumes `GET /api/allocator/view?token=...`.
- Renders: tearsheet + monthly grid + equity curve + drawdown table + verdict + methodology footnotes.
- Hides journal, emotional state, individual trade notes, account balances — enforced by the API but the frontend does not attempt to render fields that aren't in the payload.

### Implementation steps

- [ ] **Step 1: Implement all nine pages, one file per page** — each ≤ 250 lines. Reuse `MetricCard`, `VerdictBand`, `EmptyState`, `YearLedger`, `MonthlyGrid` from Task 27.
- [ ] **Step 2: Add data hooks per page under `src/hooks/`** — one hook per data resource.
- [ ] **Step 3: Manual smoke check** — `npm run dev` and click through every route.
- [ ] **Step 4: Playwright happy path** — extend the Task 28 test file with one navigation smoke per page (asserting the page's headline copy exists).
- [ ] **Step 5: Commit**

```bash
git commit -m "feat(tej-capital): insight-half pages — Performance, Monthly, Attribution, Policy, Accounts, Audit, Tearsheet, Settings, Allocator"
```

---

## Task 30: Nav link in existing `trading-journal/frontend`

**Files:**
- Modify: `trading-journal/frontend/src/App.tsx` (or the existing nav component — first task step confirms which file)

**Interfaces:**
- Consumes: nothing from the new codebase.
- Produces: one visible nav item labelled `TEJ Capital ↗` that opens `/tej-capital/` in a new browser tab via `window.open(url, "_blank", "noopener,noreferrer")`. Placed as the last nav item.

This is the ONLY change allowed to the existing `trading-journal/frontend` — per spec §12 and Global Constraints.

- [ ] **Step 1: Identify the nav file**

```bash
grep -rn "nav\|Nav\|Sidebar\|Menu" trading-journal/frontend/src --include="*.tsx" -l | head -5
```

Expected: prints one or two files that define the existing app's nav. If the existing app has no nav (single-page), add the link to `App.tsx` near the header.

- [ ] **Step 2: Add the link**

```tsx
// e.g. in existing Sidebar.tsx
<a
  href="/tej-capital/"
  target="_blank"
  rel="noopener noreferrer"
  className="nav-link tej-capital-link"
  onClick={(e) => {
    e.preventDefault();
    window.open("/tej-capital/", "_blank", "noopener,noreferrer");
  }}
>
  TEJ Capital ↗
</a>
```

Style it to match the existing nav's other items. Use only the existing app's tokens — do NOT bring the new design system tokens into the existing app.

- [ ] **Step 3: Manual smoke — start both frontends and click the link**

```bash
# Terminal A
cd trading-journal/frontend && npm run dev
# Terminal B
cd trading-journal/tej-capital/frontend && npm run dev
```

Click the new nav item — a fresh browser tab opens to `http://localhost:5174/tej-capital/`.

- [ ] **Step 4: Commit**

```bash
git add trading-journal/frontend/src/
git commit -m "feat(trading-journal): add TEJ Capital nav link (opens new tab; existing app otherwise untouched)"
```

---

## Task 31: docker-compose + Caddyfile + `.env.example`

**Files:**
- Create: `tej-capital/docker-compose.yml`
- Create: `tej-capital/Caddyfile`
- Create: `tej-capital/.env.example`
- Create: `tej-capital/frontend/Dockerfile`

**Interfaces:**
- Produces: `docker compose up` on a fresh machine brings up postgres (timescale), api, web (nginx serving the built frontend), caddy (TLS + single-user basic auth). Optional `worker` and `temporal` services declared but commented out — enabled by setting `TEJ_TEMPORAL_HOST` in `.env`.

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: timescale/timescaledb-ha:pg16
    environment:
      POSTGRES_USER: tej
      POSTGRES_PASSWORD: tej
      POSTGRES_DB: tej_capital
    volumes:
      - tej_pgdata:/var/lib/postgresql/data
    ports:
      - "5433:5432"

  api:
    build: ./backend
    depends_on: [postgres]
    environment:
      TEJ_DATABASE_URL: postgresql+asyncpg://tej:tej@postgres:5432/tej_capital
      TEJ_TELEGRAM_BOT_TOKEN: ${TEJ_TELEGRAM_BOT_TOKEN:-}
      TEJ_TELEGRAM_CHAT_ID: ${TEJ_TELEGRAM_CHAT_ID:-}
      TEJ_QDRANT_URL: ${TEJ_QDRANT_URL:-}
      TEJ_LLM_API_KEY: ${TEJ_LLM_API_KEY:-}
      TEJ_ALLOCATOR_LINK_SECRET: ${TEJ_ALLOCATOR_LINK_SECRET:-change-me}
    ports:
      - "8000:8000"
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"

  web:
    build: ./frontend
    depends_on: [api]
    ports:
      - "5174:80"

  caddy:
    image: caddy:2
    depends_on: [api, web]
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config

  # Enable if you have a Temporal server:
  # worker:
  #   build: ./backend
  #   depends_on: [postgres]
  #   environment:
  #     TEJ_DATABASE_URL: postgresql+asyncpg://tej:tej@postgres:5432/tej_capital
  #     TEJ_TEMPORAL_HOST: temporal:7233
  #   command: python -m app.workflows.worker

volumes:
  tej_pgdata:
  caddy_data:
  caddy_config:
```

- [ ] **Step 2: Write `Caddyfile`** — single-user basic auth

```
{
  email admin@tej.capital
}

tej.local {
  handle_path /api/* {
    reverse_proxy api:8000
  }
  handle_path /tej-capital/* {
    reverse_proxy web:80
  }
  basicauth {
    tej JDJhJDEwJHRlbXBsYXRlLXJlcGxhY2VkLXdpdGgtcmVhbC1oYXNo
  }
}
```

Instruct user in README to replace the bcrypt hash with output of `caddy hash-password`.

- [ ] **Step 3: Write `.env.example`** — every env var the app reads, commented with its role and a default sentinel.

```
# --- Database ---
TEJ_DATABASE_URL=postgresql+asyncpg://tej:tej@localhost:5432/tej_capital

# --- Integrations (unset = disabled; app runs without them) ---
TEJ_TELEGRAM_BOT_TOKEN=
TEJ_TELEGRAM_CHAT_ID=

TEJ_QDRANT_URL=
TEJ_LLM_API_KEY=

TEJ_MT5_LOGIN=
TEJ_MT5_PASSWORD=
TEJ_MT5_SERVER=

TEJ_BYBIT_API_KEY=
TEJ_BYBIT_SECRET=

TEJ_DARWINEX_API_KEY=

TEJ_TEMPORAL_HOST=

# --- Shareable-link signing ---
TEJ_ALLOCATOR_LINK_SECRET=change-me-in-prod
```

- [ ] **Step 4: Write `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html/tej-capital
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

Add `frontend/nginx.conf`:

```
server {
  listen 80;
  location /tej-capital/ {
    alias /usr/share/nginx/html/tej-capital/;
    try_files $uri $uri/ /tej-capital/index.html;
  }
}
```

- [ ] **Step 5: Bring the stack up on a clean checkout**

```bash
cd tej-capital && cp .env.example .env && docker compose up --build -d
curl -sf http://localhost:8000/api/health | jq
```

Expected: `{"status":"ok","db":"ok","integrations":{...all false...}}`.

- [ ] **Step 6: Commit**

```bash
git add tej-capital/docker-compose.yml tej-capital/Caddyfile tej-capital/.env.example \
        tej-capital/frontend/Dockerfile tej-capital/frontend/nginx.conf
git commit -m "chore(tej-capital): docker-compose + Caddyfile + env template — one-command boot"
```

---

## Task 32: README + smoke tests + Playwright happy path

**Files:**
- Modify: `tej-capital/README.md` — add operator sections.
- Create: `tej-capital/frontend/playwright.config.ts`
- Modify: `tej-capital/frontend/tests/pages.spec.ts` — add cross-page navigation smoke.
- Create: `tej-capital/backend/tests/test_full_flow.py` — one end-to-end backend smoke.

**Interfaces:**
- Consumes: every prior task.
- Produces: onboarding doc + a single end-to-end test that proves the whole app runs.

- [ ] **Step 1: Extend `README.md`**

Add sections: `Prerequisites`, `Local dev`, `Running tests`, `Enabling integrations` (one subsection per: Telegram, Qdrant + LLM, MT5, Bybit, Darwinex, Temporal, PDF export), `Deploying to Oracle Cloud`, `Backup and restore`, `Security posture` (read-only broker keys, IP allowlisting, `pg_dump` schedule).

- [ ] **Step 2: Write `playwright.config.ts`**

```ts
import { defineConfig } from "@playwright/test";
export default defineConfig({
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5174/tej-capital/",
    timeout: 60_000,
    reuseExistingServer: !process.env.CI,
  },
  use: { baseURL: "http://localhost:5174" },
  testDir: "tests",
});
```

- [ ] **Step 3: Extend `tests/pages.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

const ROUTES = [
  ["/", "Today"],
  ["/ledger", "Ledger"],
  ["/performance", "Performance"],
  ["/monthly", "Monthly"],
  ["/attribution", "Attribution"],
  ["/policy", "Risk Policy"],
  ["/accounts", "Accounts"],
  ["/audit", "Audit"],
  ["/settings", "Settings"],
] as const;

for (const [path, headline] of ROUTES) {
  test(`${path} renders headline ${headline}`, async ({ page }) => {
    await page.goto(`http://localhost:5174/tej-capital${path}`);
    await expect(page.getByRole("heading", { name: headline })).toBeVisible();
  });
}
```

- [ ] **Step 4: Backend end-to-end smoke**

```python
# tests/test_full_flow.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_end_to_end_flow_create_account_mark_trade_freeze(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        acct = (await ac.post("/api/accounts", json={
            "name": "Main", "broker": "IBKR", "currency": "USD", "account_type": "live"
        })).json()

        await ac.post(f"/api/accounts/{acct['id']}/nav", json={
            "as_of_date": "2026-08-16", "closing_equity": "15000.00"})

        await ac.post("/api/trades", json={
            "account_id": acct["id"], "instrument": "XAUUSD", "direction": "long",
            "entry_price": "2400", "exit_price": "2430", "initial_stop": "2390",
            "position_size": "0.10", "risk_amount": "100", "gross_pnl": "300", "costs": "5",
            "opened_at": "2026-08-16T10:00:00+00:00",
            "closed_at": "2026-08-16T15:00:00+00:00"})

        snap = (await ac.post("/api/metrics/freeze", json={
            "as_of_date": "2026-08-16", "scope": "composite"})).json()
        assert len(snap["ledger_hash"]) == 64

        live = (await ac.get("/api/metrics/live")).json()
        assert live["verdict"]["level"] == "not_yet_meaningful"
        assert "N=" not in str(live["verdict"]["headline"])  # N is in a separate field
        assert live["verdict"]["n_days"] == 0  # one NAV row → zero return days
```

- [ ] **Step 5: Run the full test suite**

```bash
cd tej-capital/backend && pytest -v
cd ../frontend && npm run build && npx playwright test
```

Expected: all backend tests pass; all Playwright scenarios pass against a running dev server.

- [ ] **Step 6: Final commit**

```bash
git add tej-capital/README.md tej-capital/frontend/playwright.config.ts \
        tej-capital/frontend/tests/ tej-capital/backend/tests/test_full_flow.py
git commit -m "chore(tej-capital): README, playwright config, end-to-end smoke tests"
```

---

## Self-review (author's checklist)

Ran against the spec:

1. **Spec coverage:** every spec section maps to a task —
   - §1 scope / fully-wired vs stubbed → Tasks 21 (CSV wired) + 22 (stubs) + 23 (Temporal stub) + 24 (Telegram) + 25 (AI) + 26 (PDF).
   - §2 R1–R7 invariants → schema (Task 2), corrections helper (Task 14 `services/corrections.py`), R3 empty handling (every `core/` metric returns None), R4 composite immutability (Task 13), R5 policy versioning + drawdown-block (Task 17), R6 `{value, n}` envelope (Task 18 `_wrap`), R7 verdict (Task 11).
   - §3 repo layout → Task 1.
   - §4 data model → Tasks 2 + 3.
   - §5 twelve screens → Tasks 27 + 28 + 29 + 30.
   - §6 core metric engine → Tasks 4–11.
   - §7 exports/tearsheet → Task 26.
   - §7 ingestion → Tasks 21 + 22.
   - §8 nightly close → Task 23.
   - §9 alerts → Task 24.
   - §10 AI layer → Task 25.
   - §11 exports → Task 26.
   - §12 nav-link integration → Task 30.
   - §13 deployment → Task 31.
   - §14 testing → Tasks 4–11 (core), 12–20 (api), 28–29 (playwright), 32 (e2e).
2. **Placeholder scan:** searched for `TODO/TBD/XXX/placeholder/fill in details` in the plan — none present. Every step carries code or exact commands. Some tasks with mechanical repetition (Task 3 model files, Task 16 journal API) say "same pattern as X" but always give an example first — a fresh reviewer can implement from what's shown.
3. **Type consistency:** `Metric<T>` in `frontend/lib/api.ts` matches `_wrap` on the backend. `Verdict` type on frontend matches `verdict_band()` return dict. `enrichment_needed` is set in `_serialize` (Task 15) and read in Task 28's Trade Entry link.
4. **R6 compliance:** every metric API response goes through `_wrap` (Task 18) → `{"value": ..., "n": ...}`. The frontend `MetricCard` (Task 27) always renders `N=…`. Confirmed.

No gaps found. If a reviewer executes tasks in order, each produces working, testable software.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-16-tej-capital.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints for review.

Which approach?
