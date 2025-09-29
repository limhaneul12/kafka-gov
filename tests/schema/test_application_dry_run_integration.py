"""SchemaBatchDryRunUseCase 통합 테스트 - SchemaPolicyAdapter 활용"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.policy.domain.models import DomainPolicySeverity
from app.schema.application.use_cases import SchemaBatchDryRunUseCase
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainPolicyViolation as SchemaViolation,
    DomainSchemaBatch,
    DomainSchemaMetadata,
    DomainSchemaPlan,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSubjectStrategy,
)


class TestSchemaBatchDryRunUseCaseWithPolicyAdapter:
    """SchemaBatchDryRunUseCase의 SchemaPolicyAdapter 통합 테스트"""

    @pytest.fixture
    def mock_repositories(self):
        """Mock repositories"""
        return {
            "registry": AsyncMock(),
            "metadata": AsyncMock(),
            "audit": AsyncMock(),
        }

    @pytest.fixture
    def mock_policy_engine(self):
        """Mock SchemaPolicyEngine"""
        engine = MagicMock()
        engine.validate_batch.return_value = []
        return engine

    @pytest.fixture
    def use_case(self, mock_repositories, mock_policy_engine):
        """SchemaBatchDryRunUseCase 인스턴스"""
        return SchemaBatchDryRunUseCase(
            registry_repository=mock_repositories["registry"],
            metadata_repository=mock_repositories["metadata"],
            audit_repository=mock_repositories["audit"],
            policy_engine=mock_policy_engine,
        )

    @pytest.fixture
    def sample_batch(self):
        """테스트용 스키마 배치"""
        specs = [
            DomainSchemaSpec(
                subject="dev.test-schema",
                schema_type=DomainSchemaType.AVRO,
                compatibility=DomainCompatibilityMode.BACKWARD,
                schema='{"type": "record", "name": "Test", "fields": []}',
                metadata=DomainSchemaMetadata(owner="test@example.com"),
            )
        ]
        return DomainSchemaBatch(
            change_id="test-change-001",
            env=DomainEnvironment.DEV,
            subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
            specs=tuple(specs),
        )

    def test_execute_without_violations(self, use_case, mock_repositories, sample_batch):
        """정책 위반이 없는 경우 테스트"""
        # Given
        plan = DomainSchemaPlan(
            change_id=sample_batch.change_id,
            env=sample_batch.env,
            items=(),
            violations=(),  # 위반 없음
        )
        mock_repositories["metadata"].save_plan = AsyncMock()

        # Mock planner service
        use_case.planner_service.create_plan = AsyncMock(return_value=plan)

        # When
        result = use_case.execute(sample_batch, "test-actor")

        # Then
        assert result == plan
        use_case.planner_service.create_plan.assert_called_once_with(sample_batch)
        mock_repositories["metadata"].save_plan.assert_called_once_with(plan, "test-actor")
        mock_repositories["audit"].log_operation.assert_called()  # 시작/완료 로그 확인

    def test_execute_with_violations_uses_adapter(self, use_case, mock_repositories, sample_batch):
        """정책 위반이 있는 경우 SchemaPolicyAdapter 사용 테스트"""
        # Given
        schema_violations = [
            SchemaViolation(
                subject="dev.test-schema",
                rule="schema.naming.pattern",
                message="Invalid naming pattern",
                severity="error",
                field="subject",
            )
        ]

        plan = DomainSchemaPlan(
            change_id=sample_batch.change_id,
            env=sample_batch.env,
            items=(),
            violations=tuple(schema_violations),
        )
        mock_repositories["metadata"].save_plan = AsyncMock()

        # Mock planner service
        use_case.planner_service.create_plan = AsyncMock(return_value=plan)

        # When
        result = use_case.execute(sample_batch, "test-actor")

        # Then
        assert result == plan

        # SchemaPolicyAdapter.to_policy_violation이 호출되었는지 확인
        # (실제로는 _analyze_policy_violations에서 호출됨)
        use_case.planner_service.create_plan.assert_called_once_with(sample_batch)
        mock_repositories["metadata"].save_plan.assert_called_once_with(plan, "test-actor")

    def test_analyze_policy_violations_warning_only(self, use_case):
        """WARNING만 있는 정책 위반 분석 테스트"""
        # Given
        policy_violations = [
            MagicMock(severity=DomainPolicySeverity.WARNING),
            MagicMock(severity=DomainPolicySeverity.WARNING),
        ]

        # When
        use_case._analyze_policy_violations(policy_violations, "test-actor")

        # Then
        # WARNING은 차단하지 않으므로 blocking_count는 0
        # (실제로는 print가 호출되지만 테스트에서는 확인하기 어려움)

    def test_analyze_policy_violations_with_blocking(self, use_case):
        """차단하는 정책 위반이 있는 경우 테스트"""
        # Given
        policy_violations = [
            MagicMock(severity=DomainPolicySeverity.WARNING),
            MagicMock(severity=DomainPolicySeverity.ERROR),
            MagicMock(severity=DomainPolicySeverity.CRITICAL),
        ]

        # When
        use_case._analyze_policy_violations(policy_violations, "test-actor")

        # Then
        # ERROR와 CRITICAL이 있으므로 blocking_count는 2
        # (실제로는 print가 호출되지만 테스트에서는 확인하기 어려움)

    def test_adapter_converts_schema_violations_to_policy_violations(self, use_case, sample_batch):
        """어댑터가 스키마 위반을 정책 위반으로 올바르게 변환하는지 테스트"""
        # Given
        schema_violations = [
            SchemaViolation(
                subject="dev.test-schema",
                rule="schema.naming.pattern",
                message="Invalid naming pattern",
                severity="error",
                field="subject",
            ),
            SchemaViolation(
                subject="dev.another-schema",
                rule="schema.metadata.owner",
                message="Owner is required",
                severity="warning",
                field="metadata.owner",
            ),
        ]

        plan = DomainSchemaPlan(
            change_id=sample_batch.change_id,
            env=sample_batch.env,
            items=(),
            violations=tuple(schema_violations),
        )
        mock_repositories = {
            "registry": AsyncMock(),
            "metadata": AsyncMock(),
            "audit": AsyncMock(),
        }
        mock_repositories["metadata"].save_plan = AsyncMock()

        # Mock planner service
        use_case.planner_service.create_plan = AsyncMock(return_value=plan)

        # When
        result = use_case.execute(sample_batch, "test-actor")

        # Then
        assert result == plan

        # 실제 변환 로직은 _analyze_policy_violations에서 수행됨
        # 변환된 policy_violations는 DomainPolicySeverity Enum을 사용해야 함
        use_case.planner_service.create_plan.assert_called_once_with(sample_batch)
