# Schema Register MVP

## Overview

이 문서는 **Schema 등록(Register)** 기능만 따로 떼어 현재 구현을 검토하고,
MVP 기준으로 어떻게 정리할지 정리한 문서입니다.

여기서 등록은 아래 두 경우를 포함합니다.

1. **새 subject 최초 등록** → `v1`
2. **기존 subject에 새 버전 등록** → `v+1`

즉 등록은 단순히 \"파일 업로드\"가 아니라,
**Schema Registry에 실제 schema version을 생성하는 작업**입니다.

---

## Scope

이번 문서의 범위:

- schema 등록 진입점
- 입력/검증/실행 흐름
- 현재 구현의 문제점
- MVP 기준 정리 방향

이번 범위에서 제외:

- 정책 전체 재설계
- draft workflow 전체
- lineage / catalog
- 고도화된 approval UX

---

## Current Registration Paths

현재 등록 경로는 크게 2개입니다.

## 1. Upload path

파일:

- `app/schema/interface/routers/management_router.py`
- `app/schema/application/use_cases/management/upload.py`

엔드포인트:

- `POST /api/v1/schemas/upload`

특징:

- multipart 파일 업로드 기반
- 파일 확장자 기준 schema type 추론
- subject 이름 자동 생성
- Registry에 즉시 등록 시도
- compatibility mode 설정 시도
- metadata 저장
- artifact 저장

즉 지금 upload는 \"업로드 + 등록\"을 같이 수행합니다.

---

## 2. Batch apply path

파일:

- `app/schema/interface/routers/batch_router.py`
- `app/schema/application/use_cases/batch/apply.py`

엔드포인트:

- `POST /api/v1/schemas/batch/apply`

특징:

- JSON batch request 기반
- dry-run / plan 이후 apply
- compatibility / violations / policy pack 재검증
- 통과한 항목만 실제 Registry 등록
- artifact / apply result 저장

즉 batch apply는 \"계획된 등록\" 경로입니다.

---

## Current Strengths

현재 등록 기능에서 좋은 점은 다음과 같습니다.

1. **실제 Registry 등록 로직은 adapter에 모여 있음**
   - `ConfluentSchemaRegistryAdapter.register_schema()`

2. **ConnectionManager를 통해 registry client를 가져옴**
   - registry connection responsibility가 분리되어 있음

3. **Batch apply는 plan → validate → register 순서를 따름**
   - 등록 전에 재검증이 가능함

4. **등록 결과를 메타데이터/artifact/audit와 연결함**
   - 이후 history 추적 기반이 됨

---

## Current Problems

## 1. Registration path가 두 개라 의미가 분산됨

지금은:

- `upload` = 파일 업로드 기반 즉시 등록
- `batch/apply` = 계획 기반 등록

으로 나뉘어 있습니다.

문제는 두 경로의 의미가 다르다는 점입니다.

- upload는 \"preflight\"보다 \"fire and register\"에 가깝고
- apply는 \"validated mutation\"에 가깝습니다.

MVP 기준으로는 등록의 **정식 경로를 하나로 정하는 것**이 필요합니다.

---

## 2. Upload path가 Registry 실패를 너무 관대하게 삼킴

파일:

- `app/schema/application/use_cases/management/upload.py`

현재 `_process_schema_file()`에서는 Registry 등록 실패 시:

- warning log 남김
- fallback artifact를 `version=1`로 생성
- metadata는 저장 시도
- artifact도 기록

즉 실제 Registry 등록에 실패했는데도,
내부 기록상은 어느 정도 등록된 것처럼 남을 수 있습니다.

이건 registration MVP 기준으로 위험합니다.

### Why this is risky

- Registry truth와 DB truth가 어긋날 수 있음
- history / detail / search에서 혼동을 일으킬 수 있음
- 사용자는 등록 성공으로 오해할 수 있음

### MVP rule

> **실제 Registry 등록 실패는 등록 실패로 간주해야 한다.**

artifact / metadata fallback 기록은 별도 failed-upload 모델이 아니면 남기지 않는 편이 안전합니다.

---

## 3. Upload endpoint 설명과 실제 동작이 다소 어긋남

라우터 설명은 \"사전 검증\"처럼 읽히지만,
실제 구현은 바로 Registry 등록까지 수행합니다.

즉 API 의미가 모호합니다.

MVP에서는 둘 중 하나로 명확히 해야 합니다.

1. **upload = validate only**
2. **upload = upload and register**

현재 구현은 사실상 2번입니다.

문서/이름/UX를 이에 맞춰 정리해야 합니다.

---

## 4. ZIP 처리 경로는 실제 등록이 아님

현재 ZIP 파일 처리에서는:

- schema 파일 존재 여부만 확인
- bundle artifact만 기록

하고, ZIP 내부 schema를 실제 Registry에 등록하지 않습니다.

즉 ZIP 업로드는 현재 기준으로는
**실제 schema registration flow가 아니라 bundle intake에 가깝습니다.**

MVP에서는 이것도 분리해서 봐야 합니다.

### Recommendation

- ZIP intake는 나중 기능으로 미루거나
- ZIP을 풀어서 실제 per-schema register를 하도록 명확화

---

## 5. Subject naming이 아직 너무 단순함

현재 upload path의 subject 생성은:

- `gov:EnvPrefixed`면 `env.filename`
- 아니면 그냥 `filename`

수준입니다.

파일:

- `app/schema/application/use_cases/management/upload.py`

이건 등록 MVP 기준에서도 최소한 아래는 필요합니다.

- subject 충돌 가능성 설명
- naming strategy를 명확히 제한
- file stem 기반 자동 subject의 위험성 인지

정책 재설계 전이라도 **register path에서 naming 의미를 더 명확히 해야 합니다.**

---

## 6. Compatibility mode 설정과 schema 등록이 한 트랜잭션이 아님

upload path는:

1. schema 등록
2. subject compatibility mode 설정

순서로 진행합니다.

문제는:

- 등록 성공
- compatibility mode 설정 실패

가 가능하다는 점입니다.

즉 부분 성공 상태가 생길 수 있습니다.

MVP에서는 이 상태를 명시적으로 다뤄야 합니다.

### Recommendation

- compatibility mode는 별도 관리 기능으로 분리하거나
- 등록 성공 후 mode 설정 실패를 partial failure로 기록하고 명확히 반환

---

## 7. `storage_id`가 registration MVP에서는 실질적으로 사용되지 않음

라우터/유스케이스에 `storage_id`가 있지만,
현재 등록 핵심 흐름에서 실질적인 저장소 연동은 거의 없습니다.

MVP 등록에서는 불필요하면 걷어내는 게 좋습니다.

---

## Recommended MVP Direction

## 1. Canonical registration path를 하나 정한다

권장:

> **정식 등록은 `plan/dry-run -> apply` 경로를 기준으로 한다.**

즉:

- 파일 업로드는 input convenience
- 실제 등록은 apply에서만 확정

이 구조가 가장 안전합니다.

---

## 2. Registration success의 정의를 엄격히 한다

등록 성공은 아래가 모두 만족해야 합니다.

1. Registry에 schema version이 실제 생성됨
2. version / schema_id를 확인 가능함
3. 내부 metadata/artifact 저장 성공

이 중 핵심은 **1번**입니다.

Registry 등록 실패 시 success처럼 보이는 fallback은 제거하는 것이 좋습니다.

---

## 3. Register는 두 가지 타입만 지원한다

MVP에서 등록은 다음 둘만 있으면 충분합니다.

### A. New subject registration

- subject가 없음
- 결과는 `v1`

### B. New version registration

- subject가 이미 있음
- 결과는 `latest + 1`

즉 register 관점에서는 \"생성\"과 \"수정\"이 내부적으로 같은 종류의 동작입니다.

차이는 current subject 존재 여부뿐입니다.

---

## 4. Input contract를 단순화한다

MVP 등록 입력은 최소한 아래만 있으면 됩니다.

- `registry_id`
- `subject`
- `schema_type`
- `schema`
- `compatibility` (optional)
- `references` (optional)
- `metadata` (optional)

`compatibility` 예시는 `FULL_TRANSITIVE`를 사용하지만 실제 입력은
Schema Registry가 지원하는 `NONE`, `BACKWARD`, `BACKWARD_TRANSITIVE`,
`FORWARD`, `FORWARD_TRANSITIVE`, `FULL`, `FULL_TRANSITIVE` 전체를 허용하는
방향으로 문서화하는 것이 맞습니다.

파일 업로드는 convenience layer로 남기더라도,
핵심 registration service는 이 구조를 기준으로 동작하는 편이 좋습니다.

---

## Suggested Registration Model

### Register request

```json
{
  "registry_id": "default",
  "subject": "prod.orders-value",
  "schema_type": "AVRO",
  "schema": "{ ... }",
  "compatibility": "FULL_TRANSITIVE",
  "references": [],
  "metadata": {
    "owner": "team-data-platform",
    "doc": "https://wiki.company.com/schemas/orders"
  }
}
```

### Register response

```json
{
  "subject": "prod.orders-value",
  "version": 3,
  "schema_id": 101,
  "created_at": "2026-04-17T00:00:00Z",
  "status": "registered"
}
```

---

## Minimal Rules for Registration MVP

## P0 - Must reject

1. invalid schema syntax
2. invalid schema type
3. subject missing
4. duplicate invalid reference names
5. registry registration failure

## P1 - Optional for first pass

1. compatibility mode subject override handling
2. metadata completeness
3. naming strictness

---

## Recommended API Shape

MVP 기준으로는 아래 두 레벨로 정리할 수 있습니다.

## A. Canonical registration API

```text
POST /api/v1/schemas/batch/apply
```

이 경로를 정식 등록 경로로 본다.

## B. Convenience upload API

```text
POST /api/v1/schemas/upload
```

이 경로는 장기적으로 아래 둘 중 하나로 정리한다.

1. validate + convert only
2. 내부적으로 batch request를 만든 뒤 canonical apply를 호출

즉 upload가 직접 register 로직을 별도로 들고 있는 구조는 점차 줄이는 것이 좋다.

---

## Refactoring Recommendations

## 1. Shared registration service 추출

현재 upload와 batch apply가 각각 등록 로직을 갖고 있습니다.

권장:

- `SchemaRegistrationService` 또는 유사 abstraction 추가
- 입력은 `DomainSchemaSpec`
- 출력은 `version, schema_id`

그러면:

- upload
- batch apply
- future draft publish

가 같은 register core를 재사용할 수 있습니다.

---

## 2. Upload fallback artifact 제거

현재 upload path의 가장 위험한 부분입니다.

권장:

- Registry 등록 실패 시 artifact 저장하지 않음
- 실패 상태는 audit/log/error response로만 반환

---

## 3. ZIP은 등록과 분리하거나 명확히 구현

현재 ZIP은 실제 register path가 아닙니다.

MVP에서는:

- ZIP 지원을 문서상 실험 기능으로 낮추거나
- ZIP 내부 schema를 명시적으로 iterate 해서 register 하도록 설계

---

## 4. Compatibility 설정 분리 검토

등록과 동시에 compatibility mode를 바꾸는 것은 부분 실패를 만들 수 있습니다.

MVP에서는 아래가 더 단순합니다.

- register는 schema version 생성만 담당
- compatibility mode 변경은 별도 API/관리 기능

---

## Phase Plan

## Phase 1. Registration semantics cleanup

- 정식 등록 경로를 `batch/apply`로 명확히 함
- upload의 의미를 문서와 코드에서 정리

## Phase 2. Shared register core

- upload / apply가 공통 registration service 사용

## Phase 3. Failure semantics tightening

- Registry 등록 실패 fallback 제거
- partial failure 반환 규칙 정의

## Phase 4. Input simplification

- register 핵심 DTO를 단순화
- upload는 wrapper 역할만 하도록 축소

---

## Open Questions

1. upload는 장기적으로 register API인가, validate API인가?
2. compatibility mode 변경을 register와 묶을 것인가?
3. ZIP 업로드를 실제 등록 기능으로 유지할 것인가?
4. subject 자동 생성은 얼마나 허용할 것인가?

---

## Summary

Schema 등록 MVP의 핵심은 다음입니다.

> **등록은 Schema Registry에 실제 version을 생성하는 작업이며, 성공 기준은 Registry truth를 중심으로 엄격하게 정의해야 한다.**

즉 이번 단계에서 가장 중요한 정리는 아래입니다.

- 등록의 정식 경로를 하나로 정하기
- Registry 실패를 성공처럼 기록하지 않기
- upload와 apply의 책임을 분리하거나 통합하기
- 등록 코어를 공통 service로 묶기
