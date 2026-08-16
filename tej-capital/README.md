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
