# 🏗️ Architecture Overview

The shipped system is intentionally narrow:

> **Schema Registry connections + schema lifecycle + schema governance**

This repository no longer presents Kafka broker operations, topic management, or broader future-state governance domains as active runtime features.

For the exact runtime boundary, see [Current System Analysis](./current-system-analysis.md).

## High-level shape

```text
Frontend (React)
  ├─ Schemas
  ├─ Schema Detail
  ├─ Schema Policies
  └─ Schema Registry Connections
        ↓
FastAPI API
  ├─ /api/v1/schema-registries/*
  └─ /api/v1/schemas/*
        ↓
Application layer
  ├─ upload / sync / search / detail
  ├─ dry-run / apply
  ├─ history / dashboard
  ├─ delete analysis / delete
  └─ policy management
        ↓
Infrastructure
  ├─ Schema Registry client
  ├─ database repositories
  ├─ MinIO artifact storage
  └─ Redis / shared runtime services
```

## Active backend modules

### `app/registry_connections/`
Despite the folder name, this module now exists only to manage **Schema Registry connections**.

### `app/schema/`
This is the core product module:
- schema upload
- schema sync
- search/detail
- version history
- schema policies
- dry-run / apply
- rollback planning
- delete analysis

### `app/shared/`
Shared runtime support still used by the schema slice:
- DB/session management
- approval workflow support
- audit persistence
- settings / middleware / logging

## Explicitly out of the active runtime

- Kafka broker CRUD/test flows
- topic hints / topic runtime
- consumer or websocket surfaces
- dormant future-state domains (`product`, `contract`, `catalog`, `lineage`, `governance`)

## Design intent

The repository is currently optimized for **one dependable vertical slice** rather than breadth.
The goal is to make schema governance solid before expanding outward into broader data-governance capabilities.
