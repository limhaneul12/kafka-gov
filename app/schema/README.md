# 📦 Schema Module

This module is the core of the current product slice.

It owns:
- schema upload / sync
- schema search / detail / history
- compatibility and governance checks
- dry-run / apply / rollback planning
- schema policy management
- delete analysis / guarded delete

## Structure

```text
schema/
├── domain/models/          # Schema domain models
├── application/use_cases/  # Upload, Sync, Search, Detail, Policy, Apply
├── infrastructure/         # Schema Registry adapter, DB repos, MinIO integration
└── interface/              # REST routers and response/request schemas
```

## Domain events

- `schema.registered` - emitted when a schema registration completes so audit/approval handlers can react
