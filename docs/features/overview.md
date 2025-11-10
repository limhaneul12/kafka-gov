# ✨ Features Overview

Comprehensive guide to Kafka-Gov's capabilities.

## 🌟 What Makes Kafka-Gov Special?

### 🎯 Built for Governance, Not Just Monitoring

Unlike traditional Kafka UI tools that focus on *viewing* data, Kafka-Gov is designed for **enterprise governance** with metadata-first approach, policy enforcement, and operational excellence.

| Traditional Tools (Kafka-UI, AKHQ, Conduktor) | Kafka-Gov |
|-----------------------------------------------|-----------|
| ❌ No ownership tracking | ✅ Mandatory owner, team, tags |
| ❌ No policy enforcement | ✅ Environment-specific validation |
| ❌ Manual one-by-one operations | ✅ YAML-based batch operations |
| ❌ No audit trail | ✅ Complete change history |
| ❌ Schema Registry as separate tool | ✅ Integrated schema management |
| ❌ Static configuration | ✅ Dynamic cluster switching |
| ❌ Single cluster focus | ✅ Multi-cluster management |

---

## 💡 Why Kafka-Gov?

### The Problem

Existing Kafka UI tools (Kafka-UI, Conduktor, AKHQ) lack critical metadata capabilities:

- **🤔 Who owns this topic?** No ownership tracking across hundreds of topics
- **📝 What is it for?** Topic names alone don't explain purpose
- **📚 Where's the docs?** Documentation scattered across wikis and READMs
- **🔄 Change history?** No audit trail for partition changes or config updates
- **⚠️ Policy violations?** Can't detect risky configs like `min.insync.replicas=1` in production
- **🚀 Batch operations?** Manual one-by-one topic creation for new projects

### The Solution

Kafka-Gov transforms Kafka into a **governed enterprise platform**:

| Problem | Solution |
|---------|----------|
| 🔍 Unknown ownership | Mandatory `owner`, `team`, `tags` metadata |
| 📖 Missing documentation | Direct Wiki/Confluence URL linking |
| 🚫 No policies | Environment-specific validation (naming, replication, ISR) |
| ⏱️ No audit trail | Automatic logging (who, when, what, why) |
| 🐌 Manual operations | YAML-based batch create/update/delete |
| 🔗 Topic-Schema gap | Automatic correlation and impact analysis |

---

## 🎯 Features at a Glance

<table>
<tr>
<td width="33%">

### 🏷️ Rich Metadata
- Owner & Team tracking
- Documentation links
- Custom tags
- Environment labels

</td>
<td width="33%">

### 🚀 Batch Operations
- YAML-based bulk actions
- Dry-run preview
- Policy validation
- Parallel processing

</td>
<td width="33%">

### 🛡️ Policy Enforcement
- Environment-specific rules
- Version management
- Naming conventions
- Config validation

</td>
</tr>
<tr>
<td width="33%">

### 🔌 Multi-Cluster
- Dynamic cluster switching
- SASL/SSL support
- Connection pooling
- Health monitoring

</td>
<td width="33%">

### 📦 Schema Registry
- Auto schema sync
- Compatibility modes
- MinIO artifact storage
- Topic correlation

</td>
<td width="33%">

### 📊 Audit Trail
- Complete change history
- Before/after snapshots
- User attribution
- Deployment linking

</td>
</tr>
</table>

---

## 📊 Dashboard Overview

Monitor your Kafka ecosystem at a glance with real-time metrics and health status.

<div align="center">
  <img src="../../image/dashboard.png" alt="Kafka Gov Dashboard" width="800"/>
  <p><em>Unified dashboard showing total topics, schemas, correlations, and cluster health</em></p>
</div>

**Dashboard Metrics:**
- 📈 **Total Topics**: Number of managed topics across all clusters
- 📦 **Registered Schemas**: Schema Registry integration status
- 🔗 **Correlations**: Auto-linked topic-schema relationships
- 💚 **Health Status**: Real-time cluster connectivity monitoring

---

## 📚 Feature Categories

### Core Management
- [Topic Management](./topic-management.md)
- [Batch Operations](./batch-operations.md)
- [Schema Registry](./schema-registry.md)
- [Kafka Connect](./kafka-connect.md)

### Governance & Policy
- [Policy Enforcement](./policy-enforcement.md)
- [Naming Conventions](./naming-policy.md)
- [Audit Trail](../operations/audit-trail.md)

### Monitoring & Analytics
- [Real-time Monitoring](./monitoring.md)
- [Consumer Analytics](./consumer-analytics.md)
- [Team Analytics](./team-analytics.md)

### Infrastructure
- [Multi-Cluster Management](./multi-cluster.md)
- [Security & Authentication](../architecture/security.md)

---

## 🔄 Latest Updates (2025-11)

- **Topic Detail Live Metrics**: Real-time partition details on page load
- **Initial Snapshot Automation**: Auto-sync on first cluster registration
- **Sidebar Refresh & Incident Policy UI**: Improved navigation and policy preview
- **Consumer Group Monitoring**: Fairness index, stuck partition detection, rebalance scoring
- **WebSocket Streaming**: Real-time lag updates for consumer groups

---

## Next Steps

1. **Get Started**: [Quick Start Guide](../getting-started/quick-start.md)
2. **Learn Features**: Browse feature-specific guides above
3. **Understand Architecture**: [Architecture Overview](../architecture/overview.md)
4. **API Reference**: [API Documentation](../api/)
