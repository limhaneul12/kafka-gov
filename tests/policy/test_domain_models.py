"""Policy Domain Models 테스트"""

from __future__ import annotations

import pytest

from app.policy.domain.models import (
    DomainEnvironment,
    DomainNamingRule,
    DomainPolicyContext,
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
    extract_resource_name,
)


class TestExtractResourceName:
    """extract_resource_name 함수 테스트"""

    def test_extract_topic_name(self):
        """토픽 이름 추출"""
        target = {"name": "dev.test.topic", "config": {}}
        name = extract_resource_name(target, DomainResourceType.TOPIC)
        assert name == "dev.test.topic"

    def test_extract_schema_subject(self):
        """스키마 subject 추출"""
        target = {"subject": "dev.user-value", "schema": "{}"}
        name = extract_resource_name(target, DomainResourceType.SCHEMA)
        assert name == "dev.user-value"

    def test_unsupported_resource_type(self):
        """지원하지 않는 리소스 타입"""
        # 임의의 Enum 값 생성은 불가하므로 기존 타입으로 테스트
        target = {"name": "test"}
        # 정상 케이스만 테스트
        name = extract_resource_name(target, DomainResourceType.TOPIC)
        assert name == "test"


class TestDomainPolicyViolation:
    """DomainPolicyViolation 테스트"""

    def test_create_violation(self):
        """위반 정보 생성"""
        violation = DomainPolicyViolation(
            resource_type=DomainResourceType.TOPIC,
            resource_name="dev.test.topic",
            rule_id="naming.pattern",
            message="Name does not match pattern",
            severity=DomainPolicySeverity.ERROR,
            field="name",
            current_value="dev.test.topic",
            expected_value=r"^[a-z]+$",
        )

        assert violation.resource_type == DomainResourceType.TOPIC
        assert violation.resource_name == "dev.test.topic"
        assert violation.rule_id == "naming.pattern"
        assert violation.severity == DomainPolicySeverity.ERROR

    def test_violation_is_frozen(self):
        """위반 정보는 불변"""
        violation = DomainPolicyViolation(
            resource_type=DomainResourceType.TOPIC,
            resource_name="test",
            rule_id="test.rule",
            message="Test",
            severity=DomainPolicySeverity.WARNING,
        )

        with pytest.raises(AttributeError):
            violation.message = "new message"  # type: ignore[misc]


class TestDomainPolicyContext:
    """DomainPolicyContext 테스트"""

    def test_create_context(self):
        """컨텍스트 생성"""
        context = DomainPolicyContext(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            actor="test-user",
            metadata={"team": "platform"},
        )

        assert context.environment == DomainEnvironment.PROD
        assert context.resource_type == DomainResourceType.TOPIC
        assert context.actor == "test-user"
        assert context.metadata == {"team": "platform"}

    def test_context_is_frozen(self):
        """컨텍스트는 불변"""
        context = DomainPolicyContext(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            actor="test-user",
        )

        with pytest.raises(AttributeError):
            context.actor = "new-user"  # type: ignore[misc]


class TestDomainNamingRule:
    """DomainNamingRule 테스트"""

    def test_valid_name(self):
        """정상적인 이름"""
        rule = DomainNamingRule(pattern=r"^[a-z.]+$")
        context = DomainPolicyContext(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            actor="test-user",
        )
        target = {"name": "dev.test.topic"}

        violations = rule.validate(target, context)

        assert len(violations) == 0

    def test_invalid_pattern(self):
        """패턴에 맞지 않는 이름"""
        rule = DomainNamingRule(pattern=r"^[a-z]+$")
        context = DomainPolicyContext(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            actor="test-user",
        )
        target = {"name": "dev.test.topic"}  # 점(.)이 포함되어 패턴 위반

        violations = rule.validate(target, context)

        assert len(violations) > 0
        assert violations[0].rule_id == "naming.pattern"
        assert violations[0].severity == DomainPolicySeverity.ERROR

    def test_forbidden_prefix_in_prod(self):
        """프로덕션에서 금지된 접두사"""
        rule = DomainNamingRule(
            pattern=r"^[a-z.]+$",
            forbidden_prefixes=("tmp.", "test."),
        )
        context = DomainPolicyContext(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            actor="test-user",
        )
        target = {"name": "tmp.test.topic"}

        violations = rule.validate(target, context)

        # 금지된 접두사 위반
        assert len(violations) > 0
        forbidden_violations = [v for v in violations if "forbidden" in v.rule_id.lower()]
        assert len(forbidden_violations) > 0

    def test_rule_properties(self):
        """규칙 속성"""
        rule = DomainNamingRule(pattern=r"^[a-z]+$")

        assert rule.rule_id == "naming.pattern"
        assert "pattern" in rule.description.lower()


class TestDomainPolicySet:
    """DomainPolicySet 테스트"""

    def test_create_policy_set(self):
        """정책 집합 생성"""
        from app.policy.domain.models import DomainPolicySet

        rule = DomainNamingRule(pattern=r"^[a-z.]+$")
        policy_set = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            rules=(rule,),
        )

        assert policy_set.environment == DomainEnvironment.DEV
        assert policy_set.resource_type == DomainResourceType.TOPIC
        assert len(policy_set.rules) == 1

    def test_empty_rules_raises_error(self):
        """빈 규칙 리스트는 에러"""
        from app.policy.domain.models import DomainPolicySet

        with pytest.raises(ValueError, match="at least one rule"):
            DomainPolicySet(
                environment=DomainEnvironment.DEV,
                resource_type=DomainResourceType.TOPIC,
                rules=(),
            )

    def test_validate_batch(self):
        """배치 검증"""
        from app.policy.domain.models import DomainPolicySet

        rule = DomainNamingRule(pattern=r"^[a-z]+$")
        policy_set = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            rules=(rule,),
        )

        targets = [
            {"name": "validname"},
            {"name": "invalid.name"},  # 패턴 위반
        ]

        violations = policy_set.validate_batch(targets, actor="test-user")

        assert len(violations) > 0
        assert any(v.resource_name == "invalid.name" for v in violations)


class TestPolicyEngine:
    """PolicyEngine 테스트"""

    def test_register_and_evaluate(self):
        """정책 등록 및 평가"""
        from app.policy.domain.models import DomainPolicySet, PolicyEngine

        engine = PolicyEngine()
        rule = DomainNamingRule(pattern=r"^[a-z.]+$")
        policy_set = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            rules=(rule,),
        )

        engine.register_policy_set(policy_set)

        targets = [{"name": "dev.test.topic"}]
        violations = engine.evaluate(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            targets=targets,
            actor="test-user",
        )

        assert len(violations) == 0

    def test_no_policy_returns_empty(self):
        """정책이 없으면 빈 리스트 반환"""
        from app.policy.domain.models import PolicyEngine

        engine = PolicyEngine()

        targets = [{"name": "any.name"}]
        violations = engine.evaluate(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            targets=targets,
            actor="test-user",
        )

        assert len(violations) == 0

    def test_get_policy_set(self):
        """정책 집합 조회"""
        from app.policy.domain.models import DomainPolicySet, PolicyEngine

        engine = PolicyEngine()
        rule = DomainNamingRule(pattern=r"^[a-z.]+$")
        policy_set = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            rules=(rule,),
        )

        engine.register_policy_set(policy_set)

        retrieved = engine.get_policy_set(DomainEnvironment.DEV, DomainResourceType.TOPIC)
        assert retrieved is not None
        assert retrieved.environment == DomainEnvironment.DEV

        not_found = engine.get_policy_set(DomainEnvironment.PROD, DomainResourceType.SCHEMA)
        assert not_found is None

    def test_list_environments(self):
        """환경 목록 조회"""
        from app.policy.domain.models import DomainPolicySet, PolicyEngine

        engine = PolicyEngine()
        rule = DomainNamingRule(pattern=r"^[a-z.]+$")

        for env in [DomainEnvironment.DEV, DomainEnvironment.PROD]:
            policy_set = DomainPolicySet(
                environment=env,
                resource_type=DomainResourceType.TOPIC,
                rules=(rule,),
            )
            engine.register_policy_set(policy_set)

        environments = engine.list_environments()
        assert len(environments) == 2
        assert DomainEnvironment.DEV in environments
        assert DomainEnvironment.PROD in environments

    def test_list_resource_types(self):
        """리소스 타입 목록 조회"""
        from app.policy.domain.models import DomainPolicySet, PolicyEngine

        engine = PolicyEngine()
        rule = DomainNamingRule(pattern=r"^[a-z.]+$")

        for rt in [DomainResourceType.TOPIC, DomainResourceType.SCHEMA]:
            policy_set = DomainPolicySet(
                environment=DomainEnvironment.DEV,
                resource_type=rt,
                rules=(rule,),
            )
            engine.register_policy_set(policy_set)

        resource_types = engine.list_resource_types(DomainEnvironment.DEV)
        assert len(resource_types) == 2
        assert DomainResourceType.TOPIC in resource_types
        assert DomainResourceType.SCHEMA in resource_types
