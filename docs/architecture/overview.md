# 🏗️ Architecture Overview

Kafka-Gov is built on **Clean Architecture** principles with domain-driven design.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React 19)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │  Topics  │  │ Schemas  │  │Consumers │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 REST API (FastAPI)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Topic   │  │  Schema  │  │ Connect  │  │Consumer  │   │
│  │Interface │  │Interface │  │Interface │  │Interface │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Application Layer (Use Cases)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CreateTopic │ BatchOperation │ SyncSchema │ etc.   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Domain Layer (Business Logic)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Topic   │  │  Schema  │  │Connector │  │Consumer  │   │
│  │ Entities │  │ Entities │  │ Entities │  │  Group   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            Infrastructure Layer (External Systems)           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Kafka   │  │ Schema   │  │  MySQL   │  │  MinIO   │   │
│  │  Admin   │  │ Registry │  │ Database │  │ Storage  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Backend Structure (Python 3.12+)

```
app/
├── shared/          # 공통 인프라 & 도메인 이벤트
│   ├── domain/      # 공통 도메인 모델 (Environment, AuditLog 등)
│   ├── infrastructure/ # DB, 암호화, 이벤트 버스
│   ├── security/    # 보안 관련 유틸리티
│   ├── utils/       # 공통 유틸리티
│   └── interface/   # 공통 HTTP 예외 처리
│
├── cluster/         # Multi-cluster 연결 관리
│   ├── domain/      # Cluster 엔티티 & 값 객체
│   ├── application/ # Connection 관리 유즈케이스
│   ├── infrastructure/ # Kafka/Schema Registry 클라이언트
│   └── interface/   # REST API 엔드포인트
│
├── topic/           # Topic 관리 (핵심 도메인)
│   ├── domain/      # Topic, TopicBatch 엔티티
│   ├── application/ # 토픽 생성/수정/삭제 유즈케이스
│   ├── infrastructure/ # Kafka Admin API & DB 저장소
│   └── interface/   # 배치/단일 토픽 API
│
├── schema/          # Schema Registry 관리
│   ├── domain/      # Schema, Compatibility 모델
│   ├── application/ # 스키마 등록/동기화 유즈케이스
│   ├── infrastructure/ # Schema Registry & MinIO
│   └── interface/   # 스키마 API
│
├── connect/         # Kafka Connect 관리
│   ├── domain/      # Connector 도메인 모델
│   ├── application/ # Connector 생성/제어 유즈케이스
│   ├── infrastructure/ # Connect REST API 클라이언트
│   └── interface/   # Connect API 엔드포인트
│
├── consumer/        # Consumer Group 모니터링 & 분석
│   ├── domain/      # ConsumerGroup, Partition, Metrics 모델
│   ├── application/ # Lag 추적, Fairness, Stuck 감지 유즈케이스
│   ├── infrastructure/ # Kafka Admin API, DB 스냅샷 저장소
│   └── interface/   # Consumer API & WebSocket 엔드포인트
│
├── container.py     # Root DI Container (Dependency Injector)
└── main.py          # FastAPI 애플리케이션 진입점
```

---

## Frontend Structure (React 19 + TypeScript)

```
frontend/src/
├── components/      # 재사용 UI 컴포넌트
│   ├── common/      # Button, Input, Modal 등
│   ├── topic/       # TopicList, CreateTopicModal
│   ├── schema/      # SchemaList, UploadSchemaModal
│   └── policy/      # PolicyDetail, VersionHistory
│
├── pages/           # 페이지 컴포넌트 (라우팅)
│   ├── Dashboard.tsx
│   ├── Topics.tsx
│   ├── Schemas.tsx
│   └── Policies.tsx
│
├── services/        # API 클라이언트 (axios)
│   ├── topicService.ts
│   ├── schemaService.ts
│   └── policyService.ts
│
├── hooks/           # Custom React Hooks
│   ├── useTopics.ts
│   └── useBatchOperation.ts
│
├── contexts/        # React Context (전역 상태)
│   └── ClusterContext.tsx
│
├── types/           # TypeScript 타입 정의
│   └── api.ts
│
└── utils/           # 유틸리티 함수
```

---

## Key Principles

### Backend Principles

**Clean Architecture:**
- **Domain**: Pure business logic, no dependencies on frameworks
- **Application**: Use cases and orchestration
- **Infrastructure**: External integrations (Kafka, DB, MinIO)
- **Interface**: REST API endpoints and request/response schemas

**Event-Driven:**
- Domain events for cross-context communication
- Topic-schema auto-correlation via events
- Event bus for decoupling modules

**Type Safety:**
- Python 3.12+ with strict typing (`str | None`, `list[T]`)
- No `Any` types allowed
- Pydantic v2 for I/O boundary validation

**Dependency Injection:**
- Hierarchical DI containers per domain
- `dependency-injector` library
- Constructor injection for testability

**High Performance:**
- Async/await throughout
- Connection pooling
- Batch operations
- Parallel processing

**Observability:**
- Structured logging
- Detailed validation errors
- Health checks
- Audit trails

**Data-Oriented:**
- Immutable domain models with `@dataclass(frozen=True)`
- Separation of I/O DTOs (Pydantic) and domain models (dataclasses)
- Minimal validation in domain layer

**Error Resilience:**
- Graceful error handling
- Retry policies
- Detailed error messages
- Circuit breakers (planned)

---

### Frontend Principles

**Component-Driven:**
- Atomic design pattern
- Reusable components
- Single responsibility

**Type-Safe API:**
- TypeScript with strict mode
- Axios interceptors
- Full type inference

**Modern React:**
- React 19 features
- Function components only
- Hooks for state management
- Context for global state

**Responsive UI:**
- TailwindCSS utility-first
- Mobile-first design
- Accessible components

**Build Performance:**
- Rolldown (Rust-based bundler)
- Fast HMR (Hot Module Replacement)
- Code splitting

---

## Inter-Module Communication

### Event-Driven Integration

```
topic.created event → topic-schema auto-correlation
schema.registered event → topic-schema auto-correlation
policy.changed event → validation rule update
```

### Dependency Flow

```
shared (foundation)
  ↑
cluster (connection manager)
  ↑
topic, schema, connect, consumer (business domains)
```

### Data Flow Example (Batch Topic Creation)

1. User uploads YAML via `/api/v1/topics/batch/upload`
2. `topic` module parses YAML and validates against policies
3. `topic` module queries `cluster` for active Kafka Admin client
4. Dry-run preview generated and returned to user
5. User clicks "Apply"
6. `topic` module executes batch operations
7. `topic` module emits `topic.created` events
8. Topic-schema correlation updated automatically
9. `shared` module persists audit logs

---

## Module Overview

| Module | Purpose | Key Features | Documentation |
|--------|---------|--------------|---------------|
| 🌐 **`shared/`** | Common Infrastructure | Database, Event Bus, Encryption, Exception Handling | [View Details](../../app/shared/README.md) |
| 🔌 **`cluster/`** | Multi-Cluster Management | Register clusters, Dynamic switching, Health checks | [View Details](../../app/cluster/README.md) |
| 🎯 **`topic/`** | Topic Governance (Core) | CRUD + Batch operations, Policy enforcement, Versioning | [View Details](../../app/topic/README.md) |
| 📦 **`schema/`** | Schema Registry | Upload schemas, Compatibility modes, MinIO storage | [View Details](../../app/schema/README.md) |
| 🔌 **`connect/`** | Kafka Connect | Connector CRUD, Control, Plugin management | [View Details](../../app/connect/README.md) |
| 📊 **`consumer/`** | Real-time Monitoring | Topic & Consumer monitoring, Lag tracking, Fairness analysis | [View Details](../../app/consumer/README.md) |

---

## Detailed Architecture Guides

- [Backend Architecture](./backend.md)
- [Frontend Architecture](./frontend.md)
- [Database Schema](./database.md)
- [Security Architecture](./security.md)
- [Deployment Architecture](./deployment.md)

---

## Design Patterns Used

| Pattern | Usage | Module |
|---------|-------|--------|
| **Repository** | Data access abstraction | All modules |
| **Factory** | Object creation | cluster, topic |
| **Strategy** | Policy validation | topic |
| **Observer** | Event bus | shared |
| **Adapter** | External API clients | Infrastructure layers |
| **Dependency Injection** | Loose coupling | All modules |
| **CQRS** | Read/Write separation | topic (batch vs single) |
| **Event Sourcing** | Audit trail | shared |

---

## Technology Stack

### Backend
- **Python 3.12+**: Modern type hints, pattern matching
- **FastAPI 0.117+**: Async web framework
- **Pydantic v2**: I/O validation
- **SQLAlchemy 2.0**: Async ORM
- **dependency-injector**: DI container
- **confluent-kafka**: Kafka client

### Frontend
- **TypeScript 5.9+**: Type-safe development
- **React 19.1**: Latest React features
- **TailwindCSS 3.4**: Utility-first CSS
- **Rolldown**: Rust-based bundler
- **Axios 1.7+**: HTTP client

### Infrastructure
- **MySQL 8.0+**: Metadata storage
- **Apache Kafka**: Message broker
- **Schema Registry**: Schema versioning
- **MinIO**: S3-compatible object storage
- **Kafka Connect**: Data integration

---

## Next Steps

- [Backend Architecture Deep Dive](./backend.md)
- [Frontend Architecture Deep Dive](./frontend.md)
- [Database Schema Design](./database.md)
- [API Reference](../api/)
