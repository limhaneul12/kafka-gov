<div align="center">
  <img src="./image/logo.png" alt="Kafka Gov Logo" width="400"/>
  
  **🛡️ Kafka Governance Platform**
  
  [![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.117+-green.svg)](https://fastapi.tiangolo.com)
  [![Coverage](https://img.shields.io/badge/Coverage-85%25-brightgreen.svg)](https://github.com/limhaneul12/kafka-gov)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
  
  **"Without knowing who owns a topic and what it's used for, Kafka is just a message queue."**
  
  [🚀 Quick Start](#-quick-start) • [✨ Features](#-features) • [📖 Documentation](#-documentation)
</div>

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

## ✨ Features

### 🏷️ Rich Topic Metadata

<img src="./image/topic_channel.png" alt="Topic Management" width="800"/>

- **Owner & Team**: Track who owns and maintains each topic
- **Documentation**: Direct links to Wiki/Confluence docs
- **Tags**: Flexible classification (`pii`, `critical`, `deprecated`)
- **At-a-glance**: View partitions, replication, retention instantly

### 🚀 YAML-Based Batch Operations

<img src="./image/batch_channel.png" alt="Batch Operations" width="800"/>

**Create/update/delete dozens of topics at once:**

```yaml
# example/batch_topics.yml
kind: TopicBatch
env: prod
change_id: "2025-01-15_my-project"
items:
  - name: prod.orders.created
    action: create
    config:
      partitions: 12
      replication_factor: 3
      retention_ms: 604800000
      min_insync_replicas: 2
    metadata:
      owner: team-commerce
      doc: "https://wiki.company.com/orders"
      tags: ["orders", "critical"]
```

**Features:**
- 🔄 **Dry-Run**: Preview changes before applying
- ⚠️ **Policy Validation**: Auto-check naming, replication, ISR
- 🎯 **Parallel Processing**: Transactional batch operations
- 📋 **YAML Upload**: Instant dry-run via file upload

See [`example/batch_topics.yml`](./example/batch_topics.yml) for a full example.

### 📦 Schema Registry Management

<img src="./image/schema_channel.png" alt="Schema Management" width="800"/>

- **File Upload**: Drag & drop `.avsc`, `.proto`, `.json`, `.zip` files
- **Auto-Registration**: Automatic Schema Registry registration
- **Artifact Storage**: Permanent storage in MinIO (S3-compatible)
- **Topic Linking**: Auto-map schemas to topics (e.g., `prod.orders.created-value`)

<img src="./image/schema_upload.png" alt="Schema Upload" width="600"/>

### 🛡️ Environment-Specific Policies

| Policy | DEV | STG | PROD |
|--------|-----|-----|------|
| `min.insync.replicas` | ≥ 1 | ≥ 2 | ≥ 2 ⚠️ |
| `replication.factor` | ≥ 1 | ≥ 2 | ≥ 3 ⚠️ |
| Naming | `{env}.*` | `{env}.*` | `{env}.*` ⚠️ |
| `tmp` prefix | ✅ Allow | ⚠️ Warn | 🚫 Block |

**Violations block dry-run:**
```
❌ [ERROR] prod.tmp.test: 'tmp' prefix forbidden in prod
❌ [ERROR] prod.orders: min.insync.replicas must be >= 2 (current: 1)
```

### 📊 Complete Audit Trail

<img src="./image/history.png" alt="Audit History" width="800"/>

- **Who**: Actor and team
- **When**: UTC timestamp
- **What**: Before/after config snapshots
- **Why**: Change ID linking to deployment
- **Result**: Success/partial/failed with details

---

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/limhaneul12/kafka-gov.git
cd kafka-gov

# Configure environment
cp .env.example .env
# Edit .env with your Kafka connection details

# Start all services
docker-compose up -d

# Access application
open http://localhost:8000
```

<img src="./image/main.png" alt="Main Dashboard" width="800"/>

**Endpoints:**
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

**Upload your first batch:**
```bash
curl -X POST "http://localhost:8000/api/v1/topics/batch/upload" \
  -F "file=@example/batch_topics.yml"
```

Result: Dry-run preview → Review violations → Click "Apply Changes"

---

## 📖 Documentation

### Creating Topics

**1. Write YAML file** (`my-topics.yml`):
```yaml
kind: TopicBatch
env: prod
change_id: "2025-01-15_my-project"
items:
  - name: prod.events.user-signup
    action: create
    config:
      partitions: 6
      replication_factor: 3
      min_insync_replicas: 2
    metadata:
      owner: team-growth
      tags: ["events"]
```

**2. Upload via Web UI:**
- Topics tab → Batch Operations → Upload YAML
- Review dry-run results
- Apply changes

**3. Or use API:**
```bash
curl -X POST "http://localhost:8000/api/v1/topics/batch/upload" \
  -F "file=@my-topics.yml"
```

### Updating Topics

```yaml
- name: prod.events.user-signup
  action: alter  # change to 'alter'
  config:
    partitions: 12  # increase partitions
```

### Deleting Topics

```yaml
- name: prod.deprecated.old-topic
  action: delete
```

---

## 🏗️ Architecture

Built on **Clean Architecture** principles with domain-driven design:

```
app/
├── shared/          # Common infrastructure & domain events
├── topic/           # Topic management domain
├── schema/          # Schema registry domain
├── analysis/        # Analysis & correlation domain
├── container.py     # Root DI container
└── main.py          # FastAPI application
```

**Key Principles:**
- **Clean Architecture**: Domain → Application → Infrastructure → Interface
- **Event-Driven**: Domain events for cross-context communication
- **Type Safety**: Python 3.12+ with strict typing and msgspec validation
- **DI Container**: Hierarchical dependency injection with `dependency-injector`
- **High Performance**: Async/await throughout with connection pooling
- **Observability**: Structured logging, metrics, and health checks

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Framework** | FastAPI 0.117+, Pydantic v2 |
| **Domain Models** | msgspec (high-performance serialization) |
| **Database** | SQLAlchemy 2.0 (Async), MySQL/PostgreSQL |
| **Message Broker** | Apache Kafka, Confluent Platform |
| **Schema Registry** | Confluent Schema Registry |
| **Storage** | MinIO (S3-compatible) |
| **Dependency Injection** | dependency-injector |
| **Event Bus** | In-memory async event bus |
| **Architecture** | Clean Architecture, DDD, Event-Driven |
| **Testing** | pytest, pytest-asyncio, pytest-cov (85% coverage) |
| **Type Safety** | Python 3.12+, pyrefly, ruff |
| **Package Manager** | uv (ultra-fast) |
| **Main Libraries** | confluent-kafka, aiomysql, httpx, orjson |

---

## ⚙️ Configuration

Key environment variables (`.env`):

```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
SCHEMA_REGISTRY_URL=http://localhost:8081
DATABASE_URL=mysql+aiomysql://user:pass@localhost/kafka_gov
MINIO_ENDPOINT=localhost:9000
```

See [`.env.example`](.env.example) for all options.

---

## 🔌 API Reference

**Topics**
- `POST /api/v1/topics/batch/upload` - Upload YAML & dry-run
- `POST /api/v1/topics/batch/apply` - Apply changes
- `GET /api/v1/topics` - List topics
- `DELETE /api/v1/topics/bulk-delete` - Bulk delete

**Schemas**
- `POST /api/v1/schemas/upload` - Upload schema files
- `POST /api/v1/schemas/sync` - Sync from Schema Registry
- `GET /api/v1/schemas` - List schemas

**Analysis**
- `GET /api/v1/analysis/correlation/by-schema/{subject}` - Topics using schema
- `GET /api/v1/analysis/impact/schema/{subject}` - Impact analysis

**System**
- `GET /health` - Health check
- `GET /docs` - Swagger UI

See full API docs at http://localhost:8000/docs

---

## 🚀 Deployment

**Docker Compose (Recommended)**
```bash
docker-compose up -d
```

**Production**
```bash
docker build -t kafka-gov:latest .
docker run -d -p 8000:8000 --env-file .env.prod kafka-gov:latest
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Write tests: `uv run pytest --cov=app`
4. Commit: `git commit -m 'feat: Add feature'`
5. Push and create Pull Request

**Standards**: Python 3.12+, 80%+ test coverage, Clean Architecture, Ruff linting

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Async web framework
- [Confluent Kafka](https://www.confluent.io/) - Python client
- [SQLAlchemy](https://www.sqlalchemy.org/) - Async ORM
- [msgspec](https://jcristharif.com/msgspec/) - High-performance serialization
- [uv](https://github.com/astral-sh/uv) - Fast package manager

---

<div align="center">
  
**Make Kafka safer and more efficient** 🚀

Made with ❤️ by developers, for developers

⭐ **Star if you find this useful!** ⭐

</div>