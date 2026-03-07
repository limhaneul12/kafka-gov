# Kafka Governance Control Plane Decisions

- Product boundary fixed to Kafka governance control-plane capabilities only: connections, topic governance, schema governance, consumer governance signals, and audit/snapshot collection.
- Frontend surface keeps routed core pages only and restores consumer governance routes as first-class product paths.
- API contract standard is `/api/v1` for HTTP and `/ws` for WebSocket endpoints; remaining legacy non-`/api/v1` paths are normalized in this cycle.
- Redis and Celery configuration now derive from env-driven settings with `REDIS_URL` as the primary source and Celery-specific overrides optional.
- High-risk topic/schema apply operations require `approvalOverride` evidence with reason, approver, and expiry; completed audit snapshots persist both risk assessment and override metadata.
