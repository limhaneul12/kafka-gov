<div align="center">
  <img src="./image/kafka_gov_logo.png" alt="Kafka Gov Logo" width="300"/>
  
  # 🛡️ Kafka Governance Platform
  
  **Enterprise-grade Kafka management with rich metadata, policy enforcement, and batch operations**
  
  [![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.117.1+-green.svg)](https://fastapi.tiangolo.com)
  [![Confluent Kafka](https://img.shields.io/badge/Confluent--Kafka-2.6.1-orange.svg)](https://github.com/confluentinc/confluent-kafka-python)
  [![Pydantic](https://img.shields.io/badge/Pydantic-2.11.9+-e92063.svg)](https://docs.pydantic.dev/)

  [![React](https://img.shields.io/badge/React-19.1-61dafb.svg)](https://react.dev)
  [![TypeScript](https://img.shields.io/badge/TypeScript-5.9+-3178c6.svg)](https://www.typescriptlang.org/)
  [![Coverage](https://img.shields.io/badge/Coverage-64%25-brightgreen.svg)](https://github.com/limhaneul12/kafka-gov)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
  
  **"Without knowing who owns a topic and what it's used for, Kafka is just a message queue."**
  
  [🚀 Quick Start](#-quick-start) • [✨ Features](#-features) • [📖 Documentation](#-documentation) • [🏗️ Architecture](#️-architecture) • [📦 Modules](#-module-responsibilities) • [🗺️ Roadmap](#️-roadmap)
</div>

---

## 🌟 What Makes Kafka-Gov Special?

<div align="center">

### 🎯 **Built for Governance**, Not Just Monitoring

Unlike traditional Kafka UI tools that focus on *viewing* data, Kafka-Gov is designed for **enterprise governance** with metadata-first approach, policy enforcement, and operational excellence.

</div>

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

## ✨ Features

### 📊 Dashboard Overview

Monitor your Kafka ecosystem at a glance with real-time metrics and health status.

<div align="center">
  <img src="./image/dashboard.png" alt="Kafka Gov Dashboard" width="800"/>
  <p><em>Unified dashboard showing total topics, schemas, correlations, and cluster health</em></p>
</div>

**Dashboard Metrics:**
- 📈 **Total Topics**: Number of managed topics across all clusters
- 📦 **Registered Schemas**: Schema Registry integration status
- 🔗 **Correlations**: Auto-linked topic-schema relationships
- 💚 **Health Status**: Real-time cluster connectivity monitoring

---

### 📊 Topic Management Dashboard

Manage all topics at a glance from the unified dashboard.

<div align="center">
  <img src="./image/topic_list.png" alt="Topic Management Dashboard" width="800"/>
  <p><em>Filter and search topics with rich metadata</em></p>
</div>

**Key Features:**
- 📌 Filter topics by Owner/Team
- 🏷️ Tag-based search and classification
- 📝 Quick access to documentation links
- 🌍 Environment-based management (DEV/STG/PROD)
- 📊 Instant view of Partition, Replication, Retention info
- 🔍 Real-time search with multiple filters

### 🔌 Multi-Cluster Connection Management

- **Dynamic Cluster Registration**: Register and switch between multiple Kafka clusters at runtime
- **Connection Storage**: Bootstrap servers, SASL/SSL authentication, timeout settings
- **Schema Registry Integration**: Manage Schema Registry URL and authentication per cluster
- **Object Storage Integration**: Connect to MinIO/S3-compatible storage for schema artifacts
- **Kafka Connect Management**: Manage Connect REST API URLs and authentication
- **Connection Testing**: Verify connectivity before registration with latency measurement
- **Encryption**: Sensitive credentials are encrypted at rest

**Supported Security Protocols:**
- PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL
- SASL Mechanisms: PLAIN, SCRAM-SHA-256, SCRAM-SHA-512, GSSAPI, OAUTHBEARER

### 🏷️ Rich Topic Metadata

- **Owner & Team**: Track who owns and maintains each topic
- **Documentation**: Direct links to Wiki/Confluence docs (required)
- **Tags**: Flexible classification (`pii`, `critical`, `deprecated`)
- **At-a-glance**: View partitions, replication, retention instantly
- **Single Topic Creation**: Quick form-based creation for individual topics

### 📏 Flexible Naming Policy

**3 Built-in Strategies + Custom Support:**

| Strategy | Structure | Use Case |
|----------|-----------|----------|
| **Permissive** | Free-form | Startups, rapid development |
| **Balanced** | `{env}.{domain}.{resource}` | Mid-size companies, team namespaces |
| **Strict** | `{env}.{classification}.{domain}.{resource}.{version}` | Enterprises, compliance-driven |
| **Custom** | Defined via YAML | Special requirements |

**Features:**
- ✅ Runtime strategy switching (no redeployment required)
- ✅ Strict Pydantic-based validation (StrictStr, StringConstraints)
- ✅ PII data classification with additional constraints
- ✅ Upload custom YAML rules

```bash
# Switch with one click in the UI
Permissive → Balanced → Strict

# Or upload YAML
curl -X POST /api/v1/naming-policy/custom \
  -F "file=@my-company-policy.yml"
```

📖 **Detailed Guide**: [Topic Naming Conventions](./docs/topic-naming-conventions.md)

### 🚀 YAML-Based Batch Operations

**Create/update/delete dozens of topics at once:**

<div align="center">
  <img src="./image/create_topic.png" alt="Create Topic - Single & Batch" width="800"/>
  <p><em>Choose between single topic creation or YAML batch creation</em></p>
</div>

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

<div align="center">
  <img src="./image/batch_result.png" alt="Batch Processing Result" width="800"/>
  <p><em>View batch processing results in real-time and download in text/JSON format</em></p>
</div>

See [`example/batch_topics.yml`](./example/batch_topics.yml) for a full example.

### 📦 Schema Registry Management

- **Auto-Registration**: Automatic Schema Registry registration
- **Compatibility Modes**: Set schema evolution rules (BACKWARD, FORWARD, FULL, NONE)
- **Team Tracking**: Associate schemas with owning teams
- **Artifact Storage**: Permanent storage in MinIO (S3-compatible)
- **Topic Linking**: Auto-map schemas to topics (e.g., `prod.orders.created-value`)
- **Impact Analysis**: View topics affected by schema changes

**Compatibility Modes:**
- **BACKWARD** (default): New schema can read old data
- **FORWARD**: Old schema can read new data
- **FULL**: Both backward and forward compatible
- **NONE**: No compatibility checks

### 🔌 Kafka Connect Management

- **Connector CRUD**: Create, read, update, delete Source/Sink connectors
- **State Control**: Start, pause, restart connectors and tasks
- **Real-time Monitoring**: Monitor connector and task status (RUNNING, PAUSED, FAILED)
- **Plugin Management**: List installed connector plugins and validate configurations
- **Topic Tracking**: Auto-track topics used by connectors
- **Metadata Integration**: Associate team/tag info with connectors (governance)
- **REST API Proxy**: Securely proxy Kafka Connect REST API

**Key Features:**
- ✅ List connectors (expand option for status/config details)
- ✅ Create/update/delete connectors (with config validation)
- ✅ Connector control: pause/resume/restart
- ✅ Task management: restart individual tasks, view status
- ✅ Plugin listing and config validation

### 🛡️ Environment-Specific Policies

Apply different policies per environment to ensure operational stability.

<div align="center">
  <img src="./image/policy.png" alt="Policy Detail View" width="800"/>
  <p><em>Policy detail view - Define and manage rules in JSON format</em></p>
</div>

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

<div align="center">
  <img src="./image/policy_versing.png" alt="Policy Version Management" width="800"/>
  <p><em>Policy version management - Track policy change history with Draft, Active, Archived states</em></p>
</div>

**Policy Version Management:**
- ✅ **Draft**: Policy in progress (not applied)
- ✅ **Active**: Currently applied policy (only one allowed)
- ✅ **Archived**: Historical policy versions
- 🔄 Version comparison and rollback support
- 📅 Track creation and activation times

### 📊 Complete Audit Trail

- **Who**: Actor and team
- **When**: UTC timestamp
- **What**: Before/after config snapshots
- **Why**: Change ID linking to deployment
- **Result**: Success/partial/failed with details
- **Schema Events**: Track schema uploads, compatibility changes, and deletions

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

Quickest way to get started:

```bash
# 1. Clone repository
git clone https://github.com/limhaneul12/kafka-gov.git
cd kafka-gov

# 2. Configure environment
cp .env.example .env
# Edit .env file with your Kafka connection details

# 3. Start all services (Kafka, MySQL, MinIO, Backend, Frontend)
docker-compose up -d

# 4. Access web UI
open http://localhost:8000
```

**Main Endpoints:**
- 🌐 **Web UI**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs (Swagger UI)
- 💚 **Health Check**: http://localhost:8000/health

### Option 2: Local Development

Detailed setup for developers:

**Backend (Python 3.12+)**
```bash
# Install Python dependencies (using uv)
cd kafka-gov
uv sync

# Run database migrations
uv run alembic upgrade head

# Start development server
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend (React 19)**
```bash
# Install Node.js dependencies
cd frontend
npm install

# Start development server
npm run dev
# Access at http://localhost:5173
```

### Test Your First Batch Upload

```bash
# Test batch creation with YAML file
curl -X POST "http://localhost:8000/api/v1/topics/batch/upload" \
  -F "file=@example/batch_topics.yml"

# Result: Dry-run preview → Review policy violations → Click "Apply Changes"
```

### Next Steps

1. **Register Cluster**: UI → Connections → Add Cluster
2. **Configure Policy**: Policies → Create Policy
3. **Create Topics**: Topics → Create Topic (single) or Upload YAML (batch)
4. **Upload Schemas**: Schemas → Upload Schema

---

## 📖 Documentation

### Creating Topics

**Option 1: Single Topic (Quick Form)**

1. Click "Single Topic Creation" in Topics tab
2. Fill in the form:
   - Environment (DEV/STG/PROD)
   - Topic name (e.g., `prod.order.count`)
   - Partitions, Replication Factor, Min In-Sync Replicas
   - Owner (team name)
   - Documentation URL (required)
   - Tags (optional)
3. Click "Create"

**Option 2: Batch Operations (YAML)**

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
      doc: "https://wiki.company.com/events"
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

### Backend Structure (Python 3.12+)

```
app/
├── shared/          # 공통 인프라 & 도메인 이벤트
│   ├── domain/      # 공통 도메인 모델 (Environment, AuditLog 등)
│   ├── infra/       # DB, 암호화, 이벤트 버스
│   └── interface/   # 공통 HTTP 예외 처리
├── cluster/         # Multi-cluster 연결 관리
│   ├── domain/      # Cluster 엔티티 & 값 객체
│   ├── application/ # Connection 관리 유즈케이스
│   ├── infra/       # Kafka/Schema Registry 클라이언트
│   └── interface/   # REST API 엔드포인트
├── connect/         # Kafka Connect 관리
│   ├── domain/      # Connector 도메인 모델
│   ├── application/ # Connector 생성/제어 유즈케이스
│   └── interface/   # Connect API 엔드포인트
├── topic/           # Topic 관리 (핵심 도메인)
│   ├── domain/      # Topic, TopicBatch 엔티티
│   ├── application/ # 토픽 생성/수정/삭제 유즈케이스
│   ├── infra/       # Kafka Admin API & DB 저장소
│   └── interface/   # 배치/단일 토픽 API
├── schema/          # Schema Registry 관리
│   ├── domain/      # Schema, Compatibility 모델
│   ├── application/ # 스키마 등록/동기화 유즈케이스
│   └── infra/       # Schema Registry & MinIO
├── analysis/        # 토픽-스키마 연관분석
│   ├── application/ # Impact analysis 유즈케이스
│   └── interface/   # 분석 API
├── container.py     # Root DI Container (Dependency Injector)
└── main.py          # FastAPI 애플리케이션 진입점
```

### Frontend Structure (React 19 + TypeScript)

```
frontend/src/
├── components/      # 재사용 UI 컴포넌트
│   ├── common/      # Button, Input, Modal 등
│   ├── topic/       # TopicList, CreateTopicModal
│   ├── schema/      # SchemaList, UploadSchemaModal
│   └── policy/      # PolicyDetail, VersionHistory
├── pages/           # 페이지 컴포넌트 (라우팅)
│   ├── Dashboard.tsx
│   ├── Topics.tsx
│   ├── Schemas.tsx
│   └── Policies.tsx
├── services/        # API 클라이언트 (axios)
│   ├── topicService.ts
│   ├── schemaService.ts
│   └── policyService.ts
├── hooks/           # Custom React Hooks
│   ├── useTopics.ts
│   └── useBatchOperation.ts
├── contexts/        # React Context (전역 상태)
│   └── ClusterContext.tsx
├── types/           # TypeScript 타입 정의
│   └── api.ts
└── utils/           # 유틸리티 함수
```

### Key Principles

**Backend:**
- **Clean Architecture**: Domain → Application → Infrastructure → Interface
- **Event-Driven**: Domain events for cross-context communication (topic-schema sync)
- **Type Safety**: Python 3.12+ with strict typing (`str | None`, `list[T]`)
- **Dual Validation**: Pydantic v2 (I/O boundary) + msgspec (domain models)
- **DI Container**: Hierarchical dependency injection with `dependency-injector`
- **High Performance**: Async/await throughout with connection pooling and batch operations
- **Observability**: Structured JSON logging, detailed validation errors, and health checks
- **Data-Oriented**: Immutable domain models with msgspec (frozen structs)
- **Error Resilience**: Circuit breakers, retry policies, and graceful degradation

**Frontend:**
- **Component-Driven**: Atomic design pattern with reusable components
- **Type-Safe API**: TypeScript with strict mode and Axios interceptors
- **Modern React**: React 19 with hooks, context, and function components
- **Responsive UI**: TailwindCSS with mobile-first design
- **Build Performance**: Rolldown (Rust-based bundler) for fast builds

---

## 📦 Module Overview

Kafka-Gov is organized into 6 bounded contexts, each following Clean Architecture principles:

| Module | Purpose | Key Features | Documentation |
|--------|---------|--------------|---------------|
| 🌐 **`shared/`** | Common Infrastructure | Database, Event Bus, Encryption, Exception Handling | [View Details](./app/shared/README.md) |
| 🔌 **`cluster/`** | Multi-Cluster Management | Register clusters, Dynamic switching, Health checks | [View Details](./app/cluster/README.md) |
| 🎯 **`topic/`** | Topic Governance (Core) | CRUD + Batch operations, Policy enforcement, Versioning | [View Details](./app/topic/README.md) |
| 📦 **`schema/`** | Schema Registry | Upload schemas, Compatibility modes, MinIO storage | [View Details](./app/schema/README.md) |
| 🔗 **`analysis/`** | Topic-Schema Correlation | Auto-linking, Impact analysis, Event-driven | [View Details](./app/analysis/README.md) |
| 🔌 **`connect/`** | Kafka Connect | Connector CRUD, Control, Plugin management | [View Details](./app/connect/README.md) |

**Each module contains:**
- `domain/` - Entities, value objects, domain services
- `application/` - Use cases and orchestration logic
- `infrastructure/` - External integrations (Kafka, DB, MinIO)
- `interface/` - REST API endpoints and schemas
- `README.md` - Detailed documentation with API reference

---

### 🔄 Inter-Module Communication

**Event-Driven Integration:**

```
topic.created event → analysis module → auto-link to schemas
schema.registered event → analysis module → auto-link to topics
```

**Dependency Flow:**

```
shared (foundation)
  ↑
cluster (connection manager)
  ↑
topic, schema, connect, analysis (business domains)
```

**Data Flow Example (Batch Topic Creation):**

1. User uploads YAML via `/api/v1/topics/batch/upload`
2. `topic` module parses YAML and validates against policies
3. `topic` module queries `cluster` for active Kafka Admin client
4. Dry-run preview generated and returned to user
5. User clicks "Apply"
6. `topic` module executes batch operations
7. `topic` module emits `topic.created` events
8. `analysis` module listens and auto-links topics to schemas
9. `shared` module persists audit logs

### 📚 API Reference

For detailed API endpoints and request/response schemas, refer to:
- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **Readable Docs**: http://localhost:8000/redoc
- **Module-specific APIs**: See each module's README for detailed endpoint documentation

---

## 🛠️ Tech Stack

### Backend Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| **Language** | Python 3.12+ | Native union types (`str \| None`), pattern matching |
| **Framework** | FastAPI 0.117+ | High-performance async web framework |
| **Validation** | Pydantic v2 + msgspec | I/O boundary (Pydantic) + Domain models (msgspec) |
| **Database** | MySQL 8.0+ | Metadata storage (clusters, policies, audit logs) |
| **ORM** | SQLAlchemy 2.0 (Async) | Async database operations |
| **Message Broker** | Apache Kafka | Topic management via Admin API |
| **Schema Registry** | Confluent Schema Registry | Schema versioning & compatibility |
| **Object Storage** | MinIO (S3-compatible) | Schema artifact permanent storage |
| **DI Container** | dependency-injector | Hierarchical dependency injection |
| **Event Bus** | In-memory async event bus | Cross-domain communication |
| **Testing** | pytest + pytest-asyncio | 85%+ test coverage |
| **Package Manager** | uv | Ultra-fast dependency resolution (Rust-based) |
| **Key Libraries** | confluent-kafka, aiomysql, httpx, orjson, aiofiles | Async clients & serialization |

### Frontend Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| **Language** | TypeScript 5.9+ | Type-safe frontend development |
| **Framework** | React 19.1 | Latest React with concurrent features |
| **Routing** | React Router 6.28 | Client-side routing |
| **HTTP Client** | Axios 1.7+ | API communication with interceptors |
| **UI Framework** | TailwindCSS 3.4 | Utility-first CSS framework |
| **Icons** | Lucide React 0.469 | Beautiful & consistent icon set |
| **Notifications** | Sonner 1.7 | Toast notifications |
| **Build Tool** | Rolldown (Vite fork) | Rust-based ultra-fast bundler |
| **State Management** | React Context + Hooks | Lightweight state management |
| **Type Safety** | Strict TypeScript | No `any`, full type inference |

### Architecture Patterns

| Pattern | Implementation |
|---------|----------------|
| **Clean Architecture** | Domain → Application → Infrastructure → Interface |
| **DDD** | Bounded contexts: cluster, topic, schema, connect, analysis |
| **Event-Driven** | Domain events for cross-context communication |
| **CQRS** | Separate read/write operations (batch vs single topic) |
| **Repository Pattern** | Abstract data access layer |
| **Dependency Injection** | Hierarchical DI containers per domain |

---

## ⚙️ Configuration

Key environment variables (`.env`):

```bash
# Database (for storing connection metadata)
DATABASE_URL=mysql+aiomysql://user:pass@localhost/kafka_gov

# Default Kafka Cluster (for initial registration - optional)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SECURITY_PROTOCOL=PLAINTEXT

# Default Schema Registry (for initial registration - optional)
SCHEMA_REGISTRY_URL=http://localhost:8081

# Default Object Storage (for initial registration - optional)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=kafka-gov

# Default Kafka Connect (for initial registration - optional)
KAFKA_CONNECT_URL=http://localhost:8083

# Encryption (for sensitive credentials)
ENCRYPTION_KEY=<generate using generate_encryption_key.py>
```

See [`.env.example`](.env.example) for all options.

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

## 🗺️ Roadmap

### ✅ Completed (v1.0)
- ✅ Multi-cluster connection management
- ✅ Topic CRUD with rich metadata (owner, tags, docs)
- ✅ YAML-based batch operations with dry-run
- ✅ Environment-specific policy enforcement
- ✅ Policy version management (draft/active/archived)
- ✅ Schema Registry integration with MinIO storage
- ✅ Kafka Connect connector management
- ✅ Topic-Schema correlation and impact analysis
- ✅ Complete audit trail
- ✅ React 19 frontend with TailwindCSS
- ✅ Advanced topic filtering (owner, tags, environment)
- ✅ Preset-based topic creation (dev/stg/prod/custom)
- ✅ Batch vs single creation mode toggle

### 🚧 In Progress (v1.1)
- 🔄 Kafka Connect tab in Connections page (frontend UI)

### 🔮 Planned (v2.0)
- 📅 Consumer group monitoring & lag tracking
- 📅 Topic retention policy recommendations
- 📅 Schema migration wizard
- 📅 Slack/Discord notifications for policy violations
- 📅 GitOps integration (sync with Git repository)
- 📅 Role-based access control (RBAC)
- 📅 Multi-tenancy support
- 📅 Prometheus metrics export
- 📅 Grafana dashboard templates

### 💡 Ideas (Future)
- Advanced analytics (topic usage patterns, hot partitions)
- Cost estimation for topic configurations
- AI-powered topic naming suggestions
- Cross-cluster topic migration tool

---

## 📸 Screenshots

Explore the key features through visual examples:

| Feature | Screenshot |
|---------|------------|
| **Topic List** | ![Topic List](./image/topic_list.png) |
| **Create Topic** | ![Create Topic](./image/create_topic.png) |
| **Batch Result** | ![Batch Result](./image/batch_result.png) |
| **Policy Detail** | ![Policy](./image/policy.png) |
| **Policy Versioning** | ![Policy Versioning](./image/policy_versing.png) |

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