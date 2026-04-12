# 🏗️ Architecture Overview

Kafka-Gov is built on **Clean Architecture** principles with domain-driven design.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React 19)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │ Schemas  │  │History   │  │Policies  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 REST API (FastAPI)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  Schema  │  │ Cluster  │  │ Shared   │               │
│  │Interface │  │Interface │  │Interface │               │
│  └──────────┘  └──────────┘  └──────────┘               │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Application Layer (Use Cases)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SyncSchema │ PolicyEvaluation │ AuditHistory   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Domain Layer (Business Logic)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  Schema  │  │ Cluster  │  │ Shared   │               │
│  │ Entities │  │ Models   │  │ Models   │               │
│  └──────────┘  └──────────┘  └──────────┘               │
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
├── schema/          # Schema Registry 관리
│   ├── domain/      # Schema, Compatibility 모델
│   ├── application/ # 스키마 등록/동기화 유즈케이스
│   ├── infrastructure/ # Schema Registry & MinIO
│   └── interface/   # 스키마 API
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
│   ├── schema/      # UploadSchemaModal, schema detail helpers
│   └── ui/          # Shared UI building blocks
│
├── pages/           # 페이지 컴포넌트 (라우팅)
│   ├── governance/Dashboard.tsx
│   ├── History.tsx
│   ├── Connections/index.tsx
│   ├── schemas/SchemaDetail.tsx
│   └── SchemaPolicies.tsx
│
├── services/        # API 클라이언트 (axios)
│   ├── api.ts
│   └── schemaApi.ts
│
├── hooks/           # Custom React Hooks
│   └── schema/useSchemaDetail.ts
│
├── contexts/        # React Context (전역 상태)
│   └── ToastContext.tsx
│
├── types/           # TypeScript 타입 정의
│   ├── index.ts
│   └── schema.ts
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
- Schema registration events for shared audit and approval handlers
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
schema.registered event → shared audit/approval handlers
policy.changed event → validation rule update
```

### Dependency Flow

```
shared (foundation)
  ↑
cluster (connection manager)
  ↑
schema (business domain)
```

### Data Flow Example (Schema Registration)

1. User uploads a schema via `/api/v1/schemas/upload`
2. `schema` module validates compatibility and governance policy
3. `schema` module queries `cluster` for the active Schema Registry client
4. Storage and audit metadata are persisted
5. `schema` module emits `schema.registered` events
6. `shared` module persists audit logs

---

## Module Overview

| Module | Purpose | Key Features | Documentation |
|--------|---------|--------------|---------------|
| 🌐 **`shared/`** | Common Infrastructure | Database, Event Bus, Encryption, Exception Handling | [View Details](../../app/shared/README.md) |
| 🔌 **`cluster/`** | Multi-Cluster Management | Register clusters, Dynamic switching, Health checks | [View Details](../../app/cluster/README.md) |
| 📦 **`schema/`** | Schema Registry | Upload schemas, Compatibility modes, MinIO storage | [View Details](../../app/schema/README.md) |

---

## Detailed Architecture Guides

- [Features Overview](../features/overview.md)
- [Platform Direction](../features/real-time-data-governance-system.md)
- [Deployment Guide](../operations/deployment.md)

---

## Design Patterns Used

| Pattern | Usage | Module |
|---------|-------|--------|
| **Repository** | Data access abstraction | All modules |
| **Factory** | Object creation | cluster, schema |
| **Strategy** | Policy validation | schema |
| **Observer** | Event bus | shared |
| **Adapter** | External API clients | Infrastructure layers |
| **Dependency Injection** | Loose coupling | All modules |
| **CQRS** | Read/Write separation | schema governance workflows |
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

---

## Next Steps

- [Features Overview](../features/overview.md)
- [Platform Direction](../features/real-time-data-governance-system.md)
- [Deployment Guide](../operations/deployment.md)
