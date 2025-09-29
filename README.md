<div align="center">
  <img src="https://raw.githubusercontent.com/your-org/kafka-gov/main/static/logo.png" alt="Kafka Gov Logo" width="400"/>
  
  # Kafka Gov
  
  **🛡️ Enterprise-grade Kafka Topic & Schema Registry Governance Platform**
  
  [![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![CI](https://github.com/your-org/kafka-gov/workflows/CI/badge.svg)](https://github.com/your-org/kafka-gov/actions)
  [![Coverage](https://codecov.io/gh/your-org/kafka-gov/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/kafka-gov)
  
  [🚀 Quick Start](#-quick-start) • [📖 Documentation](#-documentation) • [🤝 Contributing](#-contributing) • [💬 Community](#-community)
</div>

---

## ✨ Features

### 🎯 **Topic Management**
- **Batch Operations**: Plan and execute multiple topic changes with dry-run support
- **Policy Enforcement**: Automated validation against naming conventions and configuration rules
- **Environment-aware**: DEV/STG/PROD environment separation with different policies
- **Audit Trail**: Complete history of all topic changes with rollback capabilities

### 📋 **Schema Registry Governance**
- **Schema Evolution**: Manage schema versions with compatibility validation
- **Subject Management**: Organize schemas by subject with version control
- **File Upload**: Bulk schema upload with validation and conflict resolution
- **Storage Integration**: MinIO-backed schema artifact storage

### 🔒 **Security & Compliance**
- **JWT Authentication**: Secure API access with role-based permissions
- **Policy Engine**: Configurable rules for naming, configuration, and resource limits
- **Violation Detection**: Real-time policy violation detection with severity levels
- **Compliance Reporting**: Generate compliance reports for audit purposes

### 🏗️ **Enterprise Architecture**
- **Clean Architecture**: Domain-driven design with clear layer separation
- **High Performance**: Async/await throughout with connection pooling
- **Observability**: Structured logging, metrics, and health checks
- **Scalability**: Horizontal scaling support with stateless design

## 🏗️ Architecture

Built on **Clean Architecture** principles with domain-driven design:

```
app/
├── shared/                    # Common infrastructure
│   ├── database.py           # SQLAlchemy async engine
│   ├── container.py          # Dependency injection
│   └── auth.py              # JWT authentication
├── policy/                   # Policy engine domain
│   ├── domain/              # Policy rules & evaluation
│   ├── application/         # Policy services
│   └── infrastructure/      # Rule repositories
├── topic/                    # Topic management domain
│   ├── domain/              # Topic models & business logic
│   ├── application/         # Use cases & orchestration
│   ├── infrastructure/      # Kafka & database adapters
│   └── interface/           # REST API endpoints
├── schema/                   # Schema registry domain
│   └── (similar structure)
└── main.py                   # Application entry point
```

## 🚀 주요 기능

### Topic 관리
- Topic 생성, 수정, 삭제
- 배치 작업 계획 수립 및 실행
- 정책 검증 및 위반 사항 확인
- Dry-run 모드 지원

### Schema Registry 관리
- 스키마 등록, 조회, 삭제
- Subject 및 버전 관리
- 호환성 모드 설정
- MinIO 기반 스키마 저장소

## 🛠️ 기술 스택

- **Framework**: FastAPI
- **DI Container**: dependency-injector
- **Settings**: pydantic-settings
- **Database**: SQLAlchemy (Async)
- **Kafka**: confluent-kafka-python
- **Storage**: MinIO
- **Type Safety**: Python 3.12+ with strict typing
- **Auth**: argon2-cffi (패스워드 해시), python-jose (JWT)

## 📋 환경 설정

1. `.env` 파일을 생성하고 `.env.example`을 참고하여 설정:

```bash
cp .env.example .env
```

2. 주요 설정 항목:
   - `KAFKA_BOOTSTRAP_SERVERS`: Kafka 브로커 서버 목록
   - `MINIO_ENDPOINT`: MinIO 서버 엔드포인트
   - `SCHEMA_REGISTRY_URL`: Schema Registry URL
   - `DATABASE_URL`: 데이터베이스 연결 URL
   - `SECRET_KEY`: JWT 서명용 시크릿 (예시값 제공, 반드시 교체)
   - `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`: JWT 설정

## 🏃‍♂️ 실행 방법

### 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
python -m app.main
```

### Docker Compose 실행

```bash
docker-compose up -d
```

## 📚 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 주요 엔드포인트

### Topic 관리
- `GET /api/v1/topics/{env}` - Topic 목록 조회
- `GET /api/v1/topics/{env}/{topic_name}` - Topic 설정 조회
- `POST /api/v1/topics/{env}/plan` - 배치 작업 계획 수립
- `POST /api/v1/topics/{env}/apply` - 배치 작업 실행

### Schema Registry
- `GET /api/v1/schemas/subjects` - Subject 목록 조회
- `GET /api/v1/schemas/subjects/{subject}/versions` - Subject 버전 목록
- `GET /api/v1/schemas/subjects/{subject}/versions/{version}` - 스키마 조회
- `POST /api/v1/schemas/{env}/plan` - 스키마 배치 계획 수립
- `POST /api/v1/schemas/{env}/apply` - 스키마 배치 실행

### Auth (신규)
- `POST /api/v1/auth/register` - 회원가입 및 액세스 토큰 발급
- `POST /api/v1/auth/login` - 로그인 및 액세스 토큰 발급

응답:
```
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

## 🔧 개발 원칙

### 타입 안정성
- Python 3.12+ 기준 엄격한 타입 힌트 사용
- `Optional` 대신 `| None` 사용
- 모든 공개 함수/클래스에 타입 힌트 필수

### 도메인 분리
- IO 경계는 Pydantic 모델 사용
- 내부 도메인은 dataclass(frozen=True, slots=True) 사용
- 불변성 원칙 준수

### 의존성 관리
- dependency-injector 기반
- 공통 인프라 컨테이너(shared) + 모듈별 컨테이너(topic/schema/auth) 구성
- 모듈 경계에서만 와이어링(lifespan에서 초기화)

## 🏥 헬스체크

```bash
curl http://localhost:8000/health
```

## 📝 라이선스

MIT License