# BACKEND KNOWLEDGE BASE

## OVERVIEW

`app/` is the FastAPI backend composition root plus clean-architecture domain modules.

## STRUCTURE

```text
app/
|- main.py        # FastAPI app factory and lifespan
|- container.py   # top-level DI wiring
|- shared/        # settings, middleware, infra glue
|- cluster/       # connection management
|- topic/         # topic governance and metrics
|- schema/        # schema registry and policy workflows
|- consumer/      # consumer monitoring and websocket flows
|- preflight/     # Typer CLI transport layer
`- tasks/         # Celery task targets
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| FastAPI startup | `app/main.py` | routers, lifespan, exception handlers |
| DI wiring | `app/container.py` | only composition root should wire broadly |
| Shared runtime config | `app/shared/settings.py` | DB/env precedence and Redis/Celery config |
| Shared infra | `app/shared/` | middleware, logging, database, common utilities |
| Topic details | `app/topic/README.md` | policies, metrics, batch use cases |
| Schema details | `app/schema/README.md` | schema governance and registry flows |
| Consumer details | `app/consumer/README.md` | metrics, websocket, health rules |
| CLI behavior | `app/preflight/interface/cli.py` | command tree, JSON envelopes, exit codes |
| Async jobs | `app/celery_app.py`, `app/tasks/metrics_tasks.py` | worker and beat entry surfaces |

## CONVENTIONS

- Keep dependency direction one-way: `interface -> application -> domain <- infrastructure`.
- Use absolute imports inside backend modules (`app.topic...`, `app.schema...`); this is an explicit topic-module rule already followed across the backend.
- Keep Python typing in native 3.12 style (`list[str]`, `str | None`) rather than legacy `typing` aliases.
- Put environment/bootstrap concerns in `app/shared/settings.py`; do not scatter env parsing across modules.
- Treat module READMEs as feature docs and this file as workflow guidance.

## PREFLIGHT CLI

- The `preflight` console entry is declared in `pyproject.toml` and implemented in `app/preflight/interface/cli.py`.
- When changing CLI output, preserve the JSON envelope contract unless tests and snapshots are updated in the same change.
- `preflight` builds transports from the same `AppContainer` used by the API, so transport behavior should stay aligned with backend use cases.

## ANTI-PATTERNS

- Do not add lazy imports inside functions; `CONTRIBUTING.md` explicitly forbids that pattern.
- Do not let domain modules depend on infrastructure or application layers.
- Do not wire dependencies from random modules; keep wide wiring in `app/container.py` or module containers.
- Do not restate module README content here; point contributors to the README for topic/schema/consumer specifics.

## COMMANDS

```bash
# backend dependencies
uv sync --group dev

# backend server
uv run uvicorn app.main:app --reload

# CLI
uv run preflight --help

# backend checks
uv run ruff check .
uv run pyrefly check --ignore missing-attribute --ignore index-error --ignore not-a-type --ignore bad-argument-type --ignore bad-assignment --ignore bad-override --ignore unexpected-keyword --ignore bad-keyword-argument
uv run pytest
```

## NOTES

- `app/main.py` startup can enqueue initial metrics sync work through Celery when snapshots are missing.
- Compose uses a migration-first startup path; local `uvicorn` does not.
