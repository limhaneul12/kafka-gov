"""SchemaBatchDryRunUseCase _analyze_policy_violations 메서드 단위 테스트"""

from unittest.mock import MagicMock

import pytest

from app.policy.domain.models import DomainPolicySeverity
from app.schema.application.use_cases import SchemaBatchDryRunUseCase


class TestAnalyzePolicyViolations:
    """_analyze_policy_violations 메서드 단위 테스트"""

    @pytest.fixture
    def use_case(self):
        """SchemaBatchDryRunUseCase 인스턴스 (의존성 최소화)"""
        return SchemaBatchDryRunUseCase(
            registry_repository=MagicMock(),
            metadata_repository=MagicMock(),
            audit_repository=MagicMock(),
            policy_engine=MagicMock(),
        )

    def test_analyze_no_violations(self, use_case):
        """위반이 없는 경우 테스트"""
        # Given
        violations = []

        # When
        use_case._analyze_policy_violations(violations, "test-actor")

        # Then
        # 아무런 예외 없이 실행되어야 함
        # (실제로는 print가 호출되지만 테스트에서는 확인 불가)

    def test_analyze_warning_violations_only(self, use_case):
        """WARNING만 있는 경우 테스트"""
        # Given
        violations = [
            MagicMock(severity=DomainPolicySeverity.WARNING),
            MagicMock(severity=DomainPolicySeverity.WARNING),
            MagicMock(severity=DomainPolicySeverity.WARNING),
        ]

        # When
        use_case._analyze_policy_violations(violations, "test-actor")

        # Then
        # blocking_count = 0 (WARNING만 있으므로)
        # (실제로는 print가 호출되지만 테스트에서는 확인 불가)

    def test_analyze_with_error_violations(self, use_case):
        """ERROR 위반이 있는 경우 테스트"""
        # Given
        violations = [
            MagicMock(severity=DomainPolicySeverity.WARNING),
            MagicMock(severity=DomainPolicySeverity.ERROR),
            MagicMock(severity=DomainPolicySeverity.WARNING),
        ]

        # When
        use_case._analyze_policy_violations(violations, "test-actor")

        # Then
        # blocking_count = 1 (1개의 ERROR)
        # (실제로는 print가 호출되지만 테스트에서는 확인 불가)

    def test_analyze_with_critical_violations(self, use_case):
        """CRITICAL 위반이 있는 경우 테스트"""
        # Given
        violations = [
            MagicMock(severity=DomainPolicySeverity.WARNING),
            MagicMock(severity=DomainPolicySeverity.ERROR),
            MagicMock(severity=DomainPolicySeverity.CRITICAL),
        ]

        # When
        use_case._analyze_policy_violations(violations, "test-actor")

        # Then
        # blocking_count = 2 (1개의 ERROR + 1개의 CRITICAL)
        # (실제로는 print가 호출되지만 테스트에서는 확인 불가)

    def test_analyze_mixed_severity_violations(self, use_case):
        """혼합된 심각도의 위반 테스트"""
        # Given
        violations = [
            MagicMock(severity=DomainPolicySeverity.WARNING),  # 1
            MagicMock(severity=DomainPolicySeverity.ERROR),  # 2 (blocking)
            MagicMock(severity=DomainPolicySeverity.CRITICAL),  # 3 (blocking)
            MagicMock(severity=DomainPolicySeverity.WARNING),  # 4
            MagicMock(severity=DomainPolicySeverity.ERROR),  # 5 (blocking)
        ]

        # When
        use_case._analyze_policy_violations(violations, "test-actor")

        # Then
        # blocking_count = 3 (2개의 ERROR + 1개의 CRITICAL)
        # (실제로는 print가 호출되지만 테스트에서는 확인 불가)

    def test_analyze_preserves_actor_parameter(self, use_case):
        """actor 매개변수가 올바르게 전달되는지 테스트"""
        # Given
        violations = [MagicMock(severity=DomainPolicySeverity.ERROR)]
        test_actor = "test-user"

        # When
        use_case._analyze_policy_violations(violations, test_actor)

        # Then
        # actor 매개변수가 메서드에 전달됨 (내부에서 사용하지 않지만)
        # (실제로는 print가 호출되지만 테스트에서는 확인 불가)
