# 🎯 Real-time Data Governance System PRD

Product Requirements Document for evolving Kafka-Gov from a Kafka governance tool into a real-time data governance system.

---

## Overview

Kafka-Gov의 다음 단계는 토픽/스키마 관리 기능을 더 늘리는 것이 아니라, **실시간 데이터 거버넌스 시스템**으로 관점을 전환하는 것입니다.

이 문서는 **현재 구현 상태를 설명하는 문서**라기보다, 현재 Kafka-centric runtime 위에서 어디로 이동해야 하는지를 정의하는 **target-state PRD**입니다.

이 문서의 핵심 전제는 다음과 같습니다.

- Kafka는 앞으로도 실시간 데이터 흐름에서 중요하지만, 점점 더 **처리 엔진**보다는 **이벤트 및 스토리지 허브** 역할을 강하게 맡게 된다.
- Schema Registry는 단순 부가 기능이 아니라, **버전 관리**, **호환성 검증**, **주제(topic)와의 연관성 파악**을 가능하게 하는 핵심 거버넌스 신호원이다.
- Topic과 Schema는 운영 리소스이지만, 플랫폼의 최상위 거버넌스 객체는 결국 **Product**와 **Contract**가 되어야 한다.

즉, 이 시스템은 “Kafka를 잘 관리하는 도구”가 아니라, **실시간 데이터 자산을 Product/Contract 단위로 통제하고 추적하는 플랫폼**을 지향한다.

---

## Problem

현재의 Kafka 운영 도구들은 대체로 다음 수준에서 멈춘다.

- 토픽이 존재하는지
- 스키마가 등록되었는지
- consumer lag이 얼마인지
- 설정이 정책을 위반하는지

하지만 실제 거버넌스는 그보다 높은 질문을 해결해야 한다.

- 이 데이터 스트림은 누구의 책임인가?
- 이 Topic과 Schema는 어떤 Product에 속하는가?
- 외부와 내부에 어떤 Contract를 약속하고 있는가?
- 지금 배포하려는 Schema 변경은 어떤 Consumer/Product/Contract에 영향을 주는가?
- 실시간 변경을 언제 차단하고, 언제 승인 흐름으로 보내야 하는가?

지금 리포지토리는 Topic/Schema 운영 기능은 강하지만, Product/Contract/Governance/Lineage가 아직 런타임에 올라오지 않아 **거버넌스 객체 중심의 플랫폼 경험**으로는 이어지지 못하고 있다.

---

## Product Vision

Build a real-time data governance system where:

- **Product** is the business-facing ownership boundary,
- **Contract** is the promise boundary for compatibility and change safety,
- **Topic** and **Schema** are the operational resources bound under those higher-level objects,
- **Governance** decides whether a change is safe, risky, blocked, or approval-required,
- **Lineage** explains impact in product terms, not just Kafka resource terms.

사용자는 더 이상 “topic 하나”나 “subject 하나”를 따로 보는 것이 아니라,

- 어떤 Product가 존재하는지,
- 어떤 Topic/Schema가 그 Product에 바인딩되어 있는지,
- 어떤 Contract 버전이 현재 유효한지,
- 어떤 변경이 어떤 영향과 승인을 요구하는지를

한 흐름 안에서 이해할 수 있어야 한다.

여기서 말하는 **real-time**은 단순히 화면이 자주 갱신된다는 뜻이 아니라,

- live topic/schema state,
- active schema version/compatibility state,
- producer 활동이 있을 때 관측 가능한 subject-topic association,
- approval/policy/audit decision이 실제 변경 흐름에 반응하는 상태

를 의미한다.

---

## Goals

1. Kafka/Schema Registry의 실시간 운영 신호를 거버넌스 모델로 끌어올린다.
2. Product와 Contract를 Topic/Schema 위의 일급 거버넌스 객체로 만든다.
3. Schema Registry 기반 버전/호환성 정보를 Product/Contract 판단에 연결한다.
4. Schema 변경 시 approval, audit, policy, impact를 같은 흐름에서 다룬다.
5. 운영 기능을 해치지 않으면서 거버넌스 중심 UX/API로 확장한다.

---

## Non-Goals

- Kafka Admin 또는 Schema Registry 자체를 대체하는 것
- 범용 데이터 카탈로그 전체를 한 번에 구현하는 것
- 모든 데이터 소스를 아우르는 범용 lineage를 첫 단계에서 완성하는 것
- 스트림 처리 엔진 또는 ETL orchestration 시스템이 되는 것
- Topic/Schema UI를 더 화려하게 만드는 것을 제품 목표로 착각하는 것

---

## Key Concepts

### Topic

실시간 데이터가 흐르는 운영 리소스이다. 중요하지만 최상위 거버넌스 객체는 아니다.

### Schema

데이터 계약의 실질적 payload 정의이며, Schema Registry를 통해 버전과 호환성이 관리된다.

### Product

비즈니스 관점의 데이터 자산 단위이다. Topic, Schema, 외부 저장소, 소유 조직, 정책 책임을 하나로 묶는 중심 aggregate이다.

### Contract

데이터가 외부 또는 내부 소비자에게 약속하는 형식, 호환성, 변경 규칙, 품질 기대치를 표현하는 단위이다.

### Governance Decision

어떤 변경이 허용, 경고, 차단, 승인 필요 중 어디에 속하는지를 판단하는 결과이다.

### Lineage

Topic, Schema, Product, Contract 사이의 관계와 변경 영향도를 설명하는 연결 그래프이다.

---

## Why Kafka and Schema Registry Matter

Kafka는 실시간 데이터 시스템에서 여전히 핵심이다. 다만 시간이 갈수록 Kafka의 역할은 “모든 것을 처리하는 곳”보다 “이벤트를 수용하고 보존하는 스토리지 허브”에 가까워질 가능성이 높다.

이 변화는 거버넌스에 더 중요하다.

- 저장과 재생산이 가능한 허브일수록 ownership과 contract가 중요해진다.
- Topic이 오래 살아남을수록 문서화, audit, retention, compatibility 기준이 중요해진다.
- Schema Registry가 제공하는 버전 히스토리는 Product/Contract 관점의 의사결정 입력이 된다.

또한 Schema Registry는 producer가 실제로 동작하는 경우,

- 어떤 subject가 어떤 topic 흐름과 연결되는지,
- 어떤 버전이 실제로 사용되는지,
- 호환성 모드가 무엇인지

를 파악하는 데 큰 도움을 준다.

즉, Kafka와 Schema Registry는 단순 운영 도구가 아니라 **실시간 거버넌스 신호원**이다.

---

## Architecture Direction

### Directional Model

`Product -> Contract -> Topic / Schema`

이 방향은 **거버넌스 ownership 모델**의 기본 방향이다. 운영 리소스가 상위 거버넌스 모델을 끌고 가는 것이 아니라, 상위 거버넌스 모델이 운영 리소스를 설명하고 제어해야 한다.

### Repository Direction

현재 리포지토리의 아키텍처 규칙은 다음을 따른다.

- `interface -> application -> domain <- infrastructure`
- shared infra는 공용 계층으로 모은다
- composition root는 `app/container.py`, runtime entry는 `app/main.py`에서 관리한다

이 방향에서 이번 `app/infra/kafka` 추출은 올바른 첫 단계다. Topic/Schema가 각자 Kafka/Schema Registry 구현을 소유하지 않고, 공용 infra 계층을 통해 접근하도록 길을 열었기 때문이다.

다만 아직 남은 과제는 있다.

- Topic/Schema application use case 내부에서 shared adapter를 직접 생성하는 패턴 제거
- Product/Contract를 실제 runtime module로 올리기
- Governance/Lineage를 독립 기능이 아니라 Product/Contract 변화 흐름에 연결하기

---

## Current Repo Implications

현재 리포 기준으로 보면:

- **Schema**는 가장 production-ready한 거버넌스 모듈이다.
- **Shared approval/audit**은 이미 실사용 가능한 수준의 백본이 있다.
- **Product**와 **Contract**는 도메인 모델과 유스케이스는 있지만 아직 production module이 아니다.
- **Governance**와 **Lineage**는 개념과 유스케이스는 있으나 플랫폼 런타임에 완전히 올라오지 않았다.

즉, 오늘의 shipped runtime은 **schema governance 중심**으로 정리되어 있고, 이 문서는 그것을 **Product/Contract 중심 real-time data governance system**으로 끌어올리기 위한 방향 문서다.

따라서 다음 구현은 “새 기능을 아무거나 추가”가 아니라,

1. shared Kafka infra seam 정리,
2. Product productionization,
3. Contract productionization,
4. Governance/Lineage 연결

순으로 가야 한다.

---

## Phased Plan

### Phase 1. Foundation and Shared Runtime

목표: schema governance와 shared runtime을 플랫폼 하부 런타임으로 고정한다.

- shared Kafka/Schema adapter 생성 책임을 application 밖으로 이동
- `app/infra/kafka`를 실제 공용 인프라 경계로 정착
- approval/audit을 cross-domain backbone으로 확장 가능한 형태로 정리

### Phase 2. Product as the Governance Entry Point

목표: Product를 실제 플랫폼 중심 객체로 런타임에 올린다.

- Product repository 구현
- Product container/router/runtime wiring 추가
- Product에 Topic/Schema/기타 infra binding을 연결
- 사용자가 Product 단위로 데이터 자산을 볼 수 있게 함

### Phase 3. Contract as the Change Boundary

목표: Contract를 통해 변경 위험과 호환성을 통제한다.

- Contract repository 구현
- Contract container/router/runtime wiring 추가
- Product와 Contract 관계 확립
- Schema version/compatibility와 Contract 판단을 연결

### Phase 4. Governance Decision Layer

목표: 정책, 승인, 감사가 Product/Contract 변경에 실제로 반응하게 만든다.

- policy evaluation을 mutation flow에 연결
- unsafe change를 approval-required 또는 blocked로 분기
- audit trail을 topic/schema 중심에서 product/contract 중심으로 확장

### Phase 5. Lineage and Real-time Views

목표: 운영 신호와 거버넌스 신호를 한데 묶는다.

- Product/Contract/Topic/Schema lineage 제공
- change impact를 product terms로 설명
- real-time 상태를 governance dashboard로 노출

---

## Acceptance Criteria

이 PRD가 지향하는 첫 유효 릴리스는 다음을 만족해야 한다.

1. 사용자가 Product를 생성하고, 해당 Product에 Topic/Schema 리소스를 바인딩할 수 있다.
2. 사용자가 Contract를 생성하고 버전 상태를 확인할 수 있다.
3. Schema Registry의 버전/호환성 정보가 Contract 또는 governance 판단에 반영된다.
4. Schema 변경이 approval/audit/governance 흐름과 연결된다.
5. 변경 영향이 raw topic name만이 아니라 Product/Contract 관점으로 설명된다.
6. 기존 schema governance 기능은 유지된다.
7. producer 활동이 존재하는 경우, active subject/topic/version association을 거버넌스 관점에서 확인할 수 있다.

---

## Immediate Execution Direction

현재 상태에서 바로 다음 구현 태스크는 다음과 같다.

1. Schema application use case에서 shared adapter 직접 생성 제거
2. Product module productionization
3. Contract module productionization
4. Governance decision flow 연결
5. Lineage/real-time observability 확장

즉, 지금 당장은 Product를 붙이기 전에 **Foundation seam cleanup**이 먼저다.

---

## Open Questions

1. Contract는 내부 소비자 기준인가, 외부 제공 계약까지 포함하는가?
2. Product ownership은 팀 단위만으로 충분한가, 서비스/도메인/조직 단위까지 필요한가?
3. Governance decision 중 어떤 것은 동기 차단이고 어떤 것은 비동기 경고여야 하는가?
4. Lineage는 Kafka/Schema Registry 중심으로 시작한 뒤 외부 시스템으로 확장할 것인가?

---

## Summary

Kafka-Gov의 다음 버전은 Kafka 운영툴을 더 키우는 것이 아니라, Kafka와 Schema Registry를 기반 신호원으로 삼아 **Product, Contract, Policy, Approval, Audit, Lineage를 묶는 실시간 데이터 거버넌스 시스템**으로 진화해야 한다.

이 PRD는 그 전환의 기준 문서다.
