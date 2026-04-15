# BACKEND KNOWLEDGE BASE

## OVERVIEW

`app/` is the FastAPI backend composition root plus clean-architecture domain modules.

## STRUCTURE

```text
app/
|- main.py        # FastAPI app factory and lifespan
|- container.py   # top-level DI wiring
|- shared/        # settings, middleware, infra glue
|- registry_connections/  # schema registry connection management
`- schema/        # schema registry and policy workflows
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| FastAPI startup | `app/main.py` | routers, lifespan, exception handlers |
| DI wiring | `app/container.py` | only composition root should wire broadly |
| Shared runtime config | `app/shared/settings.py` | DB/env precedence and Redis/cache config |
| Shared infra | `app/shared/` | middleware, logging, database, common utilities |
| Schema details | `app/schema/README.md` | schema governance and registry flows |

## CONVENTIONS

- Keep dependency direction one-way: `interface -> application -> domain <- infrastructure`.
- Use absolute imports inside backend modules (`app.schema...`, `app.registry_connections...`, `app.shared...`).
- Keep Python typing in native 3.12 style (`list[str]`, `str | None`) rather than legacy `typing` aliases.
- Put environment/bootstrap concerns in `app/shared/settings.py`; do not scatter env parsing across modules.
- Treat module READMEs as feature docs and this file as workflow guidance.

## ANTI-PATTERNS

- Do not add lazy imports inside functions; `CONTRIBUTING.md` explicitly forbids that pattern.
- Do not let domain modules depend on infrastructure or application layers.
- Do not wire dependencies from random modules; keep wide wiring in `app/container.py` or module containers.
- Do not restate module README content here; point contributors to the README for schema specifics.

## COMMANDS

```bash
# backend dependencies
uv sync --group dev

# backend server
uv run uvicorn app.main:app --reload

# backend checks
uv run ruff check .
uv run pyrefly check --ignore missing-attribute --ignore index-error --ignore not-a-type --ignore bad-argument-type --ignore bad-assignment --ignore bad-override --ignore unexpected-keyword --ignore bad-keyword-argument
uv run pytest
```

## NOTES

- Compose uses a migration-first startup path; local `uvicorn` does not.
