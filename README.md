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

## 🧭 Onboarding Guide

If you're new to Kafka-Gov, we recommend the following onboarding path.

1. **Choose your mode**
   - Just want to try the UI and features quickly → **Lite Mode (SQLite)**
   - Running a team PoC or a more production-like environment → **Full Stack Mode (Docker + MySQL)**

2. **Prepare your environment**
   - Lite Mode:
     - Install Python 3.12+ and [uv](https://github.com/astral-sh/uv)
     - If you do not set any DB-related values in `.env`, Kafka-Gov will automatically use SQLite
   - Full Stack Mode:
     - Install Docker / Docker Compose
     - Optionally adjust Kafka/Schema Registry settings in `.env` for your environment

3. **Configure the metadata database**
   - Default: when nothing is configured, `sqlite+aiosqlite:///./kafka_gov.db` is used
   - MySQL example:
     ```bash
     KAFKA_GOV_DATABASE_URL=mysql+aiomysql://user:password@mysql:3306/kafka_gov?charset=utf8mb4
     ```
   - PostgreSQL example:
     ```bash
     KAFKA_GOV_DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/kafka_gov
     ```

4. **Run migrations**
   - Alembic always uses `settings.database.url`, so as long as the URL is correct, migrations target the right DB.
   - Local (Lite Mode) example (recommended):
     ```bash
     bash script/migrate.sh
     # or, if executable
     ./script/migrate.sh
     ```
   - Advanced (run Alembic directly):
     ```bash
     uv run alembic upgrade head
     ```
   - In Docker environments, the `migration` service included in `docker-compose.yml` is responsible for running migrations.

5. **Open the UI and register your first connections**
   - Open `http://localhost:8000` in your browser
   - Register Kafka Cluster / Schema Registry connections directly through the UI
   - From then on, all governance metadata is stored in the selected DB (SQLite/MySQL/Postgres)

After onboarding, see [Quick Start](./docs/getting-started/quick-start.md) and
[Configuration](./docs/getting-started/configuration.md) for more details.

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

Kafka-Gov supports **Airflow-style metadata DB switching**.

### 1) Lite Mode (SQLite, no Docker required)

For local development or quick evaluation, Kafka-Gov uses a SQLite file as the metadata store.

```bash
# 1. Clone and setup
git clone https://github.com/limhaneul12/kafka-gov.git
cd kafka-gov
cp .env.example .env

# 2. (optional) If you do not set any DB env vars, SQLite is used by default
#    When KAFKA_GOV_DATABASE_URL is unset, ./kafka_gov.db is created/used automatically

# 3. Install dependencies
uv sync

# 4. Run DB migrations (uses settings.database.url → default SQLite)
bash script/migrate.sh

# 5. Start backend API
uv run uvicorn app.main:app --reload

# 6. (optional) Start frontend (from ./frontend)
# pnpm install
# pnpm dev
```

In this mode, the **local file `./kafka_gov.db`** is used as the metadata database.

### 2) Full Stack Mode (Docker Compose + MySQL)

For production-like setups, use Docker Compose to start MySQL/Kafka/Schema Registry/Redis together.

```bash
# 1. Clone and setup
git clone https://github.com/limhaneul12/kafka-gov.git
cd kafka-gov
cp .env.example .env

# 2. Start all services (includes MySQL-backed metadata DB)
docker-compose up -d

# 3. Access web UI (proxied by nginx)
open http://localhost:8000
```

**That's it!** 🎉

See [Quick Start Guide](./docs/getting-started/quick-start.md) for more details.

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
**Infrastructure:** SQLite (Lite Mode) • MySQL (Production) • Kafka • Schema Registry • MinIO • Kafka Connect

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
