# T&M Capital

Fund-operations platform for a single discretionary trader. See
`../docs/superpowers/specs/2026-08-16-tej-capital-design.md` for the
authoritative spec.

(Historical: the code paths, URL slug (`/tej-capital/`), and DB tables
keep the `tej_` / `tej-capital` prefix because renaming those is
invasive; the user-facing brand is T&M Capital.)

## Quick start

```bash
docker compose up          # postgres, api on :8000, frontend on :5174
```

## Layout

- `backend/` — FastAPI + Postgres/TimescaleDB, pure `core/` metric engine
- `frontend/` — React + Vite, 12 screens
- `docker-compose.yml` — postgres, api, worker (optional), web, caddy

## Prerequisites

- **Docker + Docker Compose** — runs Postgres/TimescaleDB, the API, and the
  web container together. This is the only supported way to run the full
  stack end-to-end.
- **Python 3.12+** — for running the backend natively (tests, Alembic,
  local `uvicorn`). The backend ships a `.venv`; recreate it with
  `python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt`
  if it's missing.
- **Node 18+ / npm** — for the frontend dev server, build, and test
  tooling (`@playwright/test`, Vitest).
- **`psql` or another Postgres client** (optional) — handy for inspecting
  the database or running `pg_dump`/restore by hand.

## Local dev

The fastest path is the full Docker stack:

```bash
docker compose up          # postgres :5433->5432, api :8000, web :5174, caddy :80/:443
```

- API: `http://localhost:8000` (OpenAPI docs at `/docs`)
- Frontend: `http://localhost:5174/tej-capital/`
- Caddy (reverse proxy, basic-auth gated): `http://tej.local` — add
  `127.0.0.1 tej.local` to `/etc/hosts` to use it

To iterate on the backend or frontend natively instead (faster reload,
easier debugging):

```bash
# Backend — run against dockerized Postgres (host port 5433)
docker compose up -d postgres
cd backend
source .venv/bin/activate            # or: python3.12 -m venv .venv && ...
export TEJ_DATABASE_URL="postgresql+asyncpg://tej:tej@localhost:5433/tej_capital"
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend — proxies /api to localhost:8000 (see vite.config.ts)
cd frontend
npm install
npm run dev                          # http://localhost:5174/tej-capital/
```

Copy `.env.example` to `.env` in `tej-capital/` (or export the `TEJ_*`
vars directly) to configure the database URL and any integrations —
everything is optional except `TEJ_DATABASE_URL`.

## Running tests

### Backend

Tests need a reachable Postgres. The simplest setup uses the same
Docker Postgres as local dev:

```bash
docker compose up -d postgres
cd backend
source .venv/bin/activate
export TEJ_DATABASE_URL="postgresql+asyncpg://tej:tej@localhost:5433/tej_capital"
alembic upgrade head                                    # creates the schema tests hit through the ASGI app
psql -h localhost -p 5433 -U tej -d postgres -c "CREATE DATABASE tej_capital_test;"   # first run only

pytest tests/ -v                                        # full suite
pytest tests/test_full_flow.py -v                        # single end-to-end smoke test
pytest tests/path/to/test_file.py::test_name -v          # single test
```

Two databases are involved: `tej_capital` (migrated with Alembic, used
by every test that drives the app over HTTP via `httpx.ASGITransport`)
and `tej_capital_test` (schema created directly from SQLAlchemy metadata,
used by tests that need a raw `AsyncSession` via the `db` fixture in
`tests/conftest.py` / `tests/api/conftest.py`). Both are derived from
`TEJ_DATABASE_URL`, so only the one env var needs setting.

`tests/test_full_flow.py` truncates the NAV/cash-flow/trade tables before
it runs (see the `_clean_composite_tables` fixture in that file) — it
asserts on the *composite* metrics endpoint, which aggregates every
account in the database, so it needs a clean slate to assert
`n_days == 0` deterministically regardless of what other tests left
behind. This is safe to run as part of the full suite or on its own.

### Frontend

```bash
cd frontend
npm install
npm run build                # tsc + vite build — must stay clean (type errors fail the build)
npm run test:unit            # Vitest
npm run test:e2e             # Playwright (see below)
```

Playwright needs browser binaries the first time:

```bash
npx playwright install chromium
```

Then, with the backend API running on `:8000` (`docker compose up -d
postgres api` or the native `uvicorn` command above):

```bash
npx playwright test          # boots `npm run dev` itself via webServer config, hits :5174
```

`playwright.config.ts` starts the Vite dev server automatically
(`reuseExistingServer` when not in CI, so a dev server you already have
running is reused). `tests/pages.spec.ts` is a cross-page navigation
smoke test — it visits each of the 9 primary routes and asserts the
page's headline renders. It genuinely exercises the app in a browser, so
it needs both a running backend and installed browser binaries; CI
should install browsers as a separate step (`npx playwright install
--with-deps chromium`) before running the suite.

## Enabling integrations

Every integration is optional. With nothing configured, the app runs
and any endpoint that would call an unconfigured integration returns a
clear "not configured" response — nothing crashes. Set the relevant
`TEJ_*` variables in `.env` (see `.env.example`) or in the `api` service
environment in `docker-compose.yml`.

#### Telegram

Nightly-close and alert notifications post to a Telegram chat.
`app/alerts/telegram.py` dedupes to one message per `(kind, day)`.

```bash
TEJ_TELEGRAM_BOT_TOKEN=123456:ABC-your-bot-token
TEJ_TELEGRAM_CHAT_ID=-100987654321
```

Create a bot via [@BotFather](https://t.me/BotFather), add it to the
target chat/channel, and use that chat's numeric ID. Without these set,
`send_alert()` logs and returns `False` — no error surfaces to the user.

#### Qdrant + LLM

Powers journal semantic search, AI commentary, and pattern detection
(`app/ai/qdrant_search.py`, `app/ai/commentary.py`,
`app/ai/pattern_detect.py`).

```bash
TEJ_QDRANT_URL=http://localhost:6333
TEJ_LLM_API_KEY=sk-...
```

Run Qdrant locally with `docker run -p 6333:6333 qdrant/qdrant` (or add
it as a service in `docker-compose.yml`) if you don't have a managed
instance. Without `TEJ_LLM_API_KEY`, AI endpoints return a stub/no-op
response rather than erroring — see `tests/ai/test_stubs.py` for the
exact contract.

#### MT5

Broker CSV import always works with no credentials. Live MT5 ingestion
(`app/ingest/mt5_adapter.py`) additionally needs:

```bash
TEJ_MT5_LOGIN=12345678
```

(MT5 typically also needs a password and server, supplied at call time
or via the MT5 terminal itself — this platform does not persist your
MT5 password in `Settings`. Check `mt5_adapter.py` for the exact
credential contract before wiring it up in production.)

#### Bybit

```bash
TEJ_BYBIT_API_KEY=your-read-only-key
```

**Use a read-only API key** — see Security posture below. The adapter
(`app/ingest/bybit_adapter.py`) only reads trade history; it should
never be granted trading or withdrawal permissions.

#### Darwinex

```bash
TEJ_DARWINEX_API_KEY=your-api-key
```

Feeds `app/ingest/darwinex_adapter.py`. Same read-only-key guidance as
Bybit applies.

#### Temporal

The nightly-close workflow (`app/workflows/nightly_close.py`) only runs
if a Temporal server is reachable. Unlike the other integrations, the
worker process reads this directly from the process environment (not
through `.env`/pydantic `Settings`), so it must be **exported**, not
just present in a `.env` file:

```bash
export TEJ_TEMPORAL_HOST=localhost:7233     # host:port of your Temporal frontend
python -m app.workflows.worker
```

If unset, the worker prints a message to stderr and exits `0` — this is
the expected, supported state for v1. To run a local Temporal server for
development, use the [Temporal CLI](https://docs.temporal.io/cli)
(`temporal server start-dev`) or uncomment the `worker` service in
`docker-compose.yml` once you have a Temporal deployment to point it at.

#### PDF export

The Monthly Tearsheet PDF export (`app/export/tearsheet_pdf.py`) renders
via headless Chromium through the Python `playwright` package. It is not
a hard dependency: `render_pdf()` catches `ImportError` and returns
`None` if Playwright isn't installed, so the HTML tearsheet still works
without it.

```bash
pip install playwright
playwright install chromium --with-deps
```

Add `playwright` to `backend/requirements.txt` before deploying if PDF
export needs to work in production — it is intentionally left out of the
default requirements so the API image stays lean when nobody needs PDFs.

## Deploying to Oracle Cloud

The stack is designed to run as a small, single-VM Docker Compose
deployment on an Oracle Cloud Infrastructure (OCI) Always Free compute
instance (an `ARM Ampere A1` shape comfortably runs Postgres + API +
frontend + Caddy).

1. **Provision a VM.** Ubuntu 22.04+ ARM or x86, at least 2 OCPUs / 12GB
   RAM recommended. Open ingress for `80`/`443` (Caddy) in the OCI
   security list/NSG — do **not** expose `5432`/`5433` (Postgres) or
   `8000` (API) publicly; those should only be reachable inside the
   Docker network.
2. **Install Docker + Compose plugin** on the VM
   (`curl -fsSL https://get.docker.com | sh`, then
   `sudo usermod -aG docker $USER`).
3. **Clone the repo** (or just `tej-capital/`) onto the VM.
4. **Set production secrets.** Copy `.env.example` to `.env` and fill in
   real values — at minimum `TEJ_ALLOCATOR_LINK_SECRET` (used to sign
   shareable allocator links; a leaked default secret means anyone can
   forge a link). Set only the integration credentials you actually use.
5. **Point DNS** for your domain at the VM's public IP, and update the
   `Caddyfile`'s site block (currently `tej.local`) to your real domain.
   Caddy will automatically provision a Let's Encrypt TLS certificate on
   first request once DNS resolves.
6. **Set the Caddy basic-auth password.** The `Caddyfile` ships with a
   placeholder bcrypt hash — generate a real one with
   `docker run --rm caddy caddy hash-password` and replace it before
   exposing the instance to the internet.
7. **Bring the stack up:**
   ```bash
   docker compose up -d --build
   docker compose exec api alembic upgrade head   # if not already run by the api entrypoint
   ```
8. **Verify:** `curl https://your-domain/api/health` should return
   `{"status": "ok", ...}`.
9. **Persistence:** the `tej_pgdata`, `caddy_data`, and `caddy_config`
   named volumes hold everything that must survive a redeploy — do not
   `docker compose down -v` in production.

For upgrades, `git pull && docker compose up -d --build` rebuilds
changed images in place; Alembic migrations run automatically as part
of the `api` container's startup command.

## Backup and restore

The database is the only stateful, non-recreatable data in this system
(Postgres/TimescaleDB, volume `tej_pgdata`). Everything else (API,
frontend, Caddy config) is rebuildable from source.

**Backup** (run from the VM, or anywhere with network access to
Postgres):

```bash
docker compose exec -T postgres pg_dump -U tej -Fc tej_capital > tej_capital_$(date +%F).dump
```

- Use custom format (`-Fc`) — it's compressed and supports selective
  restore.
- Schedule this as a daily cron job (e.g. `0 3 * * *` local time, after
  the nightly-close workflow if Temporal is enabled) and ship the dump
  off-box (S3, Backblaze, even a second VM) — a backup that only lives
  on the same disk as the primary database doesn't protect against
  volume loss or disk failure.
- Retain at least 30 daily dumps plus a handful of weekly/monthly ones;
  dumps are small (a single-trader ledger, not a multi-tenant system) so
  this is cheap.

**Restore:**

```bash
docker compose up -d postgres
docker compose exec -T postgres pg_restore -U tej -d tej_capital --clean --if-exists < tej_capital_2026-08-16.dump
```

- `--clean --if-exists` drops existing objects before recreating them,
  so this is safe to run against a database that already has (stale)
  data in it.
- After restoring, restart the API (`docker compose restart api`) so
  connection pools reconnect cleanly, and spot-check `/api/metrics/live`
  and `/api/audit` to confirm the ledger looks right before resuming
  normal use.
- Practice this at least once before you need it for real — an
  untested backup is not a backup.

## Security posture

- **Read-only broker API keys.** MT5/Bybit/Darwinex credentials
  (`TEJ_MT5_LOGIN`, `TEJ_BYBIT_API_KEY`, `TEJ_DARWINEX_API_KEY`) should
  always be scoped to read-only / trade-history access at the broker.
  This app never places orders or moves funds — there is no code path
  that needs write or withdrawal permissions, so granting them only
  increases blast radius if a credential leaks.
- **IP allowlisting.** Where the broker or LLM/Qdrant provider supports
  it, restrict API key usage to the deploying VM's static (or Elastic)
  IP. Combine with OCI security-list rules that only allow inbound
  `80`/`443` from the internet and keep every other port
  (`5432`/`5433`, `8000`, `7233`) closed to the public internet — those
  should only be reachable from `localhost` or the Docker network.
- **`pg_dump` schedule.** See Backup and restore above — a daily
  `pg_dump -Fc` shipped off-box, retained for 30+ days, is the primary
  defense against data loss (disk failure, accidental `DROP`, a bad
  migration). This is distinct from disaster-recovery — it's the
  baseline every deployment should have running from day one.
- **Shareable links** (`TEJ_ALLOCATOR_LINK_SECRET`) are HMAC-signed
  tokens, not session cookies — rotate the secret (which invalidates all
  existing links) if you suspect it has leaked, and never commit a real
  value to source control; `.env.example` intentionally ships a
  `change-me-in-prod` placeholder.
- **Corrections, not deletes.** Every mutable financial fact (NAV marks,
  cash flows, trade economics) is corrected via an append-only
  supersede-and-log flow (`app/services/corrections.py`), never an
  in-place UPDATE or DELETE. This means the audit trail
  (`/api/audit`) is a complete, tamper-evident record of every change —
  treat any gap in that trail as a security incident, not just a bug.
