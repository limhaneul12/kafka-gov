# 🗺️ Roadmap

## Current focus

The repository is intentionally narrowed to a **schema-governance slice**.
The roadmap therefore prioritizes depth and reliability in that slice over breadth.

## ✅ Completed

- Schema Registry connection management
- Schema upload / sync / detail / search
- Schema governance dashboard
- Schema policies
- Batch dry-run / apply
- Rollback planning
- Approval-aware schema apply flow
- Audit/history persistence for schema changes
- Frontend shell narrowed to schema-focused routes

## 🚧 Next

- Rename legacy internal module names that still imply broader Kafka scope
- Simplify remaining schema request/strategy vocabulary
- Tighten schema approval/audit boundaries inside the backend
- Improve schema policy UX and diagnostics

## 🔮 Later

- Reintroduce broader data-governance capabilities only when they have a clear product boundary
- Re-evaluate higher-order governance objects after the schema slice is stable
