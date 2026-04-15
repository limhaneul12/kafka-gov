# Current System Analysis (2026-04-15)

This note captures the **actual shipped/runtime surface** of the repository as of 2026-04-15 and separates it from **legacy Kafka remnants** and **future governance-direction code** that is present in-tree but not wired into the running product.

## Executive Summary

- The **active product** is currently a **schema-governance control plane** built around three wired backend areas: **cluster connections**, **schema workflows**, and **shared audit/approval services**.
- **Kafka topic management is no longer a first-class runtime feature**. Topic semantics survive only as **read-only, naming-derived hints** for schema impact and UI context.
- **Kafka broker connection management still remains active** as supporting infrastructure. The shipped UI still exposes Kafka broker CRUD/test/activate flows, and the dashboard still counts active clusters.
- The repo also contains a **next-wave governance model** (`product`, `contract`, `lineage`, `catalog`, standalone `governance`) that is **not currently wired into FastAPI or the frontend shell**.
- The biggest source of confusion for a new team is that the repo mixes **current runtime code**, **removed/placeholder surfaces**, and **future-state modules/docs** in the same tree.

## 1. What is actually running today

### 1.1 Backend runtime boundary

The FastAPI app wires only the following runtime modules:

- `app/main.py` — includes only:
  - `app.shared.interface.router`
  - `app.cluster.interface.router`
  - `app.schema.interface.router`
  - `app.schema.interface.routers.policy_router`
- `app/container.py` — creates only:
  - `InfrastructureContainer`
  - `ClusterContainer`
  - `SchemaContainer`

**Implication:** the currently shipped backend is centered on:

1. **connection management** (`cluster`)
2. **schema management + schema governance** (`schema`)
3. **audit + approval shared services** (`shared`)

### 1.2 Active API surface

Evidence from router decorators under `app/cluster/interface/routers`, `app/schema/interface/routers`, and `app/shared/interface/router.py` shows the active surface is:

- **Kafka broker connections**
  - `app/cluster/interface/routers/broker.py`
  - CRUD / activate / connection test under `/api/v1/clusters/brokers`
- **Schema Registry connections**
  - `app/cluster/interface/routers/registry.py`
  - CRUD / activate / connection test under `/api/v1/clusters/schema-registries`
- **Schema management**
  - `app/schema/interface/routers/management_router.py`
  - upload, sync, delete analysis, delete, artifact listing, detail, search
- **Schema governance**
  - `app/schema/interface/routers/governance_router.py`
  - governance dashboard, schema history, known topic names, plan change, rollback plan
- **Schema policy management**
  - `app/schema/interface/routers/policy_router.py`
- **Audit + approval workflows**
  - `app/shared/interface/router.py`
  - recent audit, history, approval request CRUD/decision endpoints

### 1.3 Frontend runtime boundary

The active routed shell is narrow and matches the backend above:

- `frontend/src/App.tsx`
  - `/governance/dashboard`
  - `/history`
  - `/schemas`
  - `/schemas/:subject`
  - `/connections`
  - `/schemas/policies`
- `frontend/src/components/layout/Sidebar.tsx`
  - only shows **Schema Registry**, **Dashboard**, **History**, **Schema Policies**, **Connections**

**Implication:** the user-facing product is no longer a topic/consumer UI. It is a schema-centric governance shell with connection management.

## 2. Current core functionality

### 2.1 Schema Registry is the center of gravity

The schema module remains the most feature-rich and product-defining area:

- `app/schema/interface/routers/management_router.py`
  - schema upload
  - sync from Schema Registry
  - delete analysis and guarded delete
  - artifact listing / detail / search
- `app/schema/interface/routers/batch_router.py`
  - dry-run planning
  - apply with `approval_override`
  - saved plan lookup
- `app/schema/interface/routers/governance_router.py`
  - governance dashboard
  - schema history
  - change planning / rollback planning
- `app/schema/domain/policies/policy_pack.py`
  - schema-focused rules around compatibility, metadata, required defaults, type changes, enum narrowing

This is consistent with the project direction stated in:

- `README.md`
- `decisions.md`
- `issues.md`

### 2.2 Audit / approval is already part of the shipped control plane

The shared module is not just plumbing; it provides active governance behavior:

- `app/shared/interface/router.py`
  - audit history/recent activity endpoints
  - approval request creation/list/get/approve/reject
- `tests/test_shared_approval_requests.py`
  - shows approval requests are persisted and surfaced through activity history

This means the current system is already more than “Schema Registry CRUD”; it is a **schema-governance workflow system** with approval-aware change control.

### 2.3 Kafka is still present, but mostly as infrastructure

Kafka is not gone. It remains active in two ways:

1. **Connection/infrastructure management**
   - `app/cluster/interface/routers/broker.py`
   - `app/infra/kafka/connection_manager.py`
   - `frontend/src/pages/Connections/index.tsx`
   - `frontend/src/services/api.ts`
2. **Dashboard/operational context**
   - `frontend/src/pages/governance/Dashboard.tsx`
   - still fetches `clustersAPI.listKafka()` and displays **Active Clusters**

So the runtime is **not Kafka-free**; it is **Kafka-de-emphasized**.

## 3. What remains of topic functionality

### 3.1 Topic handling is intentionally downgraded to hints

The strongest evidence is:

- `docs/topic-removal-review.md`
  - explicitly states no active `app/topic` runtime surface remains
  - explicitly states `/topics`, `/consumers`, `/ws` are gone from the shipped frontend
  - defines `/api/v1/schemas/known-topics/{subject}` as the remaining read-only surface
- `app/schema/application/use_cases/governance/impact.py`
  - `GetKnownTopicNamesUseCase` derives topic names from subject naming only
  - ignores runtime lookup and simply derives names
- `app/schema/domain/services.py`
  - `SchemaImpactAnalyzer` and `SchemaDeleteAnalyzer` use naming-derived topic extraction
  - warnings explicitly say actual usage still requires separate verification
- `app/schema/interface/routers/governance_router.py`
  - exposes `/v1/schemas/known-topics/{subject}` as a read-only endpoint
- `tests/test_schema_known_topic_names.py`
  - verifies topic names are flat naming-derived results
  - verifies the policy pack no longer emits old topic-link rules
- `tests/test_e2e_full_system.py`
  - verifies `Topics`, `Policies`, and `Consumers` links are absent from the shell
  - verifies `Total Topics` / `Live Brokers` style old dashboard metrics are absent

### 3.2 What this means architecturally

The system still acknowledges the **schema ↔ topic relationship**, but only as:

- naming-derived impact hints
- delete warnings
- operator context

It does **not** currently present topics as a managed runtime domain.

## 4. Legacy / mixed-state remnants still in the repo

These are the main sources of confusion for a new team.

### 4.1 Dormant future-state backend modules exist but are not wired

Present in-tree:

- `app/product/`
- `app/contract/`
- `app/lineage/`
- `app/catalog/`
- `app/governance/`

But they are **not registered in**:

- `app/main.py`
- `app/container.py`

So these directories currently read like **target-state/domain expansion work**, not active product surface.

This matches the target-state PRD in:

- `docs/features/real-time-data-governance-system.md`

That document clearly describes movement toward **Product / Contract / Lineage** governance, but the runtime has not caught up yet.

### 4.2 Frontend still contains orphaned or placeholder pages/components

Examples:

- unrouted pages
  - `frontend/src/pages/Analysis.tsx`
  - `frontend/src/pages/Connect.tsx`
  - `frontend/src/pages/Settings.tsx`
  - `frontend/src/pages/Schemas.tsx`
- placeholder / deprecated components
  - `frontend/src/pages/Connections/components/KafkaConnectList.tsx`
  - `frontend/src/pages/Connections/components/StorageList.tsx`
- debug-noisy legacy modal
  - `frontend/src/components/connection/EditConnectionModal.tsx`
    - contains multiple `console.log` / `console.error` statements
- duplicated frontend types
  - `frontend/src/types/index.ts`
  - `frontend/src/pages/Connections/Connections.types.ts`

These files are not part of the routed shell in `frontend/src/App.tsx`, but they remain in the repo and make the frontend feel larger/more active than the actual shipped experience.

### 4.3 Documentation mixes current state and future direction

There are three different documentation layers in the repo:

1. **current shipped direction**
   - `README.md`
   - `decisions.md`
   - `issues.md`
   - `docs/topic-removal-review.md`
2. **current runtime architecture docs**
   - `docs/architecture/overview.md`
3. **future-state product direction / PRD**
   - `docs/features/real-time-data-governance-system.md`

This is valuable, but for a first-time team it also blurs the line between:

- what ships now,
- what was intentionally removed,
- and what is only planned.

## 5. Recommended cleanup priorities

### Priority 1 — Decide the exact product boundary for Kafka broker management

**Why:** Kafka broker CRUD is still active even though topic operations were intentionally removed.

**Evidence**
- `app/cluster/interface/routers/broker.py`
- `app/infra/kafka/connection_manager.py`
- `frontend/src/pages/Connections/index.tsx`
- `frontend/src/pages/governance/Dashboard.tsx`
- `frontend/src/services/api.ts`

**Decision to make**
- If Kafka broker connection management is still a first-class capability, document it clearly as supporting infrastructure.
- If not, demote/hide it and keep only the minimum needed for schema governance flows.

### Priority 2 — Separate shipped runtime from future-state modules

**Why:** `product`, `contract`, `lineage`, `catalog`, and standalone `governance` modules strongly suggest a richer platform than what `app/main.py` actually exposes.

**Evidence**
- present: `app/product/`, `app/contract/`, `app/lineage/`, `app/catalog/`, `app/governance/`
- absent from wiring: `app/main.py`, `app/container.py`

**Recommendation**
- Either mark these directories as experimental/staged, or move their design notes into clearer target-state documentation.

### Priority 3 — Remove or quarantine unrouted frontend surfaces

**Why:** dead pages/components raise onboarding cost and make it harder to see the real product shell.

**Evidence**
- unrouted: `frontend/src/pages/Analysis.tsx`, `Connect.tsx`, `Settings.tsx`, `Schemas.tsx`
- placeholders: `KafkaConnectList.tsx`, `StorageList.tsx`
- debug-heavy legacy modal: `frontend/src/components/connection/EditConnectionModal.tsx`

**Recommendation**
- delete dead files if truly obsolete, or move them to an explicit experimental/staging area.

### Priority 4 — Keep topic semantics read-only until real lineage exists

**Why:** the repo already made a deliberate choice to avoid pretending it has authoritative topic runtime knowledge.

**Evidence**
- `docs/topic-removal-review.md`
- `app/schema/application/use_cases/governance/impact.py`
- `app/schema/domain/services.py`
- `tests/test_schema_known_topic_names.py`

**Recommendation**
- preserve the current “hint only / non-authoritative” stance until actual lineage/runtime evidence is implemented.
- avoid reintroducing topic management accidentally via policy rules or UI drift.

### Priority 5 — Tighten documentation around “current state” vs “target state”

**Why:** this repo already contains both the current control plane and the next governance architecture, but the distinction is not obvious to newcomers.

**Evidence**
- `README.md`
- `docs/architecture/overview.md`
- `docs/features/real-time-data-governance-system.md`

**Recommendation**
- maintain a short “current shipped surface” doc and keep the PRD clearly labeled as target-state.

## 6. Bottom line

For a new team, the simplest accurate mental model is:

> **Kafka-Gov is currently a schema-governance control plane with Kafka/Schema Registry connection management, approval/audit workflows, and read-only topic-name hints.**
>
> It is **not** currently a full topic-management platform, and it has **not yet** promoted Product / Contract / Lineage / Catalog into the wired runtime surface.

That framing best matches the code that is actually wired today.
