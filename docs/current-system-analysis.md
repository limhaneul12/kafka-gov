# Current System Analysis

_Reviewed: 2026-04-15_

## Executive Summary

- The shipped runtime is already much narrower than the repository name suggests: the active product surface is **schema governance + connection management + audit/approval**, not a general Kafka operations suite.
- Kafka topic CRUD, consumer UIs, and WebSocket surfaces are no longer shipped. The remaining topic concept is a **read-only naming-derived hint** exposed from schema subjects.
- The main source of complexity is not the active runtime itself, but the **coexistence of dormant future-state domains** (`product`, `contract`, `catalog`, `lineage`, standalone `governance`) and **legacy Kafka-oriented infrastructure/dependencies**.

## 1. Current Core Runtime

### 1.1 Backend surface actually wired into FastAPI

The application boot path only wires three runtime areas:

1. **`shared`** — audit history + approval requests
2. **`cluster`** — Kafka broker / Schema Registry connection management
3. **`schema`** — schema governance, batch apply/dry-run, history, policy, known-topic hints

This is visible in `app/main.py`, where only `shared_router`, `cluster_router`, `schema_router`, and `schema_policy_router` are included.

### 1.2 Frontend surface actually shipped

The active React routes are:

- `/governance/dashboard`
- `/history`
- `/schemas`
- `/schemas/:subject`
- `/connections`
- `/schemas/policies`

The sidebar matches this reduced surface and no longer exposes Topic / Consumer navigation.

### 1.3 Functional core users can use today

Based on the active routers and UI, the current system supports:

- **Schema governance workflows**
  - upload
  - batch dry-run / apply
  - schema change planning / rollback planning
  - schema history
  - governance dashboard
  - schema policies
  - delete impact analysis / deletion
- **Connection management**
  - Kafka broker CRUD / activation / connection test
  - Schema Registry CRUD / activation / connection test
- **Governance backbone**
  - audit history
  - approval-request lifecycle
- **Read-only topic context**
  - known topic names derived from subject naming rules only

## 2. Legacy Kafka Traces Still Present

The repository is no longer topic-centric at runtime, but Kafka-oriented traces still remain in several layers.

### 2.1 Kafka infrastructure is still active for connection management

`app/infra/kafka/connection_manager.py` still creates and caches:

- `confluent_kafka.admin.AdminClient`
- `kafka.KafkaAdminClient`
- `AsyncSchemaRegistryClient`

So Kafka is still part of the shipped runtime as an **infrastructure connectivity capability**, even though topic operations are gone.

### 2.2 Topic semantics survive as naming-derived hints

The remaining topic behavior is intentionally limited to:

- `GET /api/v1/schemas/known-topics/{subject}`
- schema delete impact responses that include `affected_topics`
- schema detail UI text explicitly saying these are **not authoritative topic associations**

This is a controlled remnant, not a full topic-management feature.

### 2.3 Dependency footprint is still Kafka-heavy

The backend dependency lists still include:

- `confluent-kafka`
- `aiokafka`
- `kafka-python-ng`
- `kafka-python`

That footprint is larger than the currently shipped feature set suggests.

### 2.4 Some storage/model vocabulary still reflects the old topic/consumer worldview

Examples include:

- shared activity types that still mention `"topic"`
- schema infrastructure models that still store `topics` and `consumers`
- roadmap / PRD language that still describes topic- and producer-linked future capabilities

These are useful clues for history and future direction, but they add onboarding noise for a team trying to understand the present-day system boundary.

## 3. Dormant or Future-State Domains Present in the Repo

The repository still contains substantial domain code for:

- `app/product`
- `app/contract`
- `app/catalog`
- `app/lineage`
- `app/governance`

However, these are **not part of the shipped FastAPI route surface** today. They exist mostly as domain/use-case building blocks and target-state groundwork.

The PRD in `docs/features/real-time-data-governance-system.md` explicitly frames these areas as the **next platform direction**, not current runtime reality.

## 4. System Structure in Practice

### 4.1 Practical runtime layering

- **Frontend**
  - React shell for schema pages, governance dashboard, history, policies, connections
- **API**
  - FastAPI app with `shared`, `cluster`, `schema`
- **Application layer**
  - use cases for schema workflows, connection CRUD/tests, approval/audit
- **Infrastructure**
  - DB repositories
  - Redis
  - Schema Registry client
  - Kafka admin connectivity
  - MinIO-backed schema artifact storage

### 4.2 Runtime boundary that a new team should assume

If a new team had to reason about the product today, the safest mental model is:

> “This is a schema-governance control plane with Kafka/Schema Registry connection management and audit/approval support. It is not a general Kafka topic/consumer operations platform anymore.”

## 5. Priority Cleanup Areas

### Priority 1 — Decide whether Kafka broker connection management is still in-scope

Why it matters:

- The UI still exposes a Kafka broker tab in Connections.
- The backend still ships `/api/v1/clusters/brokers`.
- The connection manager still maintains Kafka admin clients.

If Kafka broker registration/testing is still a required supporting feature, document it clearly as part of the supported boundary.  
If not, this is the highest-value remaining runtime simplification target.

### Priority 2 — Quarantine or explicitly mark dormant future-state modules

Why it matters:

- `product`, `contract`, `catalog`, `lineage`, and standalone `governance` add a lot of code-reading overhead.
- None of them are active shipped routes today.

Recommended cleanup:

- move them behind clearer “future-state / not wired” documentation,
- or consolidate them under a clearly marked incubation area,
- or add a repo-level map explaining “active runtime vs dormant groundwork.”

### Priority 3 — Reduce leftover topic/consumer vocabulary where it no longer reflects reality

Why it matters:

- the runtime intentionally moved away from authoritative topic management,
- but internal models, comments, and constants still suggest topic/consumer-centric behavior.

Recommended cleanup:

- rename comments/docs to emphasize “naming-derived hints” where appropriate,
- audit whether `topic` activity types and topic/consumer storage fields are still required,
- remove dead vocabulary that no longer supports a shipped feature.

### Priority 4 — Align documentation into “current state” vs “target state”

Why it matters:

- the repo already contains both current-state docs and forward-looking PRD material,
- but a first-time reader still has to infer which documents describe today versus tomorrow.

Recommended cleanup:

- keep a short “current runtime boundary” document near the root/docs index,
- keep the PRD as a target-state artifact,
- explicitly cross-link them so readers do not confuse them.

## 6. Evidence Used

- Runtime routing and startup wiring:
  - `app/main.py`
  - `app/container.py`
  - `app/cluster/interface/routers/*.py`
  - `app/schema/interface/routers/*.py`
  - `app/shared/interface/router.py`
- Frontend shipped surface:
  - `frontend/src/App.tsx`
  - `frontend/src/components/layout/Sidebar.tsx`
  - `frontend/src/pages/Connections/index.tsx`
- Explicit product-boundary decisions:
  - `decisions.md`
  - `issues.md`
  - `docs/topic-removal-review.md`
- Future-state / dormant-domain evidence:
  - `docs/features/real-time-data-governance-system.md`
  - `app/product`
  - `app/contract`
  - `app/catalog`
  - `app/lineage`
  - `app/governance`

## 7. Verification Added for This Review

To keep this analysis from drifting, the repository now includes a regression test that checks:

- the active shipped API surface still includes schema governance, connections, audit, and approvals,
- deprecated topic/consumer routes are absent,
- future-state domain routes (product / contract / catalog / lineage) are not accidentally treated as shipped runtime.
