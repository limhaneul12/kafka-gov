# Topic Policies

토픽 정책 검증 시스템

## 📂 구조

```
policies/
├── __init__.py          # Public API
├── management/          # 정책 관리 (CRUD + 버전관리)
│   └── models.py       # PolicyReference, StoredPolicy 등
├── validation/          # 정책 검증 (Orchestration)
│   ├── orchestrator.py # TopicPolicyValidator
│   └── resolver.py     # PolicyResolver
├── guardrail/           # Guardrail 정책 (설정값 검증)
│   ├── preset_schema.py
│   ├── preset_spec.py
│   └── validator.py
└── naming/              # Naming 정책 (토픽명 검증)
    ├── rule_schema.py
    ├── rule_spec.py
    └── validator.py
```

## 🎯 3가지 검증 모드

### **1. 정책 없음 (기본)**
```python
# 검증 스킵
validator = await resolver.resolve(None, None)
# → None
```

### **2. 프리셋 사용**
```python
from .validation import create_full_validator
from .naming import StrictNamingRules
from .guardrail import ProdGuardrailPreset

validator = create_full_validator(
    StrictNamingRules(),
    ProdGuardrailPreset()
)
```

### **3. 커스텀 정책 (DB)**
```python
from .validation import PolicyResolver
from .management import PolicyReference

validator = await resolver.resolve(
    naming_ref=PolicyReference(policy_id="uuid-123"),
    guardrail_ref=PolicyReference(preset="prod")
)
```

## 💡 사용 예시

```python
from app.topic.domain.policies import (
    PolicyResolver,
    TopicPolicyValidator,
    PolicyReference,
)

# Application Layer에서
class BatchApplyUseCase:
    async def execute(self, request):
        # 1. Resolver로 Validator 생성
        validator = await self.resolver.resolve(
            naming_ref=request.naming_ref,
            guardrail_ref=request.guardrail_ref,
        )
        
        # 2. 검증 (선택적)
        if validator:
            violations = validator.validate_batch(specs)
            if violations:
                return {"status": "failed", "violations": violations}
        
        # 3. Domain Service 호출 (검증 완료 후)
        plan = await self.planner_service.create_plan(batch)
        return await self.kafka.apply(plan)
```

## 📋 책임 분리

### **Domain Service (TopicPlannerService)**
- ❌ 정책 검증 안 함
- ✅ 계획 생성만 담당

### **Application Layer (UseCase)**
- ✅ PolicyResolver로 Validator 생성
- ✅ 정책 검증 수행
- ✅ Domain Service 호출

## 🔗 참고

- **repositories/** - IPolicyRepository 인터페이스
- **INTEGRATION_EXAMPLE.md** - UseCase 통합 예시 (삭제됨, 복원 필요)
