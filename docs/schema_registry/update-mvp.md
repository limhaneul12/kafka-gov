# Schema Update MVP

## Overview

이 문서는 **Schema 수정(Update)** 기능만 따로 떼어 정리한 MVP 설계 메모입니다.

여기서 수정은 일반 CRUD의 update가 아니라 다음 의미를 가집니다.

> **기존 subject의 latest schema를 기준으로 변경 계획을 세우고, 검증을 통과하면 새 버전(v+1)을 등록한다.**

즉, 기존 버전을 덮어쓰지 않고 **새 버전 등록**으로 처리합니다.

---

## Scope

이번 문서는 아래 범위만 다룹니다.

- schema 수정
- version 증가
- compatibility 검증
- 최소 영향도 분석
- apply 차단 조건

이번 범위에서 제외합니다.

- draft workflow 전체
- 정책 리소스 재설계 전체
- lineage
- delete impact 고도화
- approval UX 전체 재설계

---

## Current Implementation Review

현재 코드 기준 수정 흐름은 이미 어느 정도 잡혀 있습니다.

### Current flow

1. 프론트에서 현재 schema를 편집
2. `planChange` 호출
3. 백엔드에서 현재 latest schema 조회
4. diff / compatibility / violation 계산
5. apply 시 백엔드가 재검증 후 새 버전 등록

### Relevant files

- `app/schema/application/use_cases/management/plan_change.py`
- `app/schema/application/use_cases/batch/apply.py`
- `app/schema/domain/services.py`
- `app/schema/domain/models/plan_result.py`
- `frontend/src/pages/schemas/SchemaDetail.tsx`

### Good parts

- 수정이 덮어쓰기가 아니라 새 버전 등록으로 동작함
- apply 전에 plan 단계를 거침
- compatibility가 깨지면 apply가 차단됨
- diff를 사용자에게 보여줄 수 있음

### Gaps

1. 영향도 분석이 아직 placeholder 수준
2. schema 수정과 compatibility mode 변경이 UI/로직에서 다소 섞여 있음
3. approval이 실제 위험도보다 더 넓게 요구될 수 있음
4. environment를 subject prefix로 추론하는 방식에 의존함

---

## Core Design Decisions

## 1. Update means “register next version”

수정은 다음과 같이 정의합니다.

- 기존 subject는 유지
- 기존 version은 유지
- 새 schema는 `v+1`로 등록

즉:

- `register new subject` = 최초 등록
- `update subject` = 다음 버전 등록

---

## 2. Schema update and compatibility mode change are separate operations

MVP에서는 아래 둘을 분리합니다.

- **Schema update**: 새 schema 내용 등록
- **Compatibility mode change**: subject-level compatibility 설정 변경

이유:

- schema 수정 자체와 운영 정책 변경은 책임이 다름
- UI와 backend 의미를 단순하게 유지할 수 있음
- apply 시 무엇이 실패했는지 설명하기 쉬움

즉 MVP에서는 수정 기능이 아래 질문에만 답하면 됩니다.

> “이 새 schema를 기존 subject의 다음 버전으로 등록해도 되는가?”

---

## 3. Update is always two-step

### Step 1. Plan Update

입력:

- `registry_id`
- `subject`
- `new_schema`

출력:

- current version
- target version
- structural diff
- compatibility result
- minimal impact summary
- can_apply

### Step 2. Apply Update

입력:

- plan 결과에 대응하는 변경 요청

동작:

- 서버에서 다시 검증
- 통과 시만 Schema Registry에 등록
- 새 버전 생성

---

## 4. Backend is the final source of truth

프론트는 편집기와 preview 역할만 합니다.

최종 판정은 항상 backend가 담당합니다.

- 프론트: edit, plan 요청, 결과 표시
- 백엔드: latest schema 조회, compatibility 판단, 차단 여부 결정, 실제 register

즉 apply 직전에도 서버 재검증이 필요합니다.

---

## 5. Approval is conditional, not universal

MVP에서 approval은 모든 수정에 요구하지 않습니다.

- 안전한 변경 → 바로 apply 가능
- 위험한 변경 → approval required
- 금지된 변경 → apply 불가

즉 수정 기능의 기본 판정은 아래 3단계입니다.

- `ALLOW`
- `APPROVAL_REQUIRED`
- `REJECT`

---

## Functional Requirements

## A. Plan change

### Request

```json
{
  "subject": "prod.orders-value",
  "new_schema": "{ ... }"
}
```

### Response should include

- `subject`
- `current_version`
- `target_version`
- `diff`
- `compatibility`
- `issues`
- `impact`
- `can_apply`

---

## B. Apply change

### Expected behavior

- 대상 subject가 존재해야 함
- latest 기준으로 다시 검증해야 함
- 검증 통과 시 새 버전 등록
- 실패 시 기존 상태는 유지

### Success result should include

- `subject`
- `registered_version`
- `schema_id`
- `created_at`

---

## Minimum Validation Rules

MVP에서 수정 기능이 반드시 막아야 하는 규칙입니다.

## P0 - Hard reject

1. **Invalid schema syntax**
2. **Subject not found**
3. **Registry compatibility check failed**
4. **Required field added without default**
5. **Field type changed incompatibly**
6. **Broken schema references**

## P1 - Approval required or warning

1. enum narrowing
2. compatibility mode가 너무 느슨한 경우
3. production subject의 위험 변경

---

## Impact Analysis MVP

이번 MVP의 영향도 분석은 최소한 아래 수준이면 충분합니다.

### Required

- 변경 대상 subject
- 현재 버전
- 다음 버전
- compatibility failure 여부
- 필드 추가/삭제/타입 변경 요약
- reference 관련 기본 경고

### Deferred

- downstream consumer/service 영향
- lineage 기반 영향도
- topic association 기반 영향도

즉 이번 단계에서는 **구조적 영향도 요약**만 다룹니다.

---

## Recommended API Surface

MVP에서는 기존 흐름을 최대한 재사용하되 의미를 명확히 합니다.

### Plan update

`POST /api/v1/schemas/plan-change`

### Apply update

기존 batch apply 재사용 가능. 다만 내부 의미는 다음처럼 고정합니다.

- 단일 subject 변경
- 새로운 version 등록

장기적으로는 아래 형태도 고려할 수 있습니다.

`POST /api/v1/schemas/{subject}/versions`

---

## Backend Implementation Notes

## 1. `plan_change.py`

유지하되 역할을 더 명확히 합니다.

- 현재 subject의 latest schema 조회
- 단일 spec 생성
- planner 호출
- 결과 저장

개선 포인트:

- compatibility mode 변경과 schema 수정 의미 분리
- environment 추론 방식은 추후 분리 대상

## 2. `domain/services.py`

`SchemaPlannerService`가 핵심입니다.

현재 잘 하는 일:

- current subject 조회
- action 계산
- diff 계산
- compatibility check
- violation 수집

추가 필요:

- 최소 impact summary 강화
- update 전용 판정 메시지 정리

## 3. `batch/apply.py`

현재 구조상 apply는 이미 backend 재검증을 수행합니다.

유지 원칙:

- plan 재생성
- `plan.can_apply` 확인
- 실패 시 register 금지
- 성공 시 `register_schema()` 호출

---

## Frontend Implementation Notes

파일:

- `frontend/src/pages/schemas/SchemaDetail.tsx`

개선 포인트:

1. schema 수정과 compatibility mode 변경 UI를 분리
2. approval evidence를 무조건 요구하지 않도록 조정
3. plan result에서 `allow / approval required / reject` 상태를 더 명확히 표시

즉 edit 화면은 아래 흐름이면 충분합니다.

- Edit
- Plan
- Review Diff / Compatibility / Impact
- Apply if allowed

---

## Phase Plan

## Phase 1. Clarify semantics

- 수정은 새 버전 등록임을 코드/문서/UI에서 명확히 한다
- compatibility mode 변경 기능과 분리한다

## Phase 2. Strengthen plan result

- diff 요약 강화
- impact summary 최소 구현
- rejection reason 명확화

## Phase 3. Tighten apply rules

- backend 재검증 유지
- hard reject / approval required / allow 구분 정리

## Phase 4. Frontend cleanup

- edit UX 단순화
- approval 요구 조건 정리
- result 상태 표시 개선

---

## Open Questions

1. 수정 요청에서 compatibility를 사용자 입력으로 계속 받을 것인가?
2. compatibility mode 변경은 별도 admin API로 분리할 것인가?
3. production subject의 risky change 기준은 어디까지를 approval required로 볼 것인가?
4. impact summary에 references를 언제 포함할 것인가?

---

## Summary

Schema 수정 MVP의 핵심은 다음입니다.

> **Schema 수정은 기존 subject를 덮어쓰는 것이 아니라, 검증을 거친 뒤 새 버전을 등록하는 과정이다.**

이번 단계에서는 정책 전체를 확장하기보다,
먼저 수정 자체를 안정적으로 만들기 위해 아래를 우선한다.

- latest 기준 계획 수립
- compatibility 검증
- 최소 영향도 분석
- apply 차단 규칙 정리
- 새 버전 등록
