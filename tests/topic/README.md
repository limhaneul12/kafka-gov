# Topic 테스트 구조

## 📁 핵심 테스트 파일 (간소화 완료)

### 1. **test_policies_naming.py** ✨ NEW
- Naming Policy 전략 테스트 (Permissive, Balanced, Strict)
- 배치 검증 테스트
- DomainPolicyViolation 구조 검증

### 2. **test_policies_guardrail.py** ✨ NEW
- Guardrail 환경별 테스트 (Dev, Stg, Prod)
- partition/replication/retention 검증
- Preset 기본값 테스트

### 3. **test_planner_service.py** ✨ NEW
- TopicPlannerService 핵심 기능
- 생성/수정/삭제 계획 수립
- partition 증가, config 변경 검증

### 4. **test_batch_use_cases.py** ✨ NEW
- DryRun UseCase 테스트
- Apply UseCase 테스트
- DryRun→Apply 통합 워크플로우

### 5. **test_domain_models_simple.py** ✨ NEW
- Domain 모델 핵심 검증만
- Config, Spec, Batch 기본 동작
- 입력값 validation

### 6. **conftest.py**
- 공통 fixture (repository, admin_client mocks)
- 유지 ✅

### 7. **factories.py**
- 테스트 객체 생성 헬퍼
- 유지 ✅

---

## 🗑️ 삭제 권장 파일 (불필요/과도한 테스트)

- ❌ `test_adapters_optimization.py` - 성능 테스트 (과도함)
- ❌ `test_bulk_delete.py` - 빈 파일
- ❌ `test_router_di.py` - DI 테스트 (통합 테스트, 중복)
- ❌ `test_interface_schema.py` - Pydantic 스키마 (과도한 검증)
- ❌ `test_interface_adapters.py` - 변환 로직 (과도한 검증)
- ❌ `test_domain_policies.py` - 새 파일로 대체됨
- ❌ `test_domain_services.py` - 새 파일로 대체됨
- ❌ `test_use_cases.py` - 새 파일로 대체됨
- ❌ `test_domain_models.py` - 새 파일로 대체됨

---

## 🎯 테스트 철학

### **유지할 테스트**
- ✅ 비즈니스 로직 검증
- ✅ 도메인 규칙 검증
- ✅ 핵심 Use Case 흐름
- ✅ 정책 시스템 동작

### **제거한 테스트**
- ❌ Pydantic/msgspec 자체 기능 (라이브러리 테스트)
- ❌ 단순 getter/setter
- ❌ frozen/immutable 동작 (라이브러리 책임)
- ❌ DI 컨테이너 (통합 테스트 영역)
- ❌ 성능 벤치마크
- ❌ 과도한 경계값 테스트

---

## 📊 테스트 커버리지 목표

| 레이어 | 커버리지 목표 | 비고 |
|--------|--------------|------|
| Domain Models | 80%+ | 핵심 검증 로직만 |
| Domain Services | 90%+ | 비즈니스 로직 중심 |
| Policies | 95%+ | 정책은 철저히 |
| Use Cases | 85%+ | 주요 시나리오 |
| Adapters/Interface | 60%+ | 변환 로직 중심 |

---

## 🚀 테스트 실행

```bash
# 전체 topic 테스트
pytest tests/topic/ -v

# 특정 파일
pytest tests/topic/test_policies_naming.py -v

# 커버리지
pytest tests/topic/ --cov=app/topic --cov-report=html
```

---

## 📝 작성 원칙

1. **단순명료**: 한 테스트는 한 가지만 검증
2. **독립성**: 테스트 간 의존성 없음
3. **명확한 이름**: 테스트 이름만 보고 의도 파악 가능
4. **Factory 사용**: 테스트 데이터는 factories.py 사용
5. **Mock 최소화**: 필요한 경우에만 mock 사용
