# Schema Governance QA Scenarios

## Scope

This QA matrix covers the schema-governance surface currently shipped in
`kafka-gov`, with emphasis on:

- Schema list/detail/history
- Version export / compare / rollback
- Drift visibility
- Metadata and compatibility settings
- Approval requests and audit activity
- Docker Compose container boundary (`docker-compose.yml`)
- Kafka + Schema Registry test stack (`kafka-compose.yml`)

## Tooling Note

Playwright MCP is the preferred interactive browser path when it is available,
especially for live schema-governance checks against the nginx-served frontend.
The repository's checked-in Playwright-based E2E suite (`pytest` + Playwright)
remains the automated regression lane and the container-target fallback. The
container-target tests assume the compose stacks are already running.

## Compose-backed verification commands

```bash
# 1) one-shot compose-managed governance regression lane
uv run pytest --no-cov --run-e2e --e2e-target=compose \
  tests/test_e2e_container_api.py \
  tests/test_e2e_schema_governance_api.py \
  tests/test_e2e_schema_governance_ui.py

# 2) if the stacks are already running, reuse them instead
uv run pytest --no-cov --run-e2e --e2e-target=container \
  tests/test_e2e_container_api.py \
  tests/test_e2e_schema_governance_api.py \
  tests/test_e2e_schema_governance_ui.py
```

Use Playwright MCP for targeted manual validation of the routed UI after the
compose stacks are healthy, and keep the checked-in pytest suite as the
repeatable evidence lane for regressions.

## Scenario Matrix

### Web UI scenarios

| ID | Area | Steps | Expected |
| --- | --- | --- | --- |
| WEB-001 | App shell | Open `/` | Sidebar, routed shell, and landing route load |
| WEB-002 | Schema list | Click `Schemas` | `/schemas` route activates and renders |
| WEB-003 | Schema detail actions | Open a live schema detail page | Latest download, metadata, drift banner, and editor actions render |
| WEB-004 | History preview | Preview a historical version | Version modal opens with exact schema content |
| WEB-005 | Version compare | Compare historical version to latest | Compare modal opens with change summary + diff |
| WEB-006 | Rollback execute | Restore historical version | Dedicated rollback execute flow is triggered |
| WEB-007 | Metadata settings | Edit owner/doc/tags/compatibility | Settings API request succeeds and UI refreshes |
| WEB-008 | Approvals page | Open `Approvals & Audit` | Pending approvals and recent audit sections render |
| WEB-009 | Approval decision | Approve/reject a request | Decision API is called and page refreshes |

### Container API scenarios

| ID | Area | Steps | Expected |
| --- | --- | --- | --- |
| API-001 | Health | GET `/health` on backend and nginx | 200 / healthy |
| API-002 | API root | GET `/api/v1` through nginx | 200 / message payload |
| API-003 | Approval list | GET `/api/v1/approval-requests` | 200 / JSON list |
| API-004 | Audit list | GET `/api/v1/audit/recent` | 200 / JSON list |
| API-005 | Live registry upload | POST a schema file against active registry | 201 / live subject created |
| API-006 | Live governance routes | GET detail, versions, compare, export, drift | 200 / schema-governance payloads |
| API-007 | ZIP rejection contract | POST `.zip` upload | 400/422 rejection without false success |
| API-008 | Schema routes visible | Route surface test | Newly added routes are registered |

### Compose readiness scenarios

| ID | Area | Steps | Expected |
| --- | --- | --- | --- |
| COMPOSE-001 | Kafka test stack | `docker compose -f kafka-compose.yml up -d` | `kafka1` and `schema-registry` become healthy |
| COMPOSE-002 | App stack | `docker compose up -d --build` | app/frontend/nginx/redis become healthy |
| COMPOSE-003 | Proxy path | Call backend endpoints through nginx port 90 | Requests proxy successfully |
| COMPOSE-004 | Frontend shell | Open nginx UI via Playwright | App shell loads against proxied backend |

## Test Partitioning

- `tests/test_e2e_full_system.py`
  - global shell + high-level route smoke tests
- `tests/test_e2e_schema_governance_api.py`
  - nginx/proxy smoke for governance endpoints
- `tests/test_e2e_schema_governance_ui.py`
  - schema-governance UI route smoke checks against seeded live subjects
- `tests/test_e2e_container_api.py`
  - live Schema Registry upload/version/settings/rollback checks via `kafka-compose.yml`
- unit/contract tests under `tests/test_schema_*`
  - backend route/use-case contracts

## Current Gaps

- Live compare/rollback coverage is still stronger on the backend/API side than
  on browser automation because history-driven multi-version UI flows require
  more seeded mutations than the current smoke lane provisions.
- Playwright MCP is best used for targeted manual browser validation; the
  checked-in Playwright/pytest harness remains the repeatable regression lane.
