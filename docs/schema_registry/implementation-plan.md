# Schema Registry Governance Implementation Plan

## Overview

이 문서는 현재 스키마 레지스트리 중심 기능을 **조직 맞춤형 Schema Governance**로 확장하기 위한 구현 계획입니다.

핵심 방향은 다음과 같습니다.

- Schema Registry가 잘하는 일(등록, 조회, 버전, 호환성 검사)은 그대로 활용한다.
- 우리 서비스는 그 위에 **정책(policy)**, **초안(draft)**, **승인(approval)**, **감사(audit)**, **영향도 분석(impact)** 을 얹는다.
- `feat/cli-preflight-mvp-complete` 브랜치의 **topic policy 패턴**을 schema에 맞게 재사용한다.

즉, 목표는 "Schema Registry를 다시 만드는 것"이 아니라,
**Schema Registry를 실행 엔진으로 두고 그 앞에 거버넌스 게이트를 세우는 것**이다.

---

## Problem Statement

현재 schema 기능은 이미 다음을 수행한다.

- schema upload / dry-run / apply
- compatibility check
- delete analysis / delete
- history / dashboard
- schema policy CRUD

하지만 아래 문제가 남아 있다.

1. 정책 구조가 topic policy처럼 명확히 분리되어 있지 않다.
2. subject naming, metadata, compatibility, lifecycle 규칙이 한 흐름에서 섞여 있다.
3. draft / active / archived와 같은 정책 버전 관리 UX는 있지만, schema 변경 흐름 전체와의 연결은 약하다.
4. 환경별 정책 적용 방식(dev/stg/prod)이 schema 흐름 전반에 일관되게 반영되어 있지 않다.
5. topic policy에서 검증기/리졸버/프리셋 구조로 이미 해결했던 문제를 schema 쪽에서 다시 단순 구현으로 풀고 있다.

---

## Design Principles

1. **Registry-native responsibility**
   - schema register
   - schema version lookup
   - compatibility check
   - subject delete
   - reference 조회

2. **Platform responsibility**
   - naming policy
   - metadata policy
   - draft / approval workflow
   - environment-specific guardrails
   - delete impact 확장
   - audit / reason / reviewer / approver

3. **Policy as a versioned resource**
   - 정책은 단순 설정이 아니라 `draft -> active -> archived` 상태를 갖는 리소스여야 한다.

4. **Preflight-first**
   - schema 변경은 publish/apply 전에 반드시 policy validation을 통과해야 한다.

5. **Reuse topic policy patterns**
   - topic policy에서 검증된 패턴(Resolver / Validator / Preset / StoredPolicy / environment targeting)을 최대한 재사용한다.

---

## What We Reuse from Topic Policy

`feat/cli-preflight-mvp-complete` 브랜치에서 topic policy는 다음 구조로 설계되어 있다.

- `management/` : 정책 CRUD + 버전 관리
- `validation/resolver.py` : preset 또는 DB 정책을 실제 validator로 해석
- `validation/orchestrator.py` : naming/guardrail 검증 조합
- `naming/` : 이름 규칙 검증
- `guardrail/` : 환경별 운영 기준 검증
- batch dry-run/apply에서 ACTIVE 정책을 읽어 실제 mutation 전에 검증

Schema도 같은 철학을 따른다.

---

## Proposed Target Structure

```text
app/schema/domain/policies/
├── management/
│   └── models.py              # SchemaPolicyType, SchemaPolicyStatus, StoredSchemaPolicy
├── validation/
│   ├── resolver.py            # SchemaPolicyResolver
│   └── orchestrator.py        # SchemaPolicyValidator
├── naming/
│   ├── rule_schema.py         # subject / record / field naming rules
│   └── validator.py
├── metadata/
│   ├── rule_schema.py         # owner/doc/tags/contact required rules
│   └── validator.py
└── guardrail/
    ├── preset_schema.py       # dev/stg/prod compatibility/lifecycle guardrails
    └── validator.py
```

### Why this structure

- naming은 이름 규칙만 담당
- metadata는 owner/doc/contact/tag 같은 조직 규칙만 담당
- guardrail은 compatibility / approval / delete safety 같은 환경 규칙 담당
- resolver는 preset/custom policy를 validator로 변환
- orchestrator는 여러 validator를 하나의 preflight 단계로 조합

---

## Policy Model

## Policy types

초기에는 아래 3개를 권장한다.

1. `NAMING`
   - subject pattern
   - record name pattern
   - field name pattern
   - namespace pattern
   - forbidden prefixes
   - version suffix rule

2. `METADATA`
   - require owner
   - require doc
   - require contact/team
   - require classification/tag

3. `GUARDRAIL`
   - allowed compatibility modes
   - breaking change approval required
   - prod에서 NONE 금지
   - delete 전에 impact analysis 필수
   - reference 존재 시 delete 금지

### Policy status

- `DRAFT`
- `ACTIVE`
- `ARCHIVED`

### Target environment

- `dev`
- `stg`
- `prod`
- `total`

### Stored schema policy example

```json
{
  "policy_id": "uuid",
  "policy_type": "naming",
  "name": "strict-prod-schema-naming",
  "description": "Production schema naming rules",
  "version": 3,
  "status": "active",
  "target_environment": "prod",
  "content": {
    "subject_pattern": "^(dev|stg|prod)\\.[a-z0-9_.-]+-value$",
    "record_pattern": "^[A-Z][A-Za-z0-9]+$",
    "field_pattern": "^[a-z][a-z0-9_]*$",
    "namespace_pattern": "^com\\.company\\.[a-z0-9.]+$",
    "forbidden_prefixes": ["tmp.", "test.", "scratch."]
  },
  "created_by": "admin@example.com",
  "created_at": "2026-04-17T00:00:00Z"
}
```

---

## Validation Modes

Schema policy validation은 topic policy와 동일하게 3가지 모드를 지원한다.

1. **No policy**
   - 검증 스킵

2. **Preset policy**
   - built-in preset 사용
   - 예: `strict-prod`, `standard-team`, `experimental`

3. **Custom policy from DB**
   - UI/API로 저장한 ACTIVE 정책을 사용

---

## Schema Validation Pipeline

### 1. Draft save

검사 대상:
- schema parse 가능 여부
- subject naming
- metadata 기본 필수 여부

결과:
- draft 저장 가능
- violation은 저장하되 publish 금지 가능

### 2. Dry-run / Validate

검사 대상:
- registry compatibility check
- naming policy
- metadata policy
- guardrail policy
- reference integrity
- delete impact

결과:
- violations
- warning/error 구분
- approval required 여부
- publish 가능 여부

### 3. Apply / Publish

검사 대상:
- 최종 ACTIVE 정책 재평가
- approval 필요 여부 재확인
- compatibility 결과 재확인

결과:
- 통과 시 Registry 등록
- 실패 시 차단

---

## Environment Strategy

### DEV
- naming: warning 또는 relaxed
- metadata: 권장
- compatibility: BACKWARD / NONE 허용 가능
- publish: 빠른 실험 지원

### STG
- naming: 강제
- metadata: owner/doc 필수
- compatibility: 최소 BACKWARD
- breaking change: approval required

### PROD
- naming: 강제
- metadata: owner/doc/contact 필수
- compatibility: FULL 또는 FULL_TRANSITIVE 우선
- `NONE` 금지 또는 강한 승인 필요
- delete: impact analysis 없으면 차단

---

## API Plan

### Policy CRUD

```text
GET    /api/v1/schemas/policies
POST   /api/v1/schemas/policies
GET    /api/v1/schemas/policies/{policy_id}
PUT    /api/v1/schemas/policies/{policy_id}
POST   /api/v1/schemas/policies/{policy_id}/activate
GET    /api/v1/schemas/policies/{policy_id}/history
GET    /api/v1/schemas/policies/active/environment?environment=prod
DELETE /api/v1/schemas/policies/{policy_id}
```

### Draft / Preflight

```text
POST /api/v1/schemas/drafts
GET  /api/v1/schemas/drafts/{draft_id}
POST /api/v1/schemas/drafts/{draft_id}/validate
POST /api/v1/schemas/drafts/{draft_id}/publish
```

### Impact

```text
POST /api/v1/schemas/delete/analyze
POST /api/v1/schemas/plan-change
POST /api/v1/schemas/rollback/plan
```

---

## Data Model Plan

필수 테이블/컬럼 초안:

### `schema_policies`
- id
- policy_id
- policy_type
- name
- description
- version
- status
- target_environment
- content (JSON)
- created_by
- created_at
- updated_at
- activated_at

### `schema_drafts`
- draft_id
- registry_id
- subject
- environment
- schema_text
- schema_type
- metadata (JSON)
- compatibility_mode
- status
- validation_result (JSON)
- created_by
- created_at
- updated_at

### `schema_policy_evaluations`
- evaluation_id
- draft_id or change_id
- applied_policy_ids
- result (JSON)
- warning_count
- error_count
- approval_required
- created_at

---

## Implementation Phases

## Phase 1. Policy model alignment

목표:
- 현재 schema policy 모델을 topic policy 스타일로 정렬한다.

작업:
- `SchemaPolicyType` 확장 (`NAMING`, `METADATA`, `GUARDRAIL`)
- `StoredSchemaPolicy` 성격으로 모델 재구성
- 환경별 ACTIVE 정책 조회 규칙 정리
- schema policy API 응답 shape 정리

완료 기준:
- schema policy가 topic policy처럼 버전/상태/환경 개념을 명확히 가진다.

## Phase 2. Resolver / Validator 도입

목표:
- schema dry-run/apply 전에 실제 validator를 생성할 수 있게 한다.

작업:
- `SchemaPolicyResolver` 추가
- `SchemaPolicyValidator` 추가
- naming validator 추가
- metadata validator 추가
- guardrail validator 추가

완료 기준:
- schema preflight에서 ACTIVE 정책을 읽고 validator를 실행할 수 있다.

## Phase 3. Dry-run / apply integration

목표:
- 기존 `SchemaBatchDryRunUseCase`, `SchemaBatchApplyUseCase`, `SchemaUploadUseCase`에 정책 검증을 일관되게 붙인다.

작업:
- dry-run 단계에 resolver/validator 연결
- apply 단계에 최종 재검증 연결
- policy violation을 approval/risk metadata에 반영

완료 기준:
- schema mutation flow가 topic preflight와 유사한 policy gate를 갖는다.

## Phase 4. Draft workflow

목표:
- draft를 first-class resource로 만든다.

작업:
- schema draft 저장 API 추가
- validate/publish 분리
- publish 시 approval 연계

완료 기준:
- 사용자 입장에서 draft → validate → publish 흐름이 명확해진다.

## Phase 5. Delete / lifecycle guardrails

목표:
- lifecycle 정책을 delete/change 흐름에 반영한다.

작업:
- delete impact analyzer 확장
- reference / dependency 기반 차단 룰 추가
- deprecated / archived lifecycle 정책 정의

완료 기준:
- delete/change가 policy-aware lifecycle gate를 통과해야 한다.

---

## Migration Strategy

1. 기존 schema policy CRUD는 유지
2. 내부 구현만 topic policy 패턴으로 점진 교체
3. 기존 `dynamic_engine.py`는 일시적으로 compatibility layer로 둔다
4. naming / metadata / guardrail validator가 안정되면 old path 제거
5. UI는 기존 policy page를 유지하되 policy type 확장

---

## Risks

1. 기존 schema policy와 새 policy model의 의미 충돌
2. draft workflow 추가 시 기존 upload/apply UX 중복 가능성
3. compatibility rule과 platform guardrail rule의 중복 판단 위험
4. env를 subject prefix로 추론하는 현재 방식과 명시적 environment 모델 간의 충돌

---

## Open Questions

1. subject naming에서 environment는 계속 prefix 기반으로 갈 것인가?
2. schema draft는 registry subject와 1:1인가, 아니면 여러 draft를 허용할 것인가?
3. metadata policy를 naming/guardrail과 별도 타입으로 분리할 것인가?
4. delete impact에 downstream consumer / lineage를 언제 연결할 것인가?
5. approval required와 hard reject의 기준은 어떤 rule에서 결정할 것인가?

---

## Immediate Next Actions

1. schema policy 타입 재정의 초안 작성
2. topic policy 구조와 schema 현재 구조 차이점 매핑
3. `SchemaPolicyResolver` / `SchemaPolicyValidator` 뼈대 생성
4. naming rule schema 초안 정의
5. dev/stg/prod guardrail preset 초안 정의
6. dry-run use case에 policy gate 연결 방식 설계

---

## Summary

Schema Registry 구현 계획의 핵심은 다음 한 문장으로 요약된다.

> **Topic Policy에서 검증된 “versioned policy resource + resolver + validator + preflight gate” 패턴을 Schema Governance에 맞게 이식한다.**

이를 통해 schema 기능은 단순 등록/삭제 API 래퍼를 넘어서,
조직 규칙과 환경 정책을 강제하는 **실제 거버넌스 엔트리 포인트**가 된다.
