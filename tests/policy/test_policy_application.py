"""Policy 애플리케이션 서비스 테스트"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.policy.application.policy_factory import DefaultPolicyFactory
from app.policy.application.policy_service import (
    PolicyEvaluationService,
    PolicyManagementService,
)
from app.policy.domain.models import (
    DomainConfigurationRule,
    DomainEnvironment,
    DomainNamingRule,
    DomainPolicySet,
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
    PolicyEngine,
)


class TestPolicyEvaluationService:
    """PolicyEvaluationService 테스트"""

    @pytest.fixture
    def policy_engine(self) -> PolicyEngine:
        """정책 엔진 픽스처"""
        engine = PolicyEngine()

        # 테스트용 정책 등록
        naming_rule = DomainNamingRule(pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$", field="name")
        partition_rule = DomainConfigurationRule(
            config_key="partitions",
            min_value=3,
            required=True,
        )

        policy_set = DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(naming_rule, partition_rule),
        )
        engine.register_policy_set(policy_set)

        return engine

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """모의 정책 저장소 픽스처"""
        return AsyncMock()

    @pytest.fixture
    def evaluation_service(
        self, policy_engine: PolicyEngine, mock_repository: AsyncMock
    ) -> PolicyEvaluationService:
        """정책 평가 서비스 픽스처"""
        return PolicyEvaluationService(policy_engine, mock_repository)

    @pytest.fixture
    def evaluation_service_without_repo(
        self, policy_engine: PolicyEngine
    ) -> PolicyEvaluationService:
        """저장소 없는 정책 평가 서비스 픽스처"""
        return PolicyEvaluationService(policy_engine)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_evaluate_single_target_successfully(
        self, evaluation_service_without_repo: PolicyEvaluationService
    ) -> None:
        """단일 대상을 성공적으로 평가해야 한다."""
        # Arrange
        target = {"name": "user-events", "config": {"partitions": 5}}

        # Act
        violations = await evaluation_service_without_repo.evaluate_single(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            target=target,
            actor="test-user",
        )

        # Assert
        assert len(violations) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_evaluate_single_target_with_violations(
        self, evaluation_service_without_repo: PolicyEvaluationService
    ) -> None:
        """위반이 있는 단일 대상을 평가해야 한다."""
        # Arrange
        target = {"name": "InvalidName", "config": {"partitions": 1}}

        # Act
        violations = await evaluation_service_without_repo.evaluate_single(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            target=target,
            actor="test-user",
        )

        # Assert
        assert len(violations) == 2  # 네이밍 + 파티션 위반
        violation_rules = {v.rule_id for v in violations}
        assert "naming.pattern" in violation_rules
        assert "config.partitions" in violation_rules

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_evaluate_batch_targets(
        self, evaluation_service_without_repo: PolicyEvaluationService
    ) -> None:
        """배치 대상들을 평가해야 한다."""
        # Arrange
        targets = [
            {"name": "user-events", "config": {"partitions": 5}},  # 유효
            {"name": "InvalidName", "config": {"partitions": 10}},  # 네이밍 위반
            {"name": "order-events", "config": {"partitions": 1}},  # 파티션 위반
        ]

        # Act
        violations = await evaluation_service_without_repo.evaluate_batch(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            targets=targets,
            actor="test-user",
        )

        # Assert
        assert len(violations) == 2  # 2개의 위반
        violation_rules = {v.rule_id for v in violations}
        assert "naming.pattern" in violation_rules
        assert "config.partitions" in violation_rules

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_load_policy_from_repository_when_available(
        self, evaluation_service: PolicyEvaluationService, mock_repository: AsyncMock
    ) -> None:
        """저장소가 있을 때 정책을 로드해야 한다."""
        # Arrange
        naming_rule = DomainNamingRule(pattern=r"^repo-[a-z]+$")
        repo_policy_set = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            rules=(naming_rule,),
        )
        mock_repository.get_policy_set.return_value = repo_policy_set

        target = {"name": "repo-test"}

        # Act
        violations = await evaluation_service.evaluate_single(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            target=target,
            actor="test-user",
        )

        # Assert
        mock_repository.get_policy_set.assert_called_once_with(
            DomainEnvironment.DEV, DomainResourceType.TOPIC
        )
        assert len(violations) == 0  # 저장소 정책으로 통과

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_handle_repository_returning_none(
        self, evaluation_service: PolicyEvaluationService, mock_repository: AsyncMock
    ) -> None:
        """저장소가 None을 반환할 때를 처리해야 한다."""
        # Arrange
        mock_repository.get_policy_set.return_value = None
        target = {"name": "any-name"}

        # Act
        violations = await evaluation_service.evaluate_single(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            target=target,
            actor="test-user",
        )

        # Assert
        mock_repository.get_policy_set.assert_called_once()
        assert len(violations) == 0  # 정책이 없으면 통과

    @pytest.mark.unit
    def test_should_identify_blocking_violations(
        self, evaluation_service_without_repo: PolicyEvaluationService
    ) -> None:
        """차단 수준의 위반을 식별해야 한다."""
        # Arrange
        violations = [
            DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name="test",
                rule_id="rule1",
                message="Warning",
                severity=DomainPolicySeverity.WARNING,
            ),
            DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name="test",
                rule_id="rule2",
                message="Error",
                severity=DomainPolicySeverity.ERROR,
            ),
        ]

        # Act
        has_blocking = evaluation_service_without_repo.has_blocking_violations(violations)

        # Assert
        assert has_blocking is True

    @pytest.mark.unit
    def test_should_not_identify_blocking_violations_for_warnings_only(
        self, evaluation_service_without_repo: PolicyEvaluationService
    ) -> None:
        """경고만 있을 때는 차단으로 식별하지 않아야 한다."""
        # Arrange
        violations = [
            DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name="test",
                rule_id="rule1",
                message="Warning",
                severity=DomainPolicySeverity.WARNING,
            ),
        ]

        # Act
        has_blocking = evaluation_service_without_repo.has_blocking_violations(violations)

        # Assert
        assert has_blocking is False

    @pytest.mark.unit
    def test_should_group_violations_by_severity(
        self, evaluation_service_without_repo: PolicyEvaluationService
    ) -> None:
        """심각도별로 위반을 그룹화해야 한다."""
        # Arrange
        violations = [
            DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name="test1",
                rule_id="rule1",
                message="Warning",
                severity=DomainPolicySeverity.WARNING,
            ),
            DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name="test2",
                rule_id="rule2",
                message="Error",
                severity=DomainPolicySeverity.ERROR,
            ),
            DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name="test3",
                rule_id="rule3",
                message="Another Warning",
                severity=DomainPolicySeverity.WARNING,
            ),
        ]

        # Act
        groups = evaluation_service_without_repo.group_violations_by_severity(violations)

        # Assert
        assert len(groups) == 2
        assert len(groups["warning"]) == 2
        assert len(groups["error"]) == 1
        assert "critical" not in groups


class TestPolicyManagementService:
    """PolicyManagementService 테스트"""

    @pytest.fixture
    def policy_engine(self) -> PolicyEngine:
        """정책 엔진 픽스처"""
        return PolicyEngine()

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """모의 정책 저장소 픽스처"""
        return AsyncMock()

    @pytest.fixture
    def management_service(
        self, policy_engine: PolicyEngine, mock_repository: AsyncMock
    ) -> PolicyManagementService:
        """정책 관리 서비스 픽스처"""
        return PolicyManagementService(policy_engine, mock_repository)

    @pytest.fixture
    def sample_policy_set(self) -> DomainPolicySet:
        """샘플 정책 집합 픽스처"""
        naming_rule = DomainNamingRule(pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$")
        return DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(naming_rule,),
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_load_all_policies_from_repository(
        self, management_service: PolicyManagementService, mock_repository: AsyncMock
    ) -> None:
        """저장소에서 모든 정책을 로드해야 한다."""
        # Arrange
        mock_repository.list_environments.return_value = [
            DomainEnvironment.PROD,
            DomainEnvironment.DEV,
        ]
        mock_repository.list_resource_types.side_effect = [
            [DomainResourceType.TOPIC],  # PROD
            [DomainResourceType.TOPIC, DomainResourceType.SCHEMA],  # DEV
        ]

        prod_policy = DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(),
        )
        dev_topic_policy = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            rules=(),
        )
        dev_schema_policy = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.SCHEMA,
            rules=(),
        )

        mock_repository.get_policy_set.side_effect = [
            prod_policy,
            dev_topic_policy,
            dev_schema_policy,
        ]

        # Act
        await management_service.load_all_policies()

        # Assert
        mock_repository.list_environments.assert_called_once()
        assert mock_repository.list_resource_types.call_count == 2
        assert mock_repository.get_policy_set.call_count == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_update_policy_set(
        self,
        management_service: PolicyManagementService,
        mock_repository: AsyncMock,
        sample_policy_set: DomainPolicySet,
    ) -> None:
        """정책 집합을 업데이트해야 한다."""
        # Act
        await management_service.update_policy_set(
            DomainEnvironment.PROD,
            DomainResourceType.TOPIC,
            sample_policy_set,
        )

        # Assert
        mock_repository.save_policy_set.assert_called_once_with(sample_policy_set)

        # 엔진에 등록되었는지 확인
        retrieved = management_service.get_active_policy_set(
            DomainEnvironment.PROD, DomainResourceType.TOPIC
        )
        assert retrieved == sample_policy_set

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_delete_policy_set(
        self, management_service: PolicyManagementService, mock_repository: AsyncMock
    ) -> None:
        """정책 집합을 삭제해야 한다."""
        # Arrange
        mock_repository.delete_policy_set.return_value = True

        # Act
        result = await management_service.delete_policy_set(
            DomainEnvironment.PROD, DomainResourceType.TOPIC
        )

        # Assert
        assert result is True
        mock_repository.delete_policy_set.assert_called_once_with(
            DomainEnvironment.PROD, DomainResourceType.TOPIC
        )

    @pytest.mark.unit
    def test_should_get_active_policy_set(
        self, management_service: PolicyManagementService, sample_policy_set: DomainPolicySet
    ) -> None:
        """활성화된 정책 집합을 조회해야 한다."""
        # Arrange
        management_service._policy_engine.register_policy_set(sample_policy_set)

        # Act
        retrieved = management_service.get_active_policy_set(
            DomainEnvironment.PROD, DomainResourceType.TOPIC
        )

        # Assert
        assert retrieved == sample_policy_set

    @pytest.mark.unit
    def test_should_return_none_for_nonexistent_policy_set(
        self, management_service: PolicyManagementService
    ) -> None:
        """존재하지 않는 정책 집합에 대해 None을 반환해야 한다."""
        # Act
        retrieved = management_service.get_active_policy_set(
            DomainEnvironment.DEV, DomainResourceType.SCHEMA
        )

        # Assert
        assert retrieved is None


class TestDefaultPolicyFactory:
    """DefaultPolicyFactory 테스트"""

    @pytest.mark.unit
    def test_should_create_topic_policies_for_all_environments(self) -> None:
        """모든 환경에 대한 토픽 정책을 생성해야 한다."""
        # Act
        policies = DefaultPolicyFactory.create_topic_policies()

        # Assert
        assert len(policies) == 3
        assert DomainEnvironment.DEV in policies
        assert DomainEnvironment.STG in policies
        assert DomainEnvironment.PROD in policies

        # 각 정책 집합 검증
        for env, policy_set in policies.items():
            assert policy_set.environment == env
            assert policy_set.resource_type == DomainResourceType.TOPIC
            assert len(policy_set.rules) > 0

    @pytest.mark.unit
    def test_should_create_schema_policies_for_all_environments(self) -> None:
        """모든 환경에 대한 스키마 정책을 생성해야 한다."""
        # Act
        policies = DefaultPolicyFactory.create_schema_policies()

        # Assert
        assert len(policies) == 3
        assert DomainEnvironment.DEV in policies
        assert DomainEnvironment.STG in policies
        assert DomainEnvironment.PROD in policies

        # 각 정책 집합 검증
        for env, policy_set in policies.items():
            assert policy_set.environment == env
            assert policy_set.resource_type == DomainResourceType.SCHEMA
            assert len(policy_set.rules) > 0

    @pytest.mark.unit
    def test_should_have_different_rules_per_environment_for_topics(self) -> None:
        """환경별로 다른 토픽 규칙을 가져야 한다."""
        # Act
        policies = DefaultPolicyFactory.create_topic_policies()

        # Assert
        dev_policy = policies[DomainEnvironment.DEV]
        stg_policy = policies[DomainEnvironment.STG]
        prod_policy = policies[DomainEnvironment.PROD]

        # DEV는 가장 관대한 정책
        dev_naming = next(r for r in dev_policy.rules if isinstance(r, DomainNamingRule))
        assert "dev." in dev_naming.pattern
        assert len(dev_naming.forbidden_prefixes) == 0

        # STG는 중간 수준
        stg_naming = next(r for r in stg_policy.rules if isinstance(r, DomainNamingRule))
        assert "stg." in stg_naming.pattern
        assert len(stg_naming.forbidden_prefixes) > 0

        # PROD는 가장 엄격한 정책
        prod_naming = next(r for r in prod_policy.rules if isinstance(r, DomainNamingRule))
        assert "prod." in prod_naming.pattern
        assert len(prod_naming.forbidden_prefixes) > len(stg_naming.forbidden_prefixes)

    @pytest.mark.unit
    def test_should_have_stricter_partition_rules_in_prod(self) -> None:
        """PROD에서 더 엄격한 파티션 규칙을 가져야 한다."""
        # Act
        policies = DefaultPolicyFactory.create_topic_policies()

        # Assert
        dev_policy = policies[DomainEnvironment.DEV]
        prod_policy = policies[DomainEnvironment.PROD]

        dev_partition_rule = next(
            r
            for r in dev_policy.rules
            if isinstance(r, DomainConfigurationRule) and r.config_key == "partitions"
        )
        prod_partition_rule = next(
            r
            for r in prod_policy.rules
            if isinstance(r, DomainConfigurationRule) and r.config_key == "partitions"
        )

        # PROD는 최소 파티션 수가 더 높아야 함
        assert prod_partition_rule.min_value > dev_partition_rule.min_value

    @pytest.mark.unit
    def test_should_require_compression_in_prod_topics(self) -> None:
        """PROD 토픽에서 압축을 필수로 해야 한다."""
        # Act
        policies = DefaultPolicyFactory.create_topic_policies()

        # Assert
        prod_policy = policies[DomainEnvironment.PROD]
        compression_rule = next(
            r
            for r in prod_policy.rules
            if isinstance(r, DomainConfigurationRule) and r.config_key == "compression.type"
        )

        assert compression_rule.required is True
        assert compression_rule.allowed_values == ("zstd",)

    @pytest.mark.unit
    def test_should_have_environment_specific_schema_patterns(self) -> None:
        """환경별로 특정한 스키마 패턴을 가져야 한다."""
        # Act
        policies = DefaultPolicyFactory.create_schema_policies()

        # Assert
        for env, policy_set in policies.items():
            naming_rule = next(r for r in policy_set.rules if isinstance(r, DomainNamingRule))
            assert env.value in naming_rule.pattern
            assert "(-key|-value)?" in naming_rule.pattern
