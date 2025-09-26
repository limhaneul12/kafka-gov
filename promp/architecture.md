## **[Update — 2025-09-25] Pure Clean Architecture 확정 및 AVSC 지원/스토리지 설계**

### **A. 아키텍처 결정 (순수 CA)**

- 레이어 고정: **module/**
    - application/ — UseCase 조합, 트랜잭션 경계, orchestrator
    - domain/ — 엔티티, 값 객체, 순수 규칙(정책은 domain 내부 함수/서비스로 유지)
    - infra/ — Adapters (Kafka Admin, Schema Registry, MySQL Repos, MinIO Client)
    - interface/ — FastAPI routers & DTO(Pydantic v2), auth, validation
- DDD 전술은 **도메인 규칙 캡슐화 수준**까지만 사용, 바운디드 컨텍스트 분리는 보류

### **B. 스토리지/데이터베이스**

- **Object Storage: MinIO** (원본 .avsc/번들 보관)
    - 버킷: schemas-{env} (예: schemas-dev, schemas-stg, schemas-prod)
    - 오브젝트 키: {subject}/{version}/{fingerprint}/bundle.zip 또는 {subject}/{version}/schema.avsc
    - 메타데이터 태그: owner, doc, uploaded_by, change_id, canonical_hash
- **RDBMS: MySQL** (메타데이터/감사/정책)
    - 테이블 초안:
        - schema_registry_meta(subject PK, latest_version, compatibility_mode, owner, doc_url, updated_at)
        - schema_versions(id PK AI, subject FK, version, canonical_hash, storage_url, uploaded_by, created_at)
        - topic_catalog(name PK, env, owner, doc_url, created_at, updated_at)
        - batch_plan(change_id PK, env, kind ENUM('TOPIC','SCHEMA'), spec JSON, created_by, created_at)
        - audit_log(id PK AI, target ENUM('TOPIC','SCHEMA'), name, action, actor, status, message, snapshot JSON, created_at)
        - policies(env PK, rules JSON, updated_by, updated_at)

### **C. 환경변수/설정 (interface → infra 주입)**

```
MINIO_ENDPOINT: http://minio:9000
MINIO_ACCESS_KEY: ...
MINIO_SECRET_KEY: ...
MINIO_SECURE: false
SCHEMA_REGISTRY_URL: http://schema-registry:8081
MYSQL_DSN: mysql+pymysql://user:pass@mysql:3306/kafka_gov
DEFAULT_COMPATIBILITY: BACKWARD  # prod는 FULL로 override
```

### **D. API 확정(Backend 전용, UI는 AKHQ 위임)**

- **스키마 업로드(AVSC/번들)**
    - POST /v1/schemas/upload — multipart, files[] 지원 (.avsc 1개 또는 zip)
    - POST /v1/schemas/batch/dry-run — items[].source.type in [inline, file]
    - POST /v1/schemas/batch/apply — Registry 등록 + MinIO 보관 + MySQL 기록
- **토픽 배치** (기존과 동일)
    - POST /v1/topics/batch/dry-run
    - POST /v1/topics/batch/apply

응답 공통 필드: changeId, plan[], violations[], applied[], skipped[], auditId

### **E. AVSC 처리 파이프라인 (순수 CA 레이어 배치)**

1. **interface**: 파일 수신 → DTO 변환 → application.UploadSchemaBundle 유스케이스 호출
2. **application**:
    - 번들 해석/루트 결정 → **domain.canonicalize()** 호출 → **registryAdapter.checkCompatibility()**
    - idempotency 체크(이미 동일 canonical_hash 등록 여부)
    - **registryAdapter.register()** 성공 시 → **minioAdapter.putObject()**, **metadataRepo.recordVersion()**, **auditRepo.write()**
3. **domain**:
    - canonicalize(schema_dict) -> str
    - fingerprint(canonical_str) -> hex
    - diff(old_schema, new_schema) -> DomainDiff
4. **infra**:
    - SchemaRegistryAdapter (Confluent REST)
    - MinioAdapter (boto3 혹은 minio-py)
    - MySql*Repo (SQLAlchemy 2.0, async)

### **F. 정책(호환성/네이밍) — domain 규칙**

- validate_topic(env, name, config) : 정규식/가드레일 위반 수집
- validate_schema_compat(subject, mode, new_schema, latest_schema) : BACKWARD/FULL 검사 + 세부 리포트
- prod에는 mode=FULL 강제, dev/stg는 mode=BACKWARD

### **G. 마이그레이션/초기화**

- Alembic 스크립트: 위 MySQL 테이블 생성
- 초기 정책 시드: policies.rules에 네이밍/가드레일 JSON 저장
- MinIO 버킷 자동 생성(usecase: EnsureBuckets)

### **H. 수용 기준(AC) 보강**

- .avsc 단건/zip 번들 업로드가 정상 파싱·정규화·저장·등록된다
- 동일 canonical_hash 재업로드 시 **중복 등록 방지** 및 already-registered 반환
- prod에서 호환성 위반 시 422와 필드 단위 diff 리포트 제공
- 모든 등록/배치는 **MinIO URL + audit_log 링크**를 반환한다

### **I. 작업 순서(실행 To‑Do)**

1. **infra**: MinioAdapter, SchemaRegistryAdapter, MySqlRepos 스텁 / 헬스체크
2. **domain**: canonicalize/fingerprint/diff/validators
3. **application**: UploadSchemaBundle, SchemaBatchDryRun/Apply, TopicBatchUseCases
4. **interface**: /schemas/upload, batch endpoints, 예외/에러맵핑
5. **migration**: Alembic 초기 리비전 + 시드 정책
6. **obs**: JSON 로그, Prometheus 메트릭 노출(/metrics)

### **J. 예시 오브젝트 키 설계**

- 신규 등록: prod.orders.created-value/0007/5b2c.../bundle.zip
- 단건 파일: prod.orders.created-value/0007/schema.avsc
- 인덱스 문서(optional): prod.orders.created-value/index.json (최신 버전/URL/해시)

### **K. 보안/권한**

- 업로드/적용은 role in [editor, approver, admin]만 허용
- 모든 요청에 X-Request-Id 필요, 감사에 저장
- MinIO presigned URL로 읽기 권한 위임(다운로드 전용)