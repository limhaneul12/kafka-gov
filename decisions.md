# Kafka Governance Control Plane Decisions

- Product boundary fixed to schema governance, connection management, and audit/snapshot collection.
- Frontend surface keeps routed core pages only for dashboard, history, schemas, schema policies, and connections.
- API contract standard is `/api/v1` for HTTP; no active frontend-routed WebSocket surface is considered shipped in this cycle.
- Redis configuration derives from env-driven settings with `REDIS_URL` as the primary source.
- High-risk schema apply operations require `approvalOverride` evidence with reason, approver, and expiry; completed audit snapshots persist both risk assessment and override metadata.
