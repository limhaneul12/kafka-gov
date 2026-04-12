# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-08
**Commit:** 96863c7
**Branch:** main

## OVERVIEW

Kafka-Gov is a mixed FastAPI + React repository for schema workflows, cluster/registry connection management, and governance policy management.
Use this file for repo-wide entrypoints and commands; use child `AGENTS.md` files for backend, frontend, and test-local rules.

## STRUCTURE

```text
kafka-gov/
|- app/         # FastAPI backend, DI wiring, domain modules
|- frontend/    # React 19 + Vite UI
|- tests/       # unit, snapshot, and opt-in e2e coverage
|- docs/        # product and ops docs
|- migrations/  # Alembic revisions
|- script/      # helper shell entrypoints
|- docker/      # alternate compose stacks
`- nginx/       # reverse proxy config
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Backend app bootstrap | `app/main.py` | FastAPI creation, router registration, lifespan startup |
| Backend composition root | `app/container.py` | dependency-injector wiring lives here |
| Runtime settings | `app/shared/settings.py` | `.env` loading, DB URL precedence, Redis/cache URLs |
| Frontend bootstrap | `frontend/src/main.tsx` | React root mount |
| Frontend routes | `frontend/src/App.tsx` | BrowserRouter and top-level page map |
| Frontend API client | `frontend/src/services/api.ts` | Axios base URL and shared endpoint helpers |
| Migrations | `script/migrate.sh`, `migrations/env.py` | app settings drive Alembic target DB |
| CI contract | `.github/workflows/ci.yml` | Ruff, pyrefly, frontend build, full pytest |
| Test bootstrap | `tests/conftest.py` | opt-in e2e spins backend and frontend subprocesses |
| Module-specific feature detail | `app/schema/README.md` | prefer README over duplicating details here |

## CONVENTIONS

- Backend and frontend are separate working areas; backend rules live in `app/AGENTS.md`, frontend rules in `frontend/AGENTS.md`.
- Module READMEs under `app/*/README.md` are the source of truth for feature-specific behavior; keep AGENTS files focused on contributor workflow and local invariants.
- Python tooling is centered on `uv`; frontend tooling is centered on npm scripts in `frontend/package.json`.
- Docker Compose startup is not identical to the Dockerfile default: `docker-compose.yml` runs migrations before starting Uvicorn.
- Local development defaults to SQLite when `KAFKA_GOV_DATABASE_URL` and `DATABASE_URL` are unset.

## ANTI-PATTERNS (THIS PROJECT)

- Do not duplicate module README content into child `AGENTS.md` files; link or point to the module README instead.
- Do not treat generated artifacts (`htmlcov/`, `.ruff_cache/`, `frontend/dist/`, `__pycache__/`) as source hotspots when navigating the repo.
- Do not assume Docker runtime matches local runtime; Compose, direct `uvicorn`, and Dockerfile `gunicorn` paths differ.
- Do not change CLI envelopes, startup flow, or API route surfaces without checking matching tests and docs.

## UNIQUE STYLES

- The frontend dev server proxies `/api` to `http://localhost:8000` and runs on port `3000`.

## COMMANDS

```bash
# backend setup
uv sync --group dev

# migrations
bash script/migrate.sh

# backend dev server
uv run uvicorn app.main:app --reload

# frontend dev server
npm install --prefix frontend
npm run dev --prefix frontend

# backend quality gates
uv run ruff format --check .
uv run ruff check .
uv run pyrefly check --ignore missing-attribute --ignore index-error --ignore not-a-type --ignore bad-argument-type --ignore bad-assignment --ignore bad-override --ignore unexpected-keyword --ignore bad-keyword-argument
uv run pytest

# frontend quality gates
npm run build --prefix frontend
npm run lint --prefix frontend

# container stack
docker-compose up -d
```

## NOTES

- Read `tests/AGENTS.md` before touching CLI envelopes, snapshots, or e2e behavior.
- Read `frontend/AGENTS.md` before changing routes, API wiring, or translated UI strings.
- Read `app/AGENTS.md` before changing dependency wiring, settings, or backend module boundaries.
