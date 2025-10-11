<div align="center">
  <img src="./image/kafka_gov_logo.png" alt="Kafka Gov Logo" width="400"/>
  
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

### 🔌 Multi-Cluster Connection Management


- **동적 클러스터 등록**: 여러 Kafka 클러스터를 런타임에 등록/전환
- **연결 정보 저장**: Bootstrap servers, SASL/SSL 인증, 타임아웃 설정
- **Schema Registry 연동**: 클러스터별 Schema Registry URL 및 인증 관리
- **Object Storage 연동**: MinIO/S3 호환 스토리지 연결 (스키마 아티팩트 저장)
- **Kafka Connect 관리**: Connect REST API URL 및 인증 정보 관리
- **연결 테스트**: 등록 전 연결 가능 여부 검증 (latency 측정)
- **암호화**: 민감한 인증 정보는 암호화하여 저장

**지원되는 보안 프로토콜:**
- PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL
- SASL 메커니즘: PLAIN, SCRAM-SHA-256, SCRAM-SHA-512, GSSAPI, OAUTHBEARER

### 🏷️ Rich Topic Metadata

- **Owner & Team**: Track who owns and maintains each topic
- **Documentation**: Direct links to Wiki/Confluence docs (required)
- **Tags**: Flexible classification (`pii`, `critical`, `deprecated`)
- **At-a-glance**: View partitions, replication, retention instantly
- **Single Topic Creation**: Quick form-based creation for individual topics

### 🚀 YAML-Based Batch Operations

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

- **커넥터 CRUD**: Source/Sink 커넥터 생성, 조회, 수정, 삭제
- **상태 제어**: 커넥터/태스크 시작, 일시정지, 재시작
- **실시간 모니터링**: 커넥터 및 태스크 상태 실시간 확인 (RUNNING, PAUSED, FAILED)
- **플러그인 관리**: 설치된 커넥터 플러그인 목록 조회 및 설정 검증
- **토픽 추적**: 커넥터가 사용 중인 토픽 자동 추적
- **메타데이터 연동**: 커넥터에 팀/태그 정보 연결 (거버넌스)
- **REST API 프록시**: Kafka Connect REST API를 안전하게 프록시 처리

**주요 기능:**
- ✅ 커넥터 목록 조회 (expand 옵션으로 상태/설정 함께 조회 가능)
- ✅ 커넥터 생성/수정/삭제 (설정 검증 포함)
- ✅ 커넥터 제어: pause/resume/restart
- ✅ 태스크 관리: 개별 태스크 재시작, 상태 조회
- ✅ 플러그인 목록 및 설정 검증

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

- **Who**: Actor and team
- **When**: UTC timestamp
- **What**: Before/after config snapshots
- **Why**: Change ID linking to deployment
- **Result**: Success/partial/failed with details
- **Schema Events**: Track schema uploads, compatibility changes, and deletions

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

```
app/
├── shared/          # Common infrastructure & domain events
├── cluster/         # Multi-cluster connection management
├── connect/         # Kafka Connect management domain
├── topic/           # Topic management domain
├── schema/          # Schema registry domain
├── analysis/        # Analysis & correlation domain
├── container.py     # Root DI container
└── main.py          # FastAPI application
```

**Key Principles:**
- **Clean Architecture**: Domain → Application → Infrastructure → Interface
- **Event-Driven**: Domain events for cross-context communication (topic-schema sync)
- **Type Safety**: Python 3.12+ with strict typing, Pydantic v2, and msgspec validation
- **DI Container**: Hierarchical dependency injection with `dependency-injector`
- **High Performance**: Async/await throughout with connection pooling and batch operations
- **Observability**: Structured JSON logging, detailed validation errors, and health checks
- **Data-Oriented**: Immutable domain models with msgspec (frozen structs)
- **Error Resilience**: Circuit breakers, retry policies, and graceful degradation

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Framework** | FastAPI 0.117+, Pydantic v2 |
| **Domain Models** | msgspec (high-performance serialization) |
| **Database** | SQLAlchemy 2.0 (Async), MySQL 8.0+ |
| **Message Broker** | Apache Kafka, Confluent Platform |
| **Schema Registry** | Confluent Schema Registry (with compatibility modes) |
| **Storage** | MinIO (S3-compatible) for schema artifacts |
| **Dependency Injection** | dependency-injector (hierarchical containers) |
| **Event Bus** | In-memory async event bus |
| **Architecture** | Clean Architecture, DDD, Event-Driven, CQRS |
| **Testing** | pytest, pytest-asyncio, pytest-cov (85% coverage) |
| **Type Safety** | Python 3.12+ (native union types, pattern matching) |
| **Package Manager** | uv (ultra-fast dependency resolution) |
| **Main Libraries** | confluent-kafka, aiomysql, httpx, orjson, aiofiles |
| **Error Handling** | Centralized exception handlers with detailed validation errors |

---

## ⚙️ Configuration

Key environment variables (`.env`):

```bash
# Database (연결 정보 저장용)
DATABASE_URL=mysql+aiomysql://user:pass@localhost/kafka_gov

# Default Kafka Cluster (최초 등록용 - 선택사항)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SECURITY_PROTOCOL=PLAINTEXT

# Default Schema Registry (최초 등록용 - 선택사항)
SCHEMA_REGISTRY_URL=http://localhost:8081

# Default Object Storage (최초 등록용 - 선택사항)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=kafka-gov

# Default Kafka Connect (최초 등록용 - 선택사항)
KAFKA_CONNECT_URL=http://localhost:8083

# Encryption (민감한 정보 암호화용)
ENCRYPTION_KEY=<generate using generate_encryption_key.py>
```

See [`.env.example`](.env.example) for all options.

---

## 🔌 API Reference

**Cluster Management**
- `GET /api/v1/clusters` - 등록된 클러스터 목록 조회
- `POST /api/v1/clusters` - 클러스터 등록
- `PUT /api/v1/clusters/{cluster_id}` - 클러스터 정보 수정
- `DELETE /api/v1/clusters/{cluster_id}` - 클러스터 삭제
- `POST /api/v1/clusters/{cluster_id}/test` - 연결 테스트
- `POST /api/v1/clusters/{cluster_id}/activate` - 클러스터 활성화

**Kafka Connect**
- `GET /api/v1/connect/connectors` - 커넥터 목록 조회
- `POST /api/v1/connect/connectors` - 커넥터 생성
- `GET /api/v1/connect/connectors/{name}` - 커넥터 상세 조회
- `PUT /api/v1/connect/connectors/{name}/config` - 커넥터 설정 수정
- `DELETE /api/v1/connect/connectors/{name}` - 커넥터 삭제
- `POST /api/v1/connect/connectors/{name}/restart` - 커넥터 재시작
- `PUT /api/v1/connect/connectors/{name}/pause` - 커넥터 일시정지
- `PUT /api/v1/connect/connectors/{name}/resume` - 커넥터 재개
- `GET /api/v1/connect/connectors/{name}/status` - 커넥터 상태 조회
- `GET /api/v1/connect/connectors/{name}/tasks` - 태스크 목록 조회
- `POST /api/v1/connect/connectors/{name}/tasks/{id}/restart` - 태스크 재시작
- `GET /api/v1/connect/plugins` - 플러그인 목록 조회
- `PUT /api/v1/connect/plugins/{class}/validate` - 설정 검증

**Topics**
- `POST /api/v1/topics/batch/upload` - Upload YAML & dry-run
- `POST /api/v1/topics/batch/apply` - Apply changes
- `GET /api/v1/topics` - List topics
- `DELETE /api/v1/topics/bulk-delete` - Bulk delete

**Schemas**
- `POST /api/v1/schemas/upload` - Upload schema files (with compatibility mode)
- `POST /api/v1/schemas/sync` - Sync from Schema Registry
- `GET /api/v1/schemas` - List schemas (with owner/team info)
- `GET /api/v1/schemas/artifacts` - List schema artifacts
- `DELETE /api/v1/schemas/{subject}` - Delete schema by subject

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