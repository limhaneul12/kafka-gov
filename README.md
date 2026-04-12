<div align="center">
  <img src="./image/kafka_gov_logo.png" alt="Kafka Gov Logo" width="300"/>
  
  # 🛡️ Kafka-Gov
  
  **Schema-centric governance workflows with policy controls, audit history, and operational visibility**
  
  [![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.117.1+-green.svg)](https://fastapi.tiangolo.com)
  [![React](https://img.shields.io/badge/React-19.1-61dafb.svg)](https://react.dev)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
  
  **"Without clear schema ownership, compatibility rules, and audit history, real-time data is just traffic."**
  
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
   - In Docker Compose, the `app` service runs `bash script/migrate.sh` before starting FastAPI.

5. **Open the UI and register your first connections**
   - Lite Mode: run the frontend dev server and open `http://localhost:3000`
   - Full Stack Mode (Docker Compose): open `http://localhost:90`
   - Backend API docs are available at `http://localhost:8000/swagger` in non-production local runs
   - Register Kafka Cluster / Schema Registry connections directly through the UI
   - From then on, all governance metadata is stored in the selected DB (SQLite/MySQL/Postgres)

After onboarding, see [Quick Start](./docs/getting-started/quick-start.md) and
[Configuration](./docs/getting-started/configuration.md) for more details.

---

## 🌟 What is Kafka-Gov?

Kafka-Gov transforms schema operations from ad hoc registry usage into a **governed enterprise platform** with:

- **🛡️ Policy Enforcement**: Environment-specific schema governance rules and approvals
- **📦 Schema Management**: Integrated Schema Registry with versioning and compatibility workflows
- **🧭 Naming-Derived Traceability**: Read-only schema hints for related topic names
- **📊 Operational Visibility**: Governance dashboards, audit history, and connection health
- **📝 Complete Audit Trail**: Track every change (who, when, what, why)

<div align="center">
  <img src="./image/dashboard.png" alt="Dashboard" width="800"/>
</div>

---

## 💡 Why Kafka-Gov?

| Traditional Tools | Kafka-Gov |
|-------------------|-----------|
| ❌ No ownership tracking | ✅ Mandatory schema metadata and audit context |
| ❌ No policy enforcement | ✅ Environment-specific schema validation |
| ❌ Poor schema visibility | ✅ Versioned schema governance |
| ❌ No audit trail | ✅ Complete change history |
| ❌ Separate schema tool | ✅ Integrated schema management |

 **Problems we solve:**
 - 📦 **Which schema is live?** → Track version history and compatibility state
 - ⚠️ **Policy violations?** → Auto-detect risky changes before deployment
 - 🧭 **Where might this schema belong?** → Derive likely topic names from naming strategy
 - 🔄 **Change history?** → Complete audit trail with before/after snapshots

### 프로젝트 방향성

Although we initially approached this project from a governance perspective, over time it started to drift toward operational concerns. To realign with its original direction — governance — we are refocusing on **schema governance**, **approval-aware change control**, and **scenario-based policy alerts** as the core of the project.

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

# 6. (optional) Start frontend UI (from ./frontend)
# npm install
# npm run dev
```

In this mode, the **local file `./kafka_gov.db`** is used as the metadata database.
Open the backend API docs at `http://localhost:8000/swagger`.
If you also start the frontend dev server, the web UI is available at `http://localhost:3000`.

### 2) Full Stack Mode (Docker Compose)

For production-like setups, use Docker Compose to start the app, frontend, nginx, and Redis together. The compose stack expects Kafka and Schema Registry to be available on the external `kafka-network`, and the metadata DB defaults to SQLite inside the app container unless you override `KAFKA_GOV_DATABASE_URL`.

```bash
# 1. Clone and setup
git clone https://github.com/limhaneul12/kafka-gov.git
cd kafka-gov
cp .env.example .env

# 2. Start the shipped compose services
docker-compose up -d

# 3. Access web UI (proxied by nginx)
open http://localhost:90
```

**That's it!** 🎉

See [Quick Start Guide](./docs/getting-started/quick-start.md) for more details.

---

## ✨ Features

### 📦 Schema Governance

Track schema versions, compatibility, and policy quality through a single workflow:

```json
{
  "subject": "prod.orders-value",
  "compatibility": "BACKWARD",
  "version": 7
}
```

Upload → Review governance checks → Apply the next schema version

### 🛡️ Policy Enforcement

Environment-specific rules prevent production incidents:

| Policy | DEV | PROD |
|--------|-----|------|
| Missing `metadata.doc` | Warn | Approval Required |
| `compatibility: NONE` | Approval Required | Rejected |
| Breaking field type change | Rejected | Rejected |

### 🛡️ Schema Governance

Advanced schema quality control and life-cycle management to ensure data consistency across the enterprise:

- **📊 Governance Dashboard**: Real-time health scoring for every schema. Scores are calculated based on compatibility levels, documentation coverage, and compliance with organizational linting rules.
- **🛡️ Custom Guardrails (Policies)**: Define and enforce your own linting rules (e.g., mandatory 'doc' fields, naming conventions) and environment-specific compliance policies to prevent breaking changes.
- **🕒 Schema Time Machine**: Access the complete history of every schema version. Track who changed what and when, with automated rollback plans to quickly revert to a stable state.
- **🧭 Known Topic Names**: Read-only naming-derived hints that help operators understand where a schema may belong without claiming verified runtime usage.

<div align="center">
  <img src="./image/schema_linting.png" alt="Schema Linting & Violations" width="750"/>
  <p><i>Real-time Schema Linting and Policy Violation Detection</i></p>
</div>

### 📊 Operational Visibility

- **Governance dashboard** for schema and cluster health
- **Approval-aware audit history** for changes and overrides
- **Connection health visibility** for active broker and registry endpoints
- **Naming-derived traceability** surfaced where schema context matters

<div align="center">
  <img src="./image/dashboard.png" alt="Monitoring" width="700"/>
</div>

### 📦 More Features

- [Features Overview](./docs/features/overview.md)
- [Product Direction](./docs/features/real-time-data-governance-system.md)

---

## 📖 Documentation

### Getting Started
- [🚀 Quick Start](./docs/getting-started/quick-start.md)
- [📦 Installation Guide](./docs/getting-started/installation.md)
- [⚙️ Configuration](./docs/getting-started/configuration.md)

### Features
- [🧭 Product Direction](./docs/features/real-time-data-governance-system.md)
- [📚 All Features](./docs/features/overview.md)

### Architecture & API
- [🏗️ Architecture Overview](./docs/architecture/overview.md)
- [🔌 API Docs](/openapi.json)

### Operations
- [🚀 Deployment Guide](./docs/operations/deployment.md)

---

## 🛠️ Tech Stack

**Backend:** Python 3.12+ • FastAPI • Pydantic v2 • SQLAlchemy 2.0 • Confluent Kafka  
**Frontend:** React 19 • TypeScript • TailwindCSS • Rolldown  
**Infrastructure:** SQLite (Lite Mode) • MySQL (Production) • Kafka • Schema Registry • MinIO

---

## 🗺️ Roadmap

**v1.0 (Current):**
- ✅ Core governance features
- ✅ Operational visibility
- ✅ Policy enforcement

**v1.1 (Completed):**
- ✅ Enhanced Governance Dashboard
- ✅ Schema Policy (Linting) Engine
- ✅ Multi-registry health scoring

**v1.2 (In Progress):**
- 🔄 AI-assisted Schema Migration
- 🔄 Slack/Teams alert integration

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

### Test Status

- Run `uv run pytest` for the current backend suite and coverage.
- Run `npm run test --prefix frontend` for the current frontend unit tests.

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

---

<div align="center">
  
**Make Kafka safer and more efficient** 🚀

Made with ❤️ by developers, for developers

⭐ **Star if you find this useful!** ⭐

</div>
