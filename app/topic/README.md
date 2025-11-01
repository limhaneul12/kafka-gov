# 🎯 Topic Module

토픽 생명주기 관리: 배치 생성/수정/삭제, 메타데이터, 정책 검증, 메트릭 수집

## 🔄 Latest Updates (2025-11)

- **실시간 메트릭 API 추가**: `GET /metrics/topics/{topic_name}/live` 엔드포인트가 Kafka AdminClient를 통해 파티션 상세를 즉시 반환합니다. TTL 캐시 없이 호출 시점 기준 데이터를 제공합니다.
- **초기 스냅샷 보강**: FastAPI `lifespan` 훅이 클러스터별 스냅샷이 없으면 `manual_sync_metrics` 태스크를 자동 트리거하여 DB 스냅샷 공백을 방지합니다 (see `app/main.py`).

## 📁 Structure

```
topic/
├── domain/
│   ├── models/                    # Domain 모델
│   │   ├── __init__.py
│   │   └── metrics.py            # 메트릭 도메인 모델
│   ├── policies/                  # 정책 엔진
│   │   ├── naming/               # Naming 규칙
│   │   ├── guardrail/            # Guardrail 검증
│   │   ├── management/           # 정책 관리
│   │   └── validation/           # 정책 검증
│   ├── repositories/              # Repository 인터페이스
│   │   └── interfaces.py         # IAuditRepository, IPolicyRepository 등
│   └── services.py               # Domain 서비스
│
├── application/
│   ├── batch_use_cases/          # 배치 작업 Use Cases
│   │   ├── batch_apply.py
│   │   ├── batch_apply_yaml.py
│   │   ├── batch_dry_run.py
│   │   └── bulk_delete.py
│   └── topic_use_cases/          # 토픽 관리 Use Cases
│       ├── get_topic_metrics.py
│       ├── list_topics.py
│       └── policy_crud.py
│
├── infrastructure/
│   ├── adapter/                   # 외부 시스템 Adapter
│   │   ├── kafka_adapter.py      # Kafka Admin 작업
│   │   ├── kafka_metric_adapter.py  # Kafka 메트릭 기반 클래스
│   │   └── metrics/              # 메트릭 수집기
│   │       ├── partition.py
│   │       ├── storage.py
│   │       ├── cluster.py
│   │       ├── leader.py
│   │       └── collector.py      # 통합 수집기
│   ├── models/                    # ORM 모델
│   │   ├── topic_models.py       # Topic 관련
│   │   ├── audit_models.py       # Audit 로그
│   │   ├── policy_models.py      # Policy
│   │   └── metrics_models.py     # Metrics 스냅샷
│   └── repository/                # Repository 구현체
│       ├── audit_repository.py
│       ├── mysql_repository.py
│       └── policy_repository.py
│
└── interface/
    ├── routers/                   # API 라우터
    │   ├── topic_router.py       # 토픽 배치 작업
    │   ├── policy_router.py      # 정책 관리
    │   └── metrics_router.py     # 메트릭 조회
    ├── schemas/                   # Pydantic DTO
    │   ├── common.py
    │   ├── request.py
    │   ├── response.py
    │   ├── policy.py
    │   └── metrics_schemas.py
    ├── helpers/                   # 헬퍼 함수
    │   ├── error_translator.py
    │   ├── report_generator.py
    │   └── yaml_parser.py
    └── adapters.py               # DTO ↔ Domain 변환
```

## 📊 Key Models

### Topic Management
- **DomainTopicSpec**: 토픽 생성/수정 스펙
- **DomainTopicPlan**: Dry-run 실행 계획
- **DryRunReport**: 검증 결과 리포트
- **TopicMetadata**: 토픽 메타데이터 (owners, doc, tags, environment, SLO/SLA)

### Metrics
- **TopicMetrics**: 전체 토픽 메트릭 스냅샷
- **PartitionDetails**: 파티션 상세 정보 (크기, offset lag)
- **ClusterMetrics**: 클러스터 지표 (broker 수, 전체 파티션 수)
- **TopicMeta**: 토픽별 메타데이터

### Policy
- **PolicyType**: `naming` (네이밍 규칙), `guardrail` (설정 검증)
- **PolicyStatus**: `draft` → `active` → `archived`
- **StoredPolicy**: 정책 버전 관리 (policy_id + version)

## 📈 Metrics Collection

### 수집 메트릭
1. **Partition Metrics**: 파티션 수, 파티션별 크기
2. **Storage Metrics**: 전체/평균/최대/최소 파티션 크기
3. **Cluster Metrics**: 브로커 수, 파티션-브로커 비율
4. **Leader Distribution**: 브로커별 리더 파티션 분포

### 수집 방식
- **비동기 수집**: `asyncio.to_thread`로 Kafka AdminClient 호출
- **TTL 캐싱**: 15초 기본 (설정 가능)
- **자동 갱신**: TTL 만료 시 자동으로 재수집

### Collector 구조
```
BaseMetricsCollector (kafka_metric_adapter.py)
  ↓ 상속
├─ PartitionMetricsCollector
├─ StorageMetricsCollector
├─ ClusterMetricsCollector
└─ LeaderDistributionCollector
  ↓ 통합
TopicMetricsCollector (facade)
```

## 🔐 Naming Policies

| Strategy | Pattern |
| **Permissive** | Free-form |
| **Balanced** | `{env}.{domain}.{resource}` |
| **Strict** | `{env}.{classification}.{domain}.{resource}.{version}` |
| **Custom** | User-defined YAML |

## Guardrail Policies

Environment별 config 검증 (min_insync_replicas, replication_factor 등)

## 🔌 API Endpoints

### Topic Operations (`/api/v1/topics`)
- `GET /` - 토픽 목록 조회 (`?cluster_id=`)
- `POST /batch/upload` - YAML 업로드 & dry-run
- `POST /batch/dry-run` - Dry-run (JSON)
- `POST /batch/dry-run/report` - Dry-run 리포트 다운로드 (CSV/JSON)
- `POST /batch/apply-yaml` - YAML 기반 배치 적용
- `POST /batch/apply` - 배치 적용
- `POST /bulk-delete` - 일괄 삭제
- `PATCH /{name}/metadata` - 메타데이터 업데이트
- `DELETE /{name}` - 토픽 삭제

### Policy Management (`/api/v1/policies`)
- `GET /` - 정책 목록 조회
- `GET /active/environment` - 환경별 활성 정책 조회
- `POST /` - 정책 생성
- `GET /{id}` - 정책 조회
- `GET /{id}/active` - 활성 정책 조회
- `GET /{id}/versions` - 정책 버전 히스토리
- `PUT /{id}` - 정책 수정 (새 버전 생성)
- `POST /{id}/activate` - 정책 활성화
- `POST /{id}/archive` - 정책 아카이브
- `POST /{id}/rollback` - 정책 롤백
- `DELETE /{id}` - 정책 삭제
- `DELETE /{id}/all` - 정책 전체 삭제

### Metrics (`/metrics`)
- `GET /topics` - 전체 토픽 분포 요약
- `GET /topics/{topic_name}` - 특정 토픽 메트릭
- `GET /cluster` - 클러스터 메트릭
- `POST /refresh` - 메트릭 스냅샷 강제 갱신

## 🏗️ Architecture Principles

### Clean Architecture (DDD)
- **Domain**: 비즈니스 로직, 정책, 도메인 모델 (외부 의존성 없음)
- **Application**: Use Case 구현 (도메인 조율)
- **Infrastructure**: 외부 시스템 연동 (Kafka, DB, Adapter)
- **Interface**: API, DTO, 라우터

### 의존성 규칙
- ✅ 모든 import는 **절대 경로** 사용 (`app.topic.domain...`)
- ✅ Infrastructure → Domain (의존)
- ✅ Application → Domain (의존)
- ✅ Interface → Application, Domain (의존)
- ❌ Domain → Infrastructure/Application (금지)

### 주요 패턴
- **Repository Pattern**: DB 추상화
- **Adapter Pattern**: Kafka, 외부 API 추상화
- **Use Case Pattern**: 비즈니스 로직 캡슐화
- **DTO Pattern**: Interface ↔ Domain 변환

## 🔧 Dependencies

- **shared**: Database (MySQL), Error handlers
- **cluster**: ConnectionManager (Kafka AdminClient 관리)
