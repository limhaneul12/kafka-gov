# 🚀 YAML-Based Batch Operations

Create, update, and delete dozens of topics at once with YAML manifests.

## Overview

Batch operations allow you to:
- **Create multiple topics** in one transaction
- **Update configurations** across many topics simultaneously
- **Delete deprecated topics** in bulk
- **Preview changes** with dry-run before applying
- **Validate policies** automatically before execution

---

## YAML Structure

### Basic Template

```yaml
kind: TopicBatch
env: prod                          # Target environment: dev, stg, prod
change_id: "2025-01-15_my-project" # Unique identifier for tracking
items:
  - name: prod.orders.created
    action: create                  # create, alter, or delete
    config:
      partitions: 12
      replication_factor: 3
      retention_ms: 604800000       # 7 days
      min_insync_replicas: 2
    metadata:
      owner: team-commerce
      doc: "https://wiki.company.com/orders"
      tags: ["orders", "critical"]
```

---

## Actions

### Create Topics

```yaml
kind: TopicBatch
env: prod
change_id: "2025-01-15_new-service"
items:
  - name: prod.users.registered
    action: create
    config:
      partitions: 6
      replication_factor: 3
      min_insync_replicas: 2
      retention_ms: 2592000000  # 30 days
    metadata:
      owner: team-users
      doc: "https://wiki.company.com/users"
      tags: ["users", "pii"]
      
  - name: prod.users.deleted
    action: create
    config:
      partitions: 3
      replication_factor: 3
      min_insync_replicas: 2
      retention_ms: 7776000000  # 90 days (compliance)
    metadata:
      owner: team-users
      doc: "https://wiki.company.com/users"
      tags: ["users", "pii", "audit"]
```

### Update Topics

```yaml
kind: TopicBatch
env: prod
change_id: "2025-01-16_scale-up"
items:
  - name: prod.orders.created
    action: alter
    config:
      partitions: 24              # Increase partitions (irreversible!)
      retention_ms: 1209600000    # Change retention to 14 days
```

### Delete Topics

```yaml
kind: TopicBatch
env: dev
change_id: "2025-01-17_cleanup"
items:
  - name: dev.test.old-topic
    action: delete
    
  - name: dev.test.deprecated
    action: delete
```

---

## Dry-Run Workflow

<div align="center">
  <img src="../../image/batch_result.png" alt="Batch Processing Result" width="800"/>
</div>

### Step 1: Upload YAML

**Via Web UI:**
1. Navigate to Topics → Batch Operations
2. Click "Upload YAML"
3. Select your YAML file
4. View dry-run results

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/v1/topics/batch/upload" \
  -F "file=@my-topics.yml"
```

### Step 2: Review Dry-Run Results

Dry-run checks:
- ✅ **Syntax validation**: YAML format
- ✅ **Policy compliance**: Naming, replication, ISR
- ✅ **Duplicate detection**: Name conflicts
- ✅ **Permissions**: Cluster access
- ⚠️ **Warnings**: Non-blocking issues

Example output:
```json
{
  "dry_run": true,
  "summary": {
    "total": 5,
    "create": 3,
    "alter": 1,
    "delete": 1,
    "errors": 1
  },
  "results": [
    {
      "name": "prod.orders.created",
      "action": "create",
      "status": "success",
      "message": "Topic will be created"
    },
    {
      "name": "prod.tmp.test",
      "action": "create",
      "status": "error",
      "message": "'tmp' prefix forbidden in prod environment"
    }
  ]
}
```

### Step 3: Apply Changes

If dry-run passes, click "Apply" or call apply endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/topics/batch/apply" \
  -H "Content-Type: application/json" \
  -d '{
    "change_id": "2025-01-15_my-project",
    "items": [...]
  }'
```

---

## Policy Validation

Batch operations automatically enforce environment-specific policies:

| Policy Check | DEV | STG | PROD |
|--------------|-----|-----|------|
| **Min Replication Factor** | ≥ 1 | ≥ 2 | ≥ 3 |
| **Min ISR** | ≥ 1 | ≥ 2 | ≥ 2 |
| **Naming Convention** | `dev.*` | `stg.*` | `prod.*` |
| **'tmp' prefix** | ✅ Allowed | ⚠️ Warning | 🚫 Blocked |
| **Mandatory Metadata** | owner | owner, doc | owner, doc, tags |

**Policy violations block execution:**
```
❌ [ERROR] prod.tmp.test: 'tmp' prefix forbidden in prod
❌ [ERROR] prod.orders: min.insync.replicas must be >= 2 (current: 1)
❌ [ERROR] stg.invalid: Topic name must match pattern: stg.{domain}.{resource}
```

See [Policy Enforcement Guide](./policy-enforcement.md) for detailed rules.

---

## Advanced Features

### Parallel Processing

Batch operations are processed in parallel for speed:
- **Create**: All topics created concurrently
- **Alter**: Configurations updated in parallel
- **Delete**: Deletions executed simultaneously

### Transaction Boundaries

- Each action (create/alter/delete) is atomic
- Failures are isolated (one failure doesn't block others)
- Audit logs record each action individually

### Change ID Tracking

Use `change_id` to link batch operations to:
- Deployment tickets (Jira, GitHub Issues)
- Git commits
- Sprint milestones

```yaml
change_id: "JIRA-1234_add-payment-topics"
# or
change_id: "git-commit-abc123"
# or
change_id: "2025-Q1-sprint-3"
```

---

## Best Practices

### Organize by Environment

Keep separate YAML files per environment:
```
topics/
├── dev-topics.yml
├── stg-topics.yml
└── prod-topics.yml
```

### Version Control

Store YAML files in Git:
```bash
git add topics/*.yml
git commit -m "feat: Add payment service topics"
git push
```

### Incremental Changes

Don't mix create/alter/delete in one batch:
```yaml
# Good: Focused batch
kind: TopicBatch
env: prod
change_id: "2025-01-15_create-payment-topics"
items:
  - name: prod.payments.created
    action: create
    ...

# Better: Separate batches for different actions
```

### Test in DEV First

Always test batch operations in DEV before PROD:
```bash
# 1. Test in DEV
curl -X POST ".../batch/upload" -F "file=@dev-topics.yml"

# 2. Verify in DEV environment

# 3. Promote to PROD with modified YAML
curl -X POST ".../batch/upload" -F "file=@prod-topics.yml"
```

---

## Examples

### Example 1: New Microservice

Complete topic setup for a new service:

```yaml
kind: TopicBatch
env: prod
change_id: "2025-01-15_payment-service-launch"
items:
  - name: prod.payments.initiated
    action: create
    config:
      partitions: 12
      replication_factor: 3
      min_insync_replicas: 2
      retention_ms: 2592000000
    metadata:
      owner: team-payments
      doc: "https://wiki.company.com/payments/initiated"
      tags: ["payments", "critical", "pii"]
      
  - name: prod.payments.completed
    action: create
    config:
      partitions: 12
      replication_factor: 3
      min_insync_replicas: 2
      retention_ms: 7776000000  # 90 days for audit
    metadata:
      owner: team-payments
      doc: "https://wiki.company.com/payments/completed"
      tags: ["payments", "critical", "pii", "audit"]
      
  - name: prod.payments.failed
    action: create
    config:
      partitions: 6
      replication_factor: 3
      min_insync_replicas: 2
      retention_ms: 7776000000
    metadata:
      owner: team-payments
      doc: "https://wiki.company.com/payments/failed"
      tags: ["payments", "critical"]
```

### Example 2: Scale Up Partitions

Increase capacity for high-traffic topics:

```yaml
kind: TopicBatch
env: prod
change_id: "2025-01-20_scale-up-black-friday"
items:
  - name: prod.orders.created
    action: alter
    config:
      partitions: 48  # Double capacity
      
  - name: prod.checkout.completed
    action: alter
    config:
      partitions: 36
      
  - name: prod.inventory.updated
    action: alter
    config:
      partitions: 24
```

### Example 3: Cleanup Deprecated Topics

Remove old topics:

```yaml
kind: TopicBatch
env: dev
change_id: "2025-01-25_cleanup-old-topics"
items:
  - name: dev.test.experiment-2024-q3
    action: delete
    
  - name: dev.deprecated.old-service
    action: delete
    
  - name: dev.tmp.load-test
    action: delete
```

---

## Troubleshooting

### YAML syntax errors
**Error**: `Invalid YAML format`
**Solution**: Validate YAML with online tools or `yamllint`

### Policy violations
**Error**: `Topic name must start with 'prod.'`
**Solution**: Check active policy for environment

### Partition decrease attempt
**Error**: `Cannot decrease partitions`
**Solution**: Kafka doesn't allow partition reduction. Create new topic instead.

### Insufficient replicas
**Error**: `Not enough brokers for replication_factor=3`
**Solution**: Reduce replication factor or add more brokers

---

## Related Documentation

- [Topic Management](./topic-management.md)
- [Policy Enforcement](./policy-enforcement.md)
- [Naming Conventions](./naming-policy.md)
- [API Reference](../api/topics.md)
