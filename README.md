<div align="center">
  <img src="./image/kafka_gov_logo.png" alt="Kafka Gov Logo" width="300"/>
  
  # 🛡️ Kafka Governance Platform
  
  **Enterprise-grade Kafka management with rich metadata, policy enforcement, and batch operations**
  
  [![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.117.1+-green.svg)](https://fastapi.tiangolo.com)
  [![React](https://img.shields.io/badge/React-19.1-61dafb.svg)](https://react.dev)
  [![Coverage](https://img.shields.io/badge/Coverage-64%25-yellow.svg)](https://github.com/limhaneul12/kafka-gov)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
  
  **"Without knowing who owns a topic and what it's used for, Kafka is just a message queue."**
  
  [🚀 Quick Start](#-quick-start) • [✨ Features](#-features) • [📖 Documentation](#-documentation) • [🗺️ Roadmap](./docs/ROADMAP.md)
</div>

---

## 🌟 What is Kafka-Gov?

Kafka-Gov transforms Kafka from a simple message broker into a **governed enterprise platform** with:

- **🏷️ Rich Metadata**: Owner, team, tags, documentation links for every topic
- **🛡️ Policy Enforcement**: Environment-specific rules (naming, replication, ISR)
- **🚀 Batch Operations**: YAML-based bulk create/update/delete with dry-run
- **📦 Schema Management**: Integrated Schema Registry with auto-correlation
- **📊 Real-time Monitoring**: Consumer lag, fairness index, stuck partition detection
- **📝 Complete Audit Trail**: Track every change (who, when, what, why)

<div align="center">
  <img src="./image/dashboard.png" alt="Dashboard" width="800"/>
</div>

---

## 💡 Why Kafka-Gov?

| Traditional Tools | Kafka-Gov |
|-------------------|-----------|
| ❌ No ownership tracking | ✅ Mandatory owner, team, tags |
| ❌ No policy enforcement | ✅ Environment-specific validation |
| ❌ Manual one-by-one operations | ✅ YAML-based batch operations |
| ❌ No audit trail | ✅ Complete change history |
| ❌ Separate schema tool | ✅ Integrated schema management |

**Problems we solve:**
- 🤔 **Who owns this topic?** → Track ownership across hundreds of topics
- 📝 **What is it for?** → Required documentation links
- ⚠️ **Policy violations?** → Auto-detect risky configs before deployment
- 🚀 **Bulk operations?** → Create 50+ topics in one YAML file
- 🔄 **Change history?** → Complete audit trail with before/after snapshots

---

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/limhaneul12/kafka-gov.git
cd kafka-gov
cp .env.example .env

# 2. Start all services
docker-compose up -d

# 3. Access web UI
open http://localhost:8000
```

**That's it!** 🎉

See [Quick Start Guide](./docs/getting-started/quick-start.md) for detailed instructions.

---

## ✨ Features

### 🏷️ Rich Topic Metadata

Every topic includes owner, team, documentation URL, and custom tags:

```yaml
name: prod.orders.created
metadata:
  owner: team-commerce
  doc: "https://wiki.company.com/orders"
  tags: ["orders", "critical", "pii"]
```

### 🚀 YAML-Based Batch Operations

Create dozens of topics at once:

```yaml
kind: TopicBatch
env: prod
items:
  - name: prod.orders.created
    action: create
    config:
      partitions: 12
      replication_factor: 3
```

Upload → Review dry-run → Apply changes

<div align="center">
  <img src="./image/create_topic.png" alt="Batch Operations" width="700"/>
</div>

### 🛡️ Policy Enforcement

Environment-specific rules prevent production incidents:

| Policy | DEV | PROD |
|--------|-----|------|
| Min Replication | ≥ 1 | ≥ 3 ⚠️ |
| Min ISR | ≥ 1 | ≥ 2 ⚠️ |
| 'tmp' prefix | ✅ | 🚫 |

### 📊 Real-time Monitoring

- **Consumer lag tracking** with p50/p95/max metrics
- **Fairness index** (Gini coefficient) for partition distribution
- **Stuck partition detection** with configurable thresholds
- **Rebalance stability** scoring with time windows
- **WebSocket streaming** for live updates

<div align="center">
  <img src="./image/consumer_list.png" alt="Monitoring" width="700"/>
</div>

### 📦 More Features

- [Schema Registry Management](./docs/features/schema-registry.md)
- [Kafka Connect Integration](./docs/features/kafka-connect.md)
- [Multi-Cluster Support](./docs/features/multi-cluster.md)
- [Team Analytics](./docs/features/team-analytics.md)
- [Complete Audit Trail](./docs/operations/audit-trail.md)

---

## 📖 Documentation

### Getting Started
- [🚀 Quick Start](./docs/getting-started/quick-start.md)
- [📦 Installation Guide](./docs/getting-started/installation.md)
- [⚙️ Configuration](./docs/getting-started/configuration.md)

### Features
- [📊 Topic Management](./docs/features/topic-management.md)
- [🚀 Batch Operations](./docs/features/batch-operations.md)
- [🛡️ Policy Enforcement](./docs/features/policy-enforcement.md)
- [📦 Schema Registry](./docs/features/schema-registry.md)
- [📈 Real-time Monitoring](./docs/features/monitoring.md)
- [📚 All Features](./docs/features/overview.md)

### Architecture & API
- [🏗️ Architecture Overview](./docs/architecture/overview.md)
- [🔌 API Reference](./docs/api/)
- [🔐 Security](./docs/architecture/security.md)

### Operations
- [🚀 Deployment Guide](./docs/operations/deployment.md)
- [📊 Monitoring](./docs/operations/monitoring.md)
- [🔧 Troubleshooting](./docs/operations/troubleshooting.md)

---

## 🛠️ Tech Stack

**Backend:** Python 3.12+ • FastAPI • Pydantic v2 • SQLAlchemy 2.0 • Confluent Kafka  
**Frontend:** React 19 • TypeScript • TailwindCSS • Rolldown  
**Infrastructure:** MySQL • Kafka • Schema Registry • MinIO • Kafka Connect

---

## 🗺️ Roadmap

**v1.0 (Current):**
- ✅ Core governance features
- ✅ Real-time monitoring
- ✅ Policy enforcement

**v1.1 (In Progress):**
- 🔄 Enhanced frontend filters
- 🔄 Preset management UI
- 🔄 Kafka Connect UI

**v2.0 (Planned):**
- 📅 RBAC & multi-tenancy
- 📅 Prometheus/Grafana integration
- 📅 GitOps integration

[View Full Roadmap](./docs/ROADMAP.md)

---

## 🤝 Contributing

Contributions welcome! Please read our [Contributing Guide](./CONTRIBUTING.md) before submitting PRs.

```bash
# Setup development environment
uv sync
uv run pytest --cov=app

# Code standards
uv run ruff check app/
uv run ruff format app/
```

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

---

<div align="center">
  
**Make Kafka safer and more efficient** 🚀

Made with ❤️ by developers, for developers

⭐ **Star if you find this useful!** ⭐

</div>
