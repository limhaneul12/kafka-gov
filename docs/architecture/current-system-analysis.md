# Current System Analysis

_Updated after the schema-only cleanup pass._

## Executive summary

The active shipped product is now:

> **Schema Registry–backed schema governance**

The runtime is intentionally limited to:
- Schema Registry connection management
- schema lifecycle operations
- schema governance workflows
- approval/audit support used by schema changes

## Active runtime boundary

### Backend API
Only these surfaces are considered active runtime:
- `/api/v1/schema-registries/*`
- `/api/v1/schemas/*`

### Frontend routes
Only these routes remain in the shipped UI:
- `/schemas`
- `/schemas/:subject`
- `/schemas/policies`
- `/connections`

## Core capabilities

### Schema Registry connections
- create / update / list / activate / delete
- connectivity testing

### Schema lifecycle
- upload
- sync from Schema Registry
- search / detail
- version history
- delete analysis and guarded delete

### Schema governance
- governance dashboard
- compatibility checks
- schema policies
- batch dry-run / apply
- rollback planning
- approval-aware apply flow
- audit/history support

## What was intentionally removed

- Kafka broker CRUD/test flows
- topic hint APIs and topic UI context
- consumer/websocket runtime features
- dormant broader governance domains (`product`, `contract`, `catalog`, `lineage`, `governance`)

## Interpretation

This repository is no longer trying to be a broad Kafka control plane.
It now represents a single dependable vertical slice:

- **Schema Registry** = operational dependency
- **Schema** = primary governed object
- **Approval / audit / history** = governance support primitives

## Remaining residue

A few internal type/enumeration names still reflect earlier broader ambitions, but the main connection package and container naming now point at Schema Registry connections explicitly.
