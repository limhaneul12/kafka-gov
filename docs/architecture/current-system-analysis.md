# Current System Analysis (repository snapshot: 2026-04-15)

## Executive summary

이 저장소의 **현재 shipped/runtime 기준 제품 정체성**은 `schema governance + connection management + shared audit/approval backbone`입니다.

핵심 결론은 다음과 같습니다.

1. **실제 런타임은 `shared`, `cluster`, `schema` 세 모듈만 올라와 있습니다.** FastAPI는 이 세 라우터만 등록하고 있고(`app/main.py:112-126`), DI wiring도 동일 범위만 대상으로 합니다(`app/container.py:11-18`).
2. **토픽 런타임은 이미 제거되었고, topic은 read-only naming hint로만 남아 있습니다.** 남아 있는 표면은 `/api/v1/schemas/known-topics/{subject}` 하나이며(`app/schema/interface/routers/governance_router.py:66-86`), 프로젝트 자체 리뷰 문서도 이를 명시합니다(`docs/topic-removal-review.md:12-19`).
3. **다만 “Kafka 흔적”은 아직 꽤 강합니다.** Kafka broker connection CRUD/test는 여전히 활성 API/UI입니다(`app/cluster/interface/routers/broker.py:15-266`, `frontend/src/services/api.ts:96-119`, `frontend/src/pages/Connections/index.tsx:13-21`). 대시보드도 Kafka cluster 수를 먼저 보여줍니다(`frontend/src/pages/governance/Dashboard.tsx:309-318`, `390-398`).
4. **`product`, `contract`, `governance`, `lineage`는 target-state용 도메인/유스케이스 골격은 있지만 아직 production runtime이 아닙니다.** 해당 모듈들의 interface/infrastructure 패키지는 비어 있고(`app/product/interface/routers/__init__.py`, `app/contract/interface/routers/__init__.py`, `app/governance/interface/routers/__init__.py`, `app/lineage/interface/routers/__init__.py` all 0 lines), 메인 앱에도 연결되지 않습니다.

> 따라서 신규 팀 온보딩 시 이 시스템을 **“Kafka 운영툴”도 아니고 “완성된 데이터 거버넌스 플랫폼”도 아닌, 현재는 schema governance 중심으로 정리된 과도기 제품**으로 이해하는 것이 가장 정확합니다.

---

## 1. 현재 실제로 동작하는 시스템 범위

### 1.1 Backend runtime

| 영역 | 현재 상태 | 근거 |
| --- | --- | --- |
| App entry | FastAPI 앱은 shared/cluster/schema 라우터만 등록 | `app/main.py:112-126` |
| DI composition root | wiring 대상도 shared/cluster/schema 패키지뿐 | `app/container.py:11-18`, `app/container.py:20-37` |
| Shared backbone | audit history + approval request API 제공 | `app/shared/interface/router.py:17-210`, `app/shared/container.py:46-90` |
| Cluster surface | Kafka broker / Schema Registry connection CRUD, activate, test 제공 | `app/cluster/interface/routers/__init__.py:9-13`, `app/cluster/interface/routers/broker.py:15-266`, `app/cluster/interface/routers/registry.py:15-216` |
| Schema surface | upload, sync, search, detail, history, rollback plan, governance dashboard, known-topic hints 제공 | `app/schema/interface/router.py:7-11`, `app/schema/interface/routers/management_router.py:57-322`, `app/schema/interface/routers/governance_router.py:29-145` |

### 1.2 Frontend shipped surface

| 화면/라우트 | 현재 상태 | 근거 |
| --- | --- | --- |
| Routed pages | Dashboard, History, Schemas, Schema Detail, Connections, Schema Policies만 존재 | `frontend/src/App.tsx:15-27` |
| Sidebar | Schema Registry / Governance / Connections 중심 | `frontend/src/components/layout/Sidebar.tsx:22-40` |
| Topic UI | shipped navigation에서 제거됨 | `tests/test_e2e_full_system.py:12-19`, `docs/topic-removal-review.md:17-19` |
| Known topic display | Schema detail 안의 read-only contextual hint로만 남음 | `frontend/src/pages/schemas/SchemaDetail.tsx:145-149`, `407-442` |

### 1.3 현재 핵심 기능(신규 팀 기준 요약)

1. **Schema Registry governance**
   - 스키마 업로드, sync, 검색, 상세 조회, 이력, 변경 계획, rollback 계획
   - 근거: `app/schema/interface/routers/management_router.py:57-322`, `app/schema/interface/routers/governance_router.py:29-145`
2. **Connection registry / operational prerequisites**
   - Kafka broker와 Schema Registry 연결 정보를 등록/테스트/활성화
   - 근거: `app/cluster/interface/routers/broker.py:34-266`, `app/cluster/interface/routers/registry.py:36-216`
3. **Audit / approval backbone**
   - 최근 활동, 이력, 승인 요청 CRUD/approve/reject
   - 근거: `app/shared/interface/router.py:42-210`
4. **Naming-derived topic hints only**
   - topic은 authoritative runtime object가 아니라 schema naming에서 파생되는 힌트
   - 근거: `app/schema/interface/routers/governance_router.py:66-86`, `frontend/src/pages/schemas/SchemaDetail.tsx:430-438`, `tests/test_schema_known_topic_names.py:48-57`

---

## 2. 시스템 구조 해석

### 2.1 현재 구조를 한 줄로 정리하면

`Frontend (schema/governance UI) -> FastAPI -> shared + cluster + schema -> infra(kafka/schema-registry adapters, DB, Redis)`

### 2.2 코드 기준 구조 포인트

- **shared는 공통 백본**입니다.
  - DB manager, Redis, audit repository, approval repository를 관리합니다.
  - 근거: `app/shared/container.py:26-90`
- **cluster는 외부 연결의 entry point**입니다.
  - Kafka cluster repo, Schema Registry repo, ConnectionManager singleton을 제공합니다.
  - 근거: `app/cluster/container.py:28-56`
- **schema는 현재 제품의 중심 도메인**입니다.
  - 대부분의 use case가 `cluster.connection_manager`를 받아 schema registry client를 획득합니다.
  - 근거: `app/schema/container.py:32-155`
- **infra seam은 이미 `app/infra/kafka`로 추출되어 있습니다.**
  - ConnectionManager와 Confluent Schema Registry adapter가 이 경계에 있습니다.
  - 근거: `app/infra/kafka/connection_manager.py:17-235`, `app/infra/kafka/schema_registry_adapter.py:29-307`

### 2.3 하지만 seam cleanup은 아직 끝나지 않았습니다

PRD는 “shared Kafka/Schema adapter 생성 책임을 application 밖으로 이동”해야 한다고 적고 있습니다(`docs/features/real-time-data-governance-system.md:198-200`). 그런데 실제 schema use case 여러 곳이 여전히 application layer에서 adapter를 직접 생성합니다.

- `app/schema/application/use_cases/management/upload.py:97-107`
- `app/schema/application/use_cases/management/plan_change.py:59-62`
- `app/schema/application/use_cases/governance/history.py:48-53`
- 추가 다수: `rg "ConfluentSchemaRegistryAdapter\(" app/schema/application/use_cases` 결과 기준

즉, **공용 infra seam은 열렸지만 아직 application/service 계층에 adapter 생성 흔적이 남아 있는 상태**입니다.

---

## 3. 레거시 Kafka 흔적

### 3.1 이미 제거된 것

| 제거된 것 | 근거 |
| --- | --- |
| `app/topic` 런타임 모듈 | `docs/topic-removal-review.md:17-19` |
| `/topics`, `/consumers`, `/ws` shipped UI 경로 | `docs/topic-removal-review.md:17-19`, `tests/test_e2e_full_system.py:17-19` |
| 토픽 메트릭/파티션 중심 DB 테이블 | `migrations/versions/6f5f0c8f6c1f_drop_topic_module_tables.py:13-38` |

### 3.2 아직 남아 있는 Kafka-centric 흔적

| 흔적 유형 | 내용 | 근거 |
| --- | --- | --- |
| 브랜드/문구 | 앱 타이틀과 API 이름이 아직 Kafka Governance/Kafka Gov 중심 | `app/main.py:61-63`, `app/main.py:133`, `frontend/src/components/layout/Sidebar.tsx:19` |
| 활성 기능 | Kafka broker connection CRUD/test가 아직 first-class shipped surface | `app/cluster/interface/routers/broker.py:34-266`, `frontend/src/services/api.ts:96-106`, `frontend/src/pages/Connections/index.tsx:17-20`, `48-51`, `105-112` |
| 대시보드 UX | Dashboard가 schema보다 먼저 Kafka cluster 수를 보여줌 | `frontend/src/pages/governance/Dashboard.tsx:309-318`, `390-398` |
| 공유 타입/주석 | audit activity 설명과 일부 타입이 아직 `topic` vocabulary를 포함 | `app/shared/domain/repositories.py:17-18`, `43-45`; `app/shared/domain/models/value_objects.py:14-20`; `app/shared/types.py:81-88` |
| 프런트 유틸 | topic 이름/partition/replication validation 유틸이 남아 있음 | `frontend/src/utils/validation.ts:25-47`, `93-139`; `frontend/src/utils/format.ts:130-145` |
| 자산/문서 잔재 | topic 이미지/리뷰 문서/삭제 migration이 남아 있음 | `image/topic_list.png`, `image/topic_detail.png`, `docs/topic-removal-review.md`, `migrations/versions/6f5f0c8f6c1f_drop_topic_module_tables.py` |

### 3.3 중요한 해석

“Kafka 흔적이 남아 있다”는 말은 두 층으로 나뉩니다.

1. **합리적으로 남아 있는 것**: Schema Registry를 쓰기 위한 Kafka/registry connection 관리, naming-derived topic hints
2. **정리하지 않으면 새 팀을 헷갈리게 하는 것**: Kafka-first naming, dashboard emphasis, dormant topic vocabulary, 남아 있는 util/comment/image 자산

---

## 4. 현재 핵심 기능 vs 목표 상태의 거리

### 4.1 현재 핵심 기능

현재 실제로 가장 완성도 높은 축은 아래 3개입니다.

1. **Schema governance**
   - README도 이 방향으로 재정의되어 있음 (`README.md:75-83`, `95-103`, `188-202`)
2. **Shared approval/audit backbone**
   - `shared` container/router가 실제로 런타임에 연결됨 (`app/shared/container.py:46-90`, `app/shared/interface/router.py:42-210`)
3. **Cluster-based dynamic connection management**
   - DB 기반으로 Kafka/Registry 연결을 관리하고 runtime client를 동적으로 생성 (`app/shared/container.py:26-32`, `app/cluster/container.py:50-56`, `app/infra/kafka/connection_manager.py:45-235`)

### 4.2 아직 목표 상태에 머물러 있는 것

`docs/features/real-time-data-governance-system.md`는 현재 repo를 **target-state PRD**라고 명시하며(`docs/features/real-time-data-governance-system.md:9-19`), 다음을 아직 runtime 밖으로 봅니다.

- Product (`:174-177`, `202-210`)
- Contract (`:176-178`, `211-218`)
- Governance decision layer (`:220-227`)
- Lineage (`:228-235`)

코드도 이 설명과 일치합니다.

- `DataProduct` aggregate와 use case는 존재 (`app/product/domain/models/data_product.py:66-208`, `app/product/application/use_cases/create_product.py:19-71`)
- `DataContract` aggregate와 use case는 존재 (`app/contract/domain/models/data_contract.py:88-276`, `app/contract/application/use_cases/create_contract.py:21-72`)
- governance/lineage 도메인 모델과 use case는 존재 (`app/governance/domain/models/governance.py:95-284`, `app/lineage/domain/models/lineage.py:58-206`)
- 하지만 interface/infrastructure는 비어 있고 메인 앱에 wiring되지 않음 (`app/product/interface/routers/__init__.py`, `app/contract/interface/routers/__init__.py`, `app/governance/interface/routers/__init__.py`, `app/lineage/interface/routers/__init__.py` all 0 lines)

즉, **도메인 설계는 다음 단계까지 이미 앞서가 있지만, shipped product는 아직 그 수준까지 올라오지 않은 상태**입니다.

---

## 5. 신규 팀 기준 우선 정리 필요 영역

### P0. 제품 경계부터 명확히 정리

**질문:** 이 제품의 현재 1차 목적이 `schema governance`인지, `Kafka/Schema connection admin`까지 포함한 control plane인지 먼저 결정해야 합니다.

- 이유: 실제 UI/API는 Kafka broker 관리가 아직 전면에 있고(`frontend/src/pages/Connections/index.tsx:17-20`, `105-112`), 문서/구두 배경은 “Kafka 기능 대부분 제거” 쪽으로 읽힐 수 있습니다.
- 권장 정리:
  1. Kafka broker 관리를 **핵심 기능**으로 유지할지,
  2. 아니면 **schema governance를 위한 prerequisite/admin 영역**으로 후퇴시킬지 결정

### P1. “현재 런타임” 문서와 온보딩 메시지 통합

신규 팀이 가장 먼저 알아야 할 것은 다음 2문장입니다.

- 현재 shipped runtime은 `schema governance + connection management + shared audit/approval`이다.
- Product/Contract/Governance/Lineage는 아직 target-state skeleton이다.

이 분석 문서는 그 갭을 메우기 위한 첫 정리이며, 기존 onboarding/architecture 문서에서 같은 메시지를 반복적으로 통일하는 것이 좋습니다.

### P1. schema application layer의 adapter 직접 생성 제거

- 이유: PRD의 foundation seam cleanup 항목과 현재 코드가 아직 불일치
- 근거: `docs/features/real-time-data-governance-system.md:198-200`, `app/schema/application/use_cases/management/upload.py:97-107`, `app/schema/application/use_cases/management/plan_change.py:59-62`, `app/schema/application/use_cases/governance/history.py:48-53`
- 기대 효과: 런타임 경계 명확화, 테스트 단순화, future Product/Contract integration 준비

### P1. dormant module의 상태를 명시적으로 관리

`product/contract/governance/lineage`는 지금 상태로는 “없는 기능”도 아니고 “동작하는 기능”도 아닙니다. 이 중간 상태가 가장 혼란을 줍니다.

선택지는 둘입니다.

1. **productionization 우선순위를 올려 실제 runtime에 연결**
2. **당분간은 experimental/target-state 영역으로 명확히 표시**

현재로서는 PRD도 후자를 말하고 있으므로, 적어도 문서/디렉터리 설명에서 상태를 명확히 표시하는 편이 좋습니다.

### P2. Kafka/topic 잔재 vocabulary 정리

- shared audit comment의 `topic | schema` 설명
- frontend util의 topic/partition/replication helper
- topic 이미지/자산
- Kafka-first naming이 남은 UI copy

이 부분은 기능 오작동보다는 **인지 부채**에 가깝지만, 신규 팀 해석 비용을 크게 높입니다.

### P2. Dashboard/Connections의 정보 우선순위 재정렬

현재 dashboard는 cluster count를 먼저 보여주고(`frontend/src/pages/governance/Dashboard.tsx:390-398`), connections 기본 탭도 kafka입니다(`frontend/src/pages/Connections/index.tsx:17-20`).

프로젝트가 schema governance 중심이라면,

- dashboard first card를 schema/registry 상태로 바꾸거나
- connections 기본 탭을 registry로 바꾸거나
- Kafka 영역을 “advanced/admin”으로 내리는 것이 더 현재 전략과 맞습니다.

---

## 6. 최종 판단

### 지금 이 시스템을 어떻게 설명해야 하나?

가장 정확한 설명은 다음입니다.

> **Kafka-Gov는 현재 “schema governance 중심 control plane”이다.**
> Kafka topic runtime은 제거되었고 topic은 naming-derived read-only hint로만 남아 있다. 
> 그러나 Kafka broker/Schema Registry connection 관리와 Kafka-centric naming/UX 흔적은 여전히 남아 있다. 
> Product/Contract/Governance/Lineage는 다음 단계 아키텍처 방향을 보여주는 설계 골격이지만, 아직 shipped runtime은 아니다.

### 신규 팀이 당장 기억해야 할 3가지

1. **지금 당장 믿어야 할 코드 경계는 `shared + cluster + schema`뿐이다.**
2. **topic은 주 기능이 아니라 context hint다.**
3. **다음 큰 정리는 feature 추가보다 boundary cleanup과 target-state productionization 순서로 가야 한다.**

