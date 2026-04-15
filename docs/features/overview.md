# ✨ Features Overview

The active product surface is now focused on **schema governance backed by Schema Registry**.

## Core capabilities

### Schema Registry connections
- register Schema Registry endpoints
- activate the currently used registry
- test registry connectivity

### Schema lifecycle
- upload schema files
- sync from Schema Registry
- search/list/detail views
- version history
- guarded delete analysis

### Schema governance
- governance dashboard
- compatibility validation
- schema policies
- change planning / rollback planning
- approval-aware apply flow
- audit/history support

## What is intentionally excluded

- Kafka broker management
- topic management
- topic-hint UI/API
- consumer/websocket runtime features
- dormant higher-level governance domains

## Why the scope is narrow

The repository is being rebuilt around one dependable slice.
Instead of spreading across many half-finished governance concepts, the current system keeps one thing clear:

> **Schemas are the primary managed object, and Schema Registry is the primary external dependency.**

## Where to look next
- [Architecture Overview](../architecture/overview.md)
- [Current System Analysis](../architecture/current-system-analysis.md)
- [Quick Start](../getting-started/quick-start.md)
