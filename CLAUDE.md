# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Monorepo: FastAPI backend (`backend/`, Python 3.11+, SQLAlchemy 2.x, SQLite) and React/TypeScript frontend (`frontend/`, Vite 5, React 18, React Router 6, i18next). Deployed via Docker Compose; nginx in `frontend/` acts as a reverse proxy in production.

## Local development

Always run the stack via Docker Compose:

```bash
docker compose -f docker/docker-compose.local.yml up
```

Exposes frontend on `:3000` and backend on `:8000`. The local compose file already sets `AUTH_MODE=none` and `ALLOW_INSECURE_LOCAL=true` — do not commit code that requires those two together for any other mode.

Other compose variants in `docker/`:
- `docker-compose.gateway.yml` — production (only nginx `:32123` exposed, backend internal)
- `docker-compose.traefik.yml` — production behind Traefik ForwardAuth SSO

## Auth modes

Backend `AUTH_MODE` is either `none` (local dev only, requires `ALLOW_INSECURE_LOCAL=true`) or `forwardauth` (reads identity from `X-Forwarded-User` / `-Email` / `-Groups` headers). Permissions key off application roles resolved from `ROLE_GROUPS`, a JSON list like `[{"role":"admin","groups":["admins"]},{"role":"editor","groups":["family"]},{"role":"member","groups":["members"]},{"role":"viewer","groups":["relatives","friends"]}]`. Supported roles are `admin`, `editor`, `member`, and `viewer`; `viewer` is read-only and is also the fallback for authenticated users without a mapped group.

## Database

SQLAlchemy auto-creates all tables on startup (`Base.metadata.create_all()` in `backend/app/main.py` lifespan), then runs any `backend/migrate_*.py` via `run_migrations()`. No manual migration step is needed locally. To add a new migration, create `backend/migrate_<name>.py` following the pattern of `migrate_add_soft_delete.py` and register it in `run_migrations()`.

## Frontend URLs

In production (gateway mode) the frontend uses **relative** `/api/...` and `/media/...` paths — nginx proxies these to the backend. Never hardcode `http://localhost:8000` or similar in frontend code. The dev compose file sets `VITE_API_BASE_URL=http://localhost:8000` explicitly; production leaves it empty.

## i18n — three locales must stay in sync

User-facing strings live in `frontend/src/i18n/{en,he,ru}.json`. **Any new or renamed key must be added to all three files** (English, Hebrew, Russian) in the same commit. Use `/i18n-check` to verify keys match across locales before finishing work.

## Testing

There is no real test suite — `test_backend.sh` only checks Python syntax. This is an experimental project; do not propose adding pytest / eslint / mypy / prettier setups unless explicitly asked. Verify changes by running the stack and exercising the feature.

## Git

**Ask before committing or pushing.** This is a solo project but the user wants to decide each time. Don't create branches or PRs unprompted.

## CI

`.github/workflows/docker-images.yml` builds both service images on push to `main` and version tags, publishing to `ghcr.io/bronweg/doll-inventory-{backend,frontend}`.
