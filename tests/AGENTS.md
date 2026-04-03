# TEST KNOWLEDGE BASE

## OVERVIEW

`tests/` mixes backend unit tests, CLI snapshot contract tests, and opt-in end-to-end checks.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Pytest defaults | `pyproject.toml` | markers, coverage, discovery, addopts |
| Shared fixtures | `tests/conftest.py` | e2e flags, subprocess startup, Playwright browser fixture |
| Preflight contract tests | `tests/test_preflight_*.py` | CLI request/response contract coverage |
| Snapshot payloads | `tests/snapshots/preflight/` | expected JSON envelopes for CLI output |
| Domain helpers | `tests/domain_case_factory.py` | reusable backend-domain fixtures |
| E2E coverage | `tests/test_e2e_*.py` | skipped unless `--run-e2e` is passed |

## CONVENTIONS

- Test discovery follows `test_*.py` under `tests/` with pytest config from `pyproject.toml`.
- Snapshot-style preflight tests assert exact JSON envelope output; update snapshots only when the contract intentionally changes.
- E2E tests are opt-in and marked with `e2e`; default local pytest runs skip them.
- Local e2e bootstraps backend with `uv run uvicorn app.main:app` and frontend with `npm run dev` from `frontend/`.
- Keep test behavior aligned with CI, which runs preflight contract tests first and then the full pytest suite.

## ANTI-PATTERNS

- Do not change preflight CLI output, exit codes, or error classification without updating matching snapshot and integration tests.
- Do not force e2e coverage into routine unit-test changes; the repo intentionally keeps `--run-e2e` explicit.
- Do not bury shared fixtures inside individual tests when `tests/conftest.py` or `tests/domain_case_factory.py` is a better home.
- Do not treat coverage HTML or cache directories as authored test assets.

## COMMANDS

```bash
# full default suite
uv run pytest

# preflight contract-focused slice
uv run pytest tests/test_preflight_*.py

# opt-in e2e against local subprocesses
uv run pytest --run-e2e --e2e-target=local

# opt-in e2e against existing containers
uv run pytest --run-e2e --e2e-target=container
```

## NOTES

- `tests/conftest.py` waits for HTTP readiness before yielding e2e fixtures; slow startup failures usually surface there first.
- CI runs Ruff and pyrefly before pytest, so backend behavior changes should stay type- and lint-clean, not only test-green.
