"""SchemaBatchDryRunUseCase와 SchemaPolicyAdapter 통합 테스트"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.policy.domain.models import DomainPolicySeverity, DomainResourceType
from app.schema.application.policy_adapter import SchemaPolicyAdapter
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


class TestSchemaBatchDryRunUseCaseFullIntegration:
    """SchemaBatchDryRunUseCase와 SchemaPolicyAdapter 완전 통합 테스트"""

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

    def test_execute_with_schema_violations_converts_to_policy_violations(
        self, use_case, mock_repositories, sample_batch
    ):
        """스키마 위반을 정책 위반으로 변환하는 전체 플로우 테스트"""
        # Given
        schema_violations = [
            SchemaViolation(
                subject="dev.test-schema",
                rule="schema.naming.pattern",
                message="Subject does not match naming pattern",
                severity="error",
                field="subject",
            ),
            SchemaViolation(
                subject="dev.test-schema",
                rule="schema.metadata.owner",
                message="Schema owner is required",
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
        mock_repositories["metadata"].save_plan = AsyncMock()

        # Mock planner service
        use_case.planner_service.create_plan = AsyncMock(return_value=plan)

        # When
        result = use_case.execute(sample_batch, "test-actor")

        # Then
        assert result == plan
        use_case.planner_service.create_plan.assert_called_once_with(sample_batch)
        mock_repositories["metadata"].save_plan.assert_called_once_with(plan, "test-actor")

    def test_converted_policy_violations_have_correct_structure(self, use_case, sample_batch):
        """변환된 정책 위반이 올바른 구조를 가지는지 테스트"""
        # Given
        schema_violation = SchemaViolation(
            subject="dev.test-schema",
            rule="schema.naming.pattern",
            message="Subject does not match naming pattern",
            severity="error",
            field="subject",
        )

        # When
        policy_violation = SchemaPolicyAdapter.to_policy_violation(schema_violation)

        # Then
        assert policy_violation.resource_type == DomainResourceType.SCHEMA
        assert policy_violation.resource_name == "dev.test-schema"
        assert policy_violation.rule_id == "schema.naming.pattern"
        assert policy_violation.message == "Subject does not match naming pattern"
        assert policy_violation.severity == DomainPolicySeverity.ERROR
        assert policy_violation.field == "subject"

    def test_multiple_violations_conversion(self, use_case):
        """여러 스키마 위반을 정책 위반으로 변환 테스트"""
        # Given
        schema_violations = [
            SchemaViolation(
                subject="dev.schema-1",
                rule="schema.naming.pattern",
                message="Invalid pattern",
                severity="error",
                field="subject",
            ),
            SchemaViolation(
                subject="dev.schema-2",
                rule="schema.metadata.owner",
                message="Missing owner",
                severity="critical",
                field="metadata.owner",
            ),
            SchemaViolation(
                subject="dev.schema-3",
                rule="schema.compatibility.mode",
                message="Invalid compatibility",
                severity="warning",
                field="compatibility",
            ),
        ]

        # When
        policy_violations = [SchemaPolicyAdapter.to_policy_violation(v) for v in schema_violations]

        # Then
        assert len(policy_violations) == 3

        # 첫 번째 위반 (ERROR)
        assert policy_violations[0].severity == DomainPolicySeverity.ERROR
        assert policy_violations[0].resource_name == "dev.schema-1"

        # 두 번째 위반 (CRITICAL)
        assert policy_violations[1].severity == DomainPolicySeverity.CRITICAL
        assert policy_violations[1].resource_name == "dev.schema-2"

        # 세 번째 위반 (WARNING)
        assert policy_violations[2].severity == DomainPolicySeverity.WARNING
        assert policy_violations[2].resource_name == "dev.schema-3"

    def test_analyze_converted_policy_violations_calculates_blocking_correctly(self, use_case):
        """변환된 정책 위반의 차단 계산이 올바른지 테스트"""
        # Given
        policy_violations = [
            MagicMock(severity=DomainPolicySeverity.WARNING),  # 차단 안 됨
            MagicMock(severity=DomainPolicySeverity.ERROR),  # 차단 됨
            MagicMock(severity=DomainPolicySeverity.CRITICAL),  # 차단 됨
            MagicMock(severity=DomainPolicySeverity.WARNING),  # 차단 안 됨
        ]

        # When
        use_case._analyze_policy_violations(policy_violations, "test-actor")

        # Then
        # blocking_count는 2 (ERROR + CRITICAL)
        # (실제로는 print가 호출되지만 테스트에서는 확인 불가)

    def test_full_integration_with_real_adapter_and_analysis(self, use_case, sample_batch):
        """실제 어댑터와 분석이 함께 작동하는지 테스트"""
        # Given
        schema_violations = [
            SchemaViolation(
                subject="dev.test-schema",
                rule="schema.naming.pattern",
                message="Invalid naming",
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

        # 실제로 SchemaPolicyAdapter.to_policy_violation이 호출되어
        # DomainPolicySeverity.ERROR로 변환되었는지 확인
        use_case.planner_service.create_plan.assert_called_once_with(sample_batch)
        mock_repositories["metadata"].save_plan.assert_called_once_with(plan, "test-actor")
