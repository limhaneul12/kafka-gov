"""Naming Policy 테스트 - 핵심 기능만"""

import pytest

from app.shared.domain.policy_types import DomainPolicySeverity, DomainResourceType
from app.topic.domain.policies.naming import (
    BalancedNamingRules,
    NamingValidator,
    PermissiveNamingRules,
    StrictNamingRules,
)


class TestPermissiveNamingRules:
    """Permissive 전략 테스트"""

    def test_allows_almost_anything(self):
        """거의 모든 형식 허용"""
        validator = NamingValidator(PermissiveNamingRules())

        valid_names = [
            "orders",
            "user-events",
            "MyTopic",
            "PROD_ORDERS",
            "analytics.page_views",
        ]

        for name in valid_names:
            violations = validator.validate(name)
            assert len(violations) == 0, f"{name}이 거부되었습니다: {violations}"

    def test_rejects_reserved_words(self):
        """예약어는 거부"""
        validator = NamingValidator(PermissiveNamingRules())

        violations = validator.validate("__consumer_offsets")

        assert len(violations) == 1
        assert violations[0].rule_id == "naming.reserved_words"
        assert violations[0].severity == DomainPolicySeverity.ERROR


class TestBalancedNamingRules:
    """Balanced 전략 테스트"""

    def test_valid_structure(self):
        """올바른 구조: {env}.{domain}.{resource}"""
        validator = NamingValidator(BalancedNamingRules())

        valid_names = [
            "dev.commerce.orders",
            "stg.marketing.campaigns.sent",
            "prod.analytics.events",
        ]

        for name in valid_names:
            violations = validator.validate(name)
            assert len(violations) == 0, f"{name}이 거부되었습니다: {violations}"

    def test_rejects_no_environment_prefix(self):
        """환경 접두사 없으면 거부"""
        validator = NamingValidator(BalancedNamingRules())

        violations = validator.validate("orders")

        assert len(violations) > 0
        assert any(v.rule_id == "naming.pattern" for v in violations)

    def test_rejects_uppercase(self):
        """대문자 사용 거부"""
        validator = NamingValidator(BalancedNamingRules())

        violations = validator.validate("prod.Commerce.ORDERS")

        assert len(violations) > 0

    def test_rejects_forbidden_prefixes(self):
        """금지된 접두사 거부"""
        validator = NamingValidator(BalancedNamingRules())

        forbidden_names = [
            "tmp.test.topic",
            "test.something.topic",
            "debug.dev.topic",
        ]

        for name in forbidden_names:
            violations = validator.validate(name)
            # pattern 위반이 먼저 걸릴 수 있음
            assert len(violations) > 0


class TestStrictNamingRules:
    """Strict 전략 테스트"""

    def test_valid_structure(self):
        """올바른 구조: {env}.{classification}.{domain}.{resource}.{version}"""
        validator = NamingValidator(StrictNamingRules())

        valid_names = [
            "prod.pii.commerce.customer-data.v1",
            "prod.public.analytics.page-views.v2",
            "dev.internal.marketing.campaigns.v1",
        ]

        for name in valid_names:
            violations = validator.validate(name)
            assert len(violations) == 0, f"{name}이 거부되었습니다: {violations}"

    def test_rejects_missing_classification(self):
        """classification 누락 거부"""
        validator = NamingValidator(StrictNamingRules())

        violations = validator.validate("prod.commerce.orders.v1")

        assert len(violations) > 0
        assert any(v.rule_id == "naming.pattern" for v in violations)

    def test_rejects_missing_version(self):
        """버전 누락 거부"""
        validator = NamingValidator(StrictNamingRules())

        violations = validator.validate("prod.pii.commerce.orders")

        assert len(violations) > 0

    def test_rejects_invalid_classification(self):
        """잘못된 classification 거부"""
        validator = NamingValidator(StrictNamingRules())

        violations = validator.validate("prod.unknown.commerce.orders.v1")

        assert len(violations) > 0


class TestNamingValidatorBatch:
    """배치 검증 테스트"""

    def test_validate_batch(self):
        """여러 토픽 이름 한 번에 검증"""
        validator = NamingValidator(BalancedNamingRules())

        topic_names = [
            "dev.test.topic1",
            "dev.test.topic2",
            "__consumer_offsets",  # 예약어
            "invalid",  # 패턴 불일치
        ]

        violations = validator.validate_batch(topic_names)

        # 최소 2개 위반 (예약어 + 패턴)
        assert len(violations) >= 2
        assert any(v.resource_name == "__consumer_offsets" for v in violations)
        assert any(v.resource_name == "invalid" for v in violations)


class TestDomainPolicyViolation:
    """DomainPolicyViolation 구조 테스트"""

    def test_violation_structure(self):
        """위반 정보에 필수 필드 포함"""
        validator = NamingValidator(BalancedNamingRules())

        violations = validator.validate("invalid-name")

        assert len(violations) > 0
        v = violations[0]

        # 필수 필드 검증
        assert v.resource_type == DomainResourceType.TOPIC
        assert v.resource_name == "invalid-name"
        assert v.rule_id.startswith("naming.")
        assert v.message != ""
        assert v.severity in [DomainPolicySeverity.WARNING, DomainPolicySeverity.ERROR]

    def test_is_blocking(self):
        """ERROR/CRITICAL은 차단"""
        validator = NamingValidator(BalancedNamingRules())

        violations = validator.validate("__consumer_offsets")

        assert len(violations) > 0
        assert violations[0].is_blocking
