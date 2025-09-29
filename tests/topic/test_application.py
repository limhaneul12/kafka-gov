"""Topic 애플리케이션 레이어 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from app.policy.domain.models import (
    DomainPolicySeverity as PolicySeverity,
    DomainPolicyViolation as PolicyViolation,
    DomainResourceType as ResourceType,
)
from app.topic.application.policy_integration import TopicPolicyAdapter
from app.topic.application.use_cases import (
    TopicBatchApplyUseCase,
    TopicBatchDryRunUseCase,
    TopicDetailUseCase,
    TopicPlanUseCase,
)
from app.topic.domain.models import (
    DomainEnvironment as Environment,
    DomainEnvironment as PolicyEnvironment,
    DomainPlanAction as PlanAction,
    DomainTopicAction as TopicAction,
    DomainTopicApplyResult as TopicApplyResult,
    DomainTopicBatch as TopicBatch,
    DomainTopicConfig as TopicConfig,
    DomainTopicMetadata as TopicMetadata,
    DomainTopicPlan as TopicPlan,
    DomainTopicSpec as TopicSpec,
)
from app.topic.domain.repositories.interfaces import (
    IAuditRepository,
    ITopicMetadataRepository,
    ITopicRepository,
)


class TestTopicBatchDryRunUseCase:
    """TopicBatchDryRunUseCase 테스트."""

    @pytest.fixture
    def mock_topic_repository(self) -> AsyncMock:
        """모의 토픽 리포지토리."""
        mock = AsyncMock(spec=ITopicRepository)
        mock.describe_topics.return_value = {}
        return mock

    @pytest.fixture
    def mock_metadata_repository(self) -> AsyncMock:
        """모의 메타데이터 리포지토리."""
        mock = AsyncMock(spec=ITopicMetadataRepository)
        mock.save_plan.return_value = None
        return mock

    @pytest.fixture
    def mock_audit_repository(self) -> AsyncMock:
        """모의 감사 리포지토리."""
        mock = AsyncMock(spec=IAuditRepository)
        mock.log_topic_operation.return_value = "audit-123"
        return mock

    @pytest.fixture
    def mock_policy_adapter(self) -> AsyncMock:
        """모의 정책 어댑터."""
        mock = AsyncMock(spec=TopicPolicyAdapter)
        mock.validate_topic_specs.return_value = []
        return mock

    @pytest.fixture
    def sample_batch(self) -> TopicBatch:
        """샘플 토픽 배치."""
        config = TopicConfig(partitions=3, replication_factor=2)
        metadata = TopicMetadata(owner="data-team")

        spec = TopicSpec(
            name="dev.user.events",
            action=TopicAction.CREATE,
            config=config,
            metadata=metadata,
        )

        return TopicBatch(
            change_id="change-123",
            env=Environment.DEV,
            specs=(spec,),
        )

    @pytest.fixture
    def use_case(
        self,
        mock_topic_repository: AsyncMock,
        mock_metadata_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
        mock_policy_adapter: AsyncMock,
    ) -> TopicBatchDryRunUseCase:
        """DryRun 유스케이스."""
        return TopicBatchDryRunUseCase(
            topic_repository=mock_topic_repository,
            metadata_repository=mock_metadata_repository,
            audit_repository=mock_audit_repository,
            policy_adapter=mock_policy_adapter,
        )

    @pytest.mark.asyncio
    async def test_should_execute_dry_run_successfully(
        self,
        use_case: TopicBatchDryRunUseCase,
        sample_batch: TopicBatch,
        mock_audit_repository: AsyncMock,
        mock_metadata_repository: AsyncMock,
    ) -> None:
        """Dry-run을 성공적으로 실행해야 한다."""
        # Arrange
        actor = "test-user"

        # Act
        result = await use_case.execute(sample_batch, actor)

        # Assert
        assert isinstance(result, TopicPlan)
        assert result.change_id == "change-123"
        assert result.env == Environment.DEV
        assert len(result.items) == 1
        assert result.items[0].action == PlanAction.CREATE

        # 감사 로그 기록 확인
        assert mock_audit_repository.log_topic_operation.call_count == 2

        # 계획 저장 확인
        mock_metadata_repository.save_plan.assert_called_once_with(result, actor)

    @pytest.mark.asyncio
    async def test_should_handle_policy_violations(
        self,
        use_case: TopicBatchDryRunUseCase,
        sample_batch: TopicBatch,
        mock_policy_adapter: AsyncMock,
    ) -> None:
        """정책 위반이 있는 경우를 처리해야 한다."""
        # Arrange
        violation = PolicyViolation(
            resource_type=ResourceType.TOPIC,
            resource_name="dev.user.events",
            rule_id="naming_rule",
            message="토픽 이름이 권장 패턴과 다릅니다",
            severity=PolicySeverity.WARNING,
        )
        mock_policy_adapter.validate_topic_specs.return_value = [violation]
        actor = "test-user"

        # Act
        result = await use_case.execute(sample_batch, actor)

        # Assert
        assert len(result.violations) == 1
        assert result.violations[0] == violation
        assert result.has_violations is True

    @pytest.mark.asyncio
    async def test_should_handle_execution_failure(
        self,
        use_case: TopicBatchDryRunUseCase,
        sample_batch: TopicBatch,
        mock_policy_adapter: AsyncMock,
        mock_audit_repository: AsyncMock,
    ) -> None:
        """실행 실패를 처리해야 한다."""
        # Arrange
        mock_policy_adapter.validate_topic_specs.side_effect = Exception("Policy service error")
        actor = "test-user"

        # Act & Assert
        with pytest.raises(Exception, match="Policy service error"):
            await use_case.execute(sample_batch, actor)

        # 실패 감사 로그 확인
        calls = mock_audit_repository.log_topic_operation.call_args_list
        assert any("FAILED" in str(call) for call in calls)


class TestTopicBatchApplyUseCase:
    """TopicBatchApplyUseCase 테스트."""

    @pytest.fixture
    def mock_topic_repository(self) -> AsyncMock:
        """모의 토픽 리포지토리."""
        mock = AsyncMock(spec=ITopicRepository)
        mock.describe_topics.return_value = {}
        mock.create_topics.return_value = {"dev.user.events": None}  # 성공
        mock.delete_topics.return_value = {}
        mock.create_partitions.return_value = {}
        mock.alter_topic_configs.return_value = {}
        return mock

    @pytest.fixture
    def mock_metadata_repository(self) -> AsyncMock:
        """모의 메타데이터 리포지토리."""
        mock = AsyncMock(spec=ITopicMetadataRepository)
        mock.save_apply_result.return_value = None
        return mock

    @pytest.fixture
    def mock_audit_repository(self) -> AsyncMock:
        """모의 감사 리포지토리."""
        mock = AsyncMock(spec=IAuditRepository)
        mock.log_topic_operation.return_value = "audit-123"
        return mock

    @pytest.fixture
    def mock_policy_adapter(self) -> AsyncMock:
        """모의 정책 어댑터."""
        mock = AsyncMock(spec=TopicPolicyAdapter)
        mock.validate_topic_specs.return_value = []  # 위반 없음
        return mock

    @pytest.fixture
    def sample_batch(self) -> TopicBatch:
        """샘플 토픽 배치."""
        config = TopicConfig(partitions=3, replication_factor=2)
        metadata = TopicMetadata(owner="data-team")

        spec = TopicSpec(
            name="dev.user.events",
            action=TopicAction.CREATE,
            config=config,
            metadata=metadata,
        )

        return TopicBatch(
            change_id="change-123",
            env=Environment.DEV,
            specs=(spec,),
        )

    @pytest.fixture
    def use_case(
        self,
        mock_topic_repository: AsyncMock,
        mock_metadata_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
        mock_policy_adapter: AsyncMock,
    ) -> TopicBatchApplyUseCase:
        """Apply 유스케이스."""
        return TopicBatchApplyUseCase(
            topic_repository=mock_topic_repository,
            metadata_repository=mock_metadata_repository,
            audit_repository=mock_audit_repository,
            policy_adapter=mock_policy_adapter,
        )

    @pytest.mark.asyncio
    async def test_should_execute_apply_successfully(
        self,
        use_case: TopicBatchApplyUseCase,
        sample_batch: TopicBatch,
        mock_topic_repository: AsyncMock,
        mock_metadata_repository: AsyncMock,
    ) -> None:
        """Apply를 성공적으로 실행해야 한다."""
        # Arrange
        actor = "test-user"

        # Act
        result = await use_case.execute(sample_batch, actor)

        # Assert
        assert isinstance(result, TopicApplyResult)
        assert result.change_id == "change-123"
        assert result.env == Environment.DEV
        assert "dev.user.events" in result.applied
        assert len(result.failed) == 0

        # 토픽 생성 확인
        mock_topic_repository.create_topics.assert_called_once()

        # 결과 저장 확인
        mock_metadata_repository.save_apply_result.assert_called_once_with(result, actor)

    @pytest.mark.asyncio
    async def test_should_reject_apply_with_policy_violations(
        self,
        use_case: TopicBatchApplyUseCase,
        sample_batch: TopicBatch,
        mock_policy_adapter: AsyncMock,
    ) -> None:
        """정책 위반이 있으면 적용을 거부해야 한다."""
        # Arrange
        violation = PolicyViolation(
            resource_type=ResourceType.TOPIC,
            resource_name="dev.user.events",
            rule_id="partition_rule",
            message="파티션 수가 너무 적습니다",
            severity=PolicySeverity.ERROR,
        )
        mock_policy_adapter.validate_topic_specs.return_value = [violation]
        actor = "test-user"

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot apply due to policy violations"):
            await use_case.execute(sample_batch, actor)

    @pytest.mark.asyncio
    async def test_should_handle_topic_creation_failure(
        self,
        use_case: TopicBatchApplyUseCase,
        sample_batch: TopicBatch,
        mock_topic_repository: AsyncMock,
    ) -> None:
        """토픽 생성 실패를 처리해야 한다."""
        # Arrange
        error = Exception("Topic creation failed")
        mock_topic_repository.create_topics.return_value = {"dev.user.events": error}
        actor = "test-user"

        # Act
        result = await use_case.execute(sample_batch, actor)

        # Assert
        assert len(result.applied) == 0
        assert len(result.failed) == 1
        assert result.failed[0]["name"] == "dev.user.events"
        assert "Topic creation failed" in result.failed[0]["error"]

    @pytest.mark.asyncio
    async def test_should_handle_delete_action(
        self,
        mock_topic_repository: AsyncMock,
        mock_metadata_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
        mock_policy_adapter: AsyncMock,
    ) -> None:
        """DELETE 액션을 처리해야 한다."""
        # Arrange
        delete_spec = TopicSpec(
            name="dev.deprecated.topic",
            action=TopicAction.DELETE,
            reason="더 이상 사용하지 않음",
        )
        batch = TopicBatch(
            change_id="change-456",
            env=Environment.DEV,
            specs=(delete_spec,),
        )

        mock_topic_repository.delete_topics.return_value = {"dev.deprecated.topic": None}

        use_case = TopicBatchApplyUseCase(
            topic_repository=mock_topic_repository,
            metadata_repository=mock_metadata_repository,
            audit_repository=mock_audit_repository,
            policy_adapter=mock_policy_adapter,
        )
        actor = "test-user"

        # Act
        result = await use_case.execute(batch, actor)

        # Assert
        assert "dev.deprecated.topic" in result.applied
        mock_topic_repository.delete_topics.assert_called_once_with(["dev.deprecated.topic"])


class TestTopicDetailUseCase:
    """TopicDetailUseCase 테스트."""

    @pytest.fixture
    def mock_topic_repository(self) -> AsyncMock:
        """모의 토픽 리포지토리."""
        mock = AsyncMock(spec=ITopicRepository)
        return mock

    @pytest.fixture
    def mock_metadata_repository(self) -> AsyncMock:
        """모의 메타데이터 리포지토리."""
        mock = AsyncMock(spec=ITopicMetadataRepository)
        return mock

    @pytest.fixture
    def use_case(
        self,
        mock_topic_repository: AsyncMock,
        mock_metadata_repository: AsyncMock,
    ) -> TopicDetailUseCase:
        """상세 조회 유스케이스."""
        return TopicDetailUseCase(
            topic_repository=mock_topic_repository,
            metadata_repository=mock_metadata_repository,
        )

    @pytest.mark.asyncio
    async def test_should_return_topic_details(
        self,
        use_case: TopicDetailUseCase,
        mock_topic_repository: AsyncMock,
        mock_metadata_repository: AsyncMock,
    ) -> None:
        """토픽 상세 정보를 반환해야 한다."""
        # Arrange
        topic_name = "dev.user.events"
        kafka_metadata = {
            "partition_count": 3,
            "replication_factor": 2,
            "config": {"cleanup.policy": "delete"},
        }
        topic_metadata = {"owner": "data-team", "sla": "99.9%"}

        mock_topic_repository.describe_topics.return_value = {topic_name: kafka_metadata}
        mock_metadata_repository.get_topic_metadata.return_value = topic_metadata

        # Act
        result = await use_case.execute(topic_name)

        # Assert
        assert result is not None
        assert result["name"] == topic_name
        assert result["kafka_metadata"] == kafka_metadata
        assert result["metadata"] == topic_metadata

    @pytest.mark.asyncio
    async def test_should_return_none_for_nonexistent_topic(
        self,
        use_case: TopicDetailUseCase,
        mock_topic_repository: AsyncMock,
    ) -> None:
        """존재하지 않는 토픽에 대해 None을 반환해야 한다."""
        # Arrange
        topic_name = "nonexistent.topic"
        mock_topic_repository.describe_topics.return_value = {}

        # Act
        result = await use_case.execute(topic_name)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_should_handle_missing_metadata(
        self,
        use_case: TopicDetailUseCase,
        mock_topic_repository: AsyncMock,
        mock_metadata_repository: AsyncMock,
    ) -> None:
        """메타데이터가 없는 경우를 처리해야 한다."""
        # Arrange
        topic_name = "dev.user.events"
        kafka_metadata = {"partition_count": 3}

        mock_topic_repository.describe_topics.return_value = {topic_name: kafka_metadata}
        mock_metadata_repository.get_topic_metadata.return_value = None

        # Act
        result = await use_case.execute(topic_name)

        # Assert
        assert result is not None
        assert result["metadata"] == {}


class TestTopicPlanUseCase:
    """TopicPlanUseCase 테스트."""

    @pytest.fixture
    def mock_metadata_repository(self) -> AsyncMock:
        """모의 메타데이터 리포지토리."""
        mock = AsyncMock(spec=ITopicMetadataRepository)
        return mock

    @pytest.fixture
    def use_case(self, mock_metadata_repository: AsyncMock) -> TopicPlanUseCase:
        """계획 조회 유스케이스."""
        return TopicPlanUseCase(metadata_repository=mock_metadata_repository)

    @pytest.mark.asyncio
    async def test_should_return_existing_plan(
        self,
        use_case: TopicPlanUseCase,
        mock_metadata_repository: AsyncMock,
    ) -> None:
        """기존 계획을 반환해야 한다."""
        # Arrange
        change_id = "change-123"
        plan = TopicPlan(
            change_id=change_id,
            env=Environment.DEV,
            items=(),
            violations=(),
        )
        mock_metadata_repository.get_plan.return_value = plan

        # Act
        result = await use_case.execute(change_id)

        # Assert
        assert result == plan
        mock_metadata_repository.get_plan.assert_called_once_with(change_id)

    @pytest.mark.asyncio
    async def test_should_return_none_for_nonexistent_plan(
        self,
        use_case: TopicPlanUseCase,
        mock_metadata_repository: AsyncMock,
    ) -> None:
        """존재하지 않는 계획에 대해 None을 반환해야 한다."""
        # Arrange
        change_id = "nonexistent-change"
        mock_metadata_repository.get_plan.return_value = None

        # Act
        result = await use_case.execute(change_id)

        # Assert
        assert result is None


class TestTopicPolicyAdapter:
    """TopicPolicyAdapter 테스트."""

    @pytest.fixture
    def mock_policy_service(self) -> AsyncMock:
        """모의 정책 서비스."""
        mock = AsyncMock()
        mock.evaluate_batch.return_value = []
        # 동기 계약을 따르도록 동기 Mock 사용
        mock.has_blocking_violations = Mock(return_value=False)
        return mock

    @pytest.fixture
    def adapter(self, mock_policy_service: AsyncMock) -> TopicPolicyAdapter:
        """정책 어댑터."""
        return TopicPolicyAdapter(mock_policy_service)

    @pytest.fixture
    def sample_spec(self) -> TopicSpec:
        """샘플 토픽 명세."""
        config = TopicConfig(partitions=3, replication_factor=2)
        metadata = TopicMetadata(owner="data-team", sla="99.9%")

        return TopicSpec(
            name="dev.user.events",
            action=TopicAction.CREATE,
            config=config,
            metadata=metadata,
        )

    @pytest.mark.asyncio
    async def test_should_validate_topic_specs(
        self,
        adapter: TopicPolicyAdapter,
        sample_spec: TopicSpec,
        mock_policy_service: AsyncMock,
    ) -> None:
        """토픽 명세들을 검증해야 한다."""
        # Arrange

        environment = PolicyEnvironment.DEV
        actor = "test-user"

        # Act
        result = await adapter.validate_topic_specs(environment, [sample_spec], actor)

        # Assert
        assert result == []
        mock_policy_service.evaluate_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_validate_single_topic(
        self,
        adapter: TopicPolicyAdapter,
        sample_spec: TopicSpec,
        mock_policy_service: AsyncMock,
    ) -> None:
        """단일 토픽을 검증해야 한다."""
        # Arrange

        environment = PolicyEnvironment.DEV
        actor = "test-user"

        # Act
        result = await adapter.validate_single_topic(environment, sample_spec, actor)

        # Assert
        assert result == []
        mock_policy_service.evaluate_batch.assert_called_once()

    def test_should_convert_topic_spec_to_policy_target(
        self,
        adapter: TopicPolicyAdapter,
        sample_spec: TopicSpec,
    ) -> None:
        """TopicSpec을 PolicyTarget으로 변환해야 한다."""
        # Act
        result = adapter._convert_topic_spec_to_policy_target(sample_spec)

        # Assert
        assert result["name"] == "dev.user.events"
        assert result["config"]["partitions"] == 3
        assert result["config"]["replication.factor"] == 2
        assert result["metadata"]["owner"] == "data-team"
        assert result["metadata"]["sla"] == "99.9%"

    def test_should_handle_spec_without_metadata(
        self,
        adapter: TopicPolicyAdapter,
    ) -> None:
        """메타데이터가 없는 명세를 처리해야 한다."""
        # Arrange
        spec = TopicSpec(
            name="dev.test.topic",
            action=TopicAction.DELETE,
            reason="삭제",
        )

        # Act
        result = adapter._convert_topic_spec_to_policy_target(spec)

        # Assert
        assert result["name"] == "dev.test.topic"
        assert result["config"] == {}
        assert result["metadata"] == {}

    def test_should_check_blocking_violations(
        self,
        adapter: TopicPolicyAdapter,
        mock_policy_service: AsyncMock,
    ) -> None:
        """차단 수준 위반을 확인해야 한다."""
        # Arrange
        violations = [
            PolicyViolation(
                resource_type=ResourceType.TOPIC,
                resource_name="test.topic",
                rule_id="test_rule",
                message="Test error",
                severity=PolicySeverity.ERROR,
            )
        ]
        mock_policy_service.has_blocking_violations.return_value = True

        # Act
        result = adapter.has_blocking_violations(violations)

        # Assert
        assert result is True
        mock_policy_service.has_blocking_violations.assert_called_once_with(violations)
