# **Backend Job Spec — Kafka Governance & Batch Automation**

> 목적: AKHQ(UI)를 유지하면서
> 
> 
> **정책·배치·거버넌스·API**
> 

---

## **0. 원칙**

- UI 기능 복제 금지(단건 CRUD, 브라우징은 AKHQ 위임)
- **정책 우선(Policy-First)**: 모든 변경은 정책 엔진을 통과
- **배치 지향(Batch-First)**: YAML/JSON 선언 → Dry-run → 승인 → Apply
- **감사 가능(Auditable)**: 모든 변경은 Audit Trail 저장

---

## **1. 범위(Scope)**

**MVP(출발점) — 기능 4개**

1. **토픽 배치 관리**: 여러 토픽 동시 생성/수정/삭제 (YAML/JSON)
2. **스키마 배치 관리**: 여러 스키마 동시 등록/업데이트 (업로드/경로 참조)
    - **스키마 타입 지원**: **Avro**, **JSON Schema**, **Protobuf**
3. **스키마 호환성 검증**: Backward/Forward/Full 모드, dry‑run 시 리포트
4. **스키마 변경 영향도 분석**: subject↔topic 매핑 + 소비자(옵션) 조회

**제외(Non‑goals)**

- UI 콘솔(브라우징/라그 시각화) → AKHQ 사용
- 엔터프라이즈 RBAC/SSO(향후)

---

## **2. 아키텍처 개요**

- **FastAPI** (Domain → Application → Interface → Infra)
- Kafka AdminClient, Schema Registry Client(Confluent)
    - SchemaRegistryClient 는 **CachedSchemaRegistryClient 를 사용한다**
- DB: PostgreSQL/MySQL(메타데이터, 정책, 감사)
- Auth: Service Token/JWT + RBAC(Role: viewer, editor, approver, admin)
- Observability: 구조화 로그(JSON), Prometheus metrics, Sentry

```
Client(GitOps/CI) ─▶ Backend API ──▶ Policy Engine ──▶ Kafka Admin / Schema Registry
                                   └─▶ Metadata DB / Audit Log ──▶ Slack/Jira
```

---

## **3. 정책(Policy) 사양**

### **3.1 네이밍 규칙**

- 정규식: ^((dev|stg|prod)\.)[a-z0-9._-]+$
- 금지 접두사: tmp., test.(prod), 예약어 목록 유지

### **3.2 환경별 가드레일(예시)**

- prod: replication.factor ≥ 3, min.insync.replicas ≥ 2
- 압축: 기본 zstd
- retention: prod 최소 7d, dev 최대 3d
- 파티션: 최소/최대(팀별 가이드)

### **3.3 위반 처리**

- DRY‑RUN: 200 + violations[]
- APPLY: 409/422 + 해결 가이드

---

## **4. 스키마 호환성(Avro) 규칙**

- 기본 모드: **FULL**(prod), **BACKWARD**(dev/stg)
- 안전한 진화: 필드 추가 시 default 필수, 타입 변경 금지, 삭제 금지(Deprecated 플래그)
- 등록 시 자동 검사: Registry compatibility 호출 + 자체 diff 리포트

---

## **5. 배치 스펙(YAML) — 초안**

### **5.1 토픽 배치**

```
kind: TopicBatch
env: prod
changeId: 2025-09-25_001
items:
  - name: prod.orders.created
    action: upsert
    config:
      partitions: 12
      replicationFactor: 3
      cleanup.policy: compact
      compression.type: zstd
      retention.ms: 604800000  # 7d
    metadata:
      owner: team-commerce
      sla: P99<200ms
      doc: https://wiki/streams/orders
  - name: prod.tmp.experiment
    action: delete
    reason: retired
```

### **5.2 스키마 배치(Avro)**

```
kind: SchemaBatch
env: prod
subjectStrategy: TopicNameStrategy  # (TopicValue/Key)
items:
  - subject: prod.orders.created-value
    type: AVRO
    compatibility: FULL
    schema: |
      {"type":"record","name":"Order","fields":[
        {"name":"id","type":"string"},
        {"name":"email","type":"string","default":""}
      ]}
    metadata:
      owner: team-commerce
      doc: https://wiki/schemas/order
```

---

## **6. API 설계(초안)**

### **6.1 토픽**

- POST /v1/topics/batch/dry-run → 계획/위반 리포트 생성
- POST /v1/topics/batch/apply → 정책 통과 시 적용(승인 토큰 필요)
- GET /v1/topics/{name} → Kafka + 메타데이터 조합 응답
- GET /v1/topics/plan/{changeId} → 과거 계획 조회

### **6.2 스키마**

- POST /v1/schemas/batch/dry-run
    - 입력: items[].{ subject, **type: AVRO|JSON|PROTOBUF**, source{ inline|file|yaml }, compatibility? }
    - 동작: 파싱 → 정규화(canonical) → **호환성 검증** → **영향도 분석** → 리포트
- POST /v1/schemas/batch/apply
    - 동작: dry‑run 결과 승인 시 실제 등록 + MinIO 저장 + 메타DB 기록
- POST /v1/schemas/upload (multipart)
    - .avsc / .json / .proto 단건 또는 번들(zip)
    - **Avro는 YAML 정의 파일과 .avro 파일 다중 업로드 모두 지원**
    - 예: a.avro, b.avro, c.avro 파일 업로드 가능

### **6.3 정책/카탈로그/감사**

- GET/PUT /v1/policies
- GET /v1/catalog/topics?subject=...
- GET /v1/audits?...
- GET/PUT /v1/policies
- GET /v1/catalog/topics?subject=...
- GET /v1/audits?...
    
    /카탈로그/감사
    
- GET/PUT /v1/policies
- GET /v1/catalog/topics?owner=team-x&tag=pii
- GET /v1/audits?target=topic&name=prod.orders.created

### **응답 예시(dry‑run)**

```
{
  "env": "prod",
  "changeId": "2025-09-25_001",
  "plan": [
    {"name":"prod.orders.created","action":"ALTER","diff":{"partitions":"8→12"}},
    {"name":"prod.tmp.experiment","action":"DELETE"}
  ],
  "violations": [
    {"name":"prod.tmp.experiment","rule":"forbid.prefix","message":"'tmp' is forbidden in prod"}
  ]
}
```

### 6.4 Pydantic 검증 규칙

- **모든 DTO/Request 모델은 Pydantic v2 기반**
- `Strict*` 타입 사용 (StrictStr, StrictInt 등)
- ContainsModel 적극 사용 or `Field(..., min_length, max_length, pattern, strict=True)` 등 제약 필수
- `Annotated` + `constr`, `conint` 등 제약 모델 적극 사용
- 중첩 모델 시 `model_config = ConfigDict(extra='forbid', str_min_length=1, str_strip_whitespace=True)`
- 배치 입력은 리스트 내 각 항목에 대해 **엄격한 schema 검증** 수행
- 잘못된 입력은 422 반환, 에러 메시지에 위반 필드/규칙 상세 포함

---

## **7. 내부 모듈 설계(DDD)**

- **Domain**: TopicSpec, SchemaSpec, Policy, Violation, Plan
- **Application**: BatchPlanner, PolicyEvaluator, SchemaCompatibilityService
- **Interface**: REST Controllers(FastAPI), DTO(Pydantic v2)
- **Infra**: KafkaAdminAdapter, SchemaRegistryAdapter, MetadataRepo(SQL), AuditRepo

---

## **8. 보안/권한**

- JWT(Service Token), x-request-id 필수
- RBAC: viewer/editor/approver/admin
- Approve‑token 또는 Reviewer 서명 필요(배치 apply)

---

## **9. 관측/로깅**

- JSON 로그 + 요청/응답 correlation(id)
- Metrics: policy_violations_total, batch_apply_latency_ms, kafka_api_errors_total
- Error tracking: Sentry DSN

---

## **10. 테스트 전략**

- 단위: 정책/플래너/호환성
- 통합: Testcontainers(로컬 Kafka/Registry)
- 계약: OpenAPI → Dredd/schemathesis
- e2e: 배치 dry‑run→apply→검증 시나리오

---

## **11. 마이그레이션/운영**

- 초기: **Read‑only 모드**로 도입(기존 상태 카탈로그 동기화)
- 점진적: dry‑run만 허용 → 일부 네임스페이스 apply → 전사 확대
- 롤백: 변경 plan 기반 역작업 생성(가능 범위 명시)

---

## **12. 수용 기준(AC)**

- 토픽/스키마 배치 **dry‑run**이 정책 위반을 정확히 리포트
- **apply**가 idempotent하고, 감사로그에 전부 기록
- 스키마 등록 시 **호환성 실패**가 재현/차단됨
- GitOps 파이프라인에서 JSON 리포트 사용 가능

---

## **13. 일정(러프)**

- **W1**: 도메인/정책/DTO, dry‑run 토픽
- **W2**: 토픽 apply + 감사/카탈로그
- **W3**: 스키마 호환성 + 배치 apply
- **W4**: RBAC/알림/GitOps, 성능/경계 테스트

---

## **14. application directort 규격**

```
app 
├── 각 성격의 맞는 모듈 이름을 정해주세요 
│   ├── application
│   ├── domain
│   │   └── repository
│   ├── infrastructure
│   └── interface
.
.
.
.

```

---

## **15. 운영 가이드(요지)**

- 배포 전 정책을 **경고→차단** 단계로 점진 강화
- prod는 **FULL** 호환성, dev/stg는 BACKWARD 권장
- 모든 변경은 **changeId**로 추적, 외부 이슈 키와 연동(Jira)