"""Topic 인프라스트럭처 레이어 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from confluent_kafka.admin import AdminClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.policy.domain.models import (
    DomainPolicySeverity as PolicySeverity,
    DomainPolicyViolation as PolicyViolation,
    DomainResourceType as ResourceType,
)
from app.topic.domain.models import (
    DomainEnvironment as Environment,
    DomainPlanAction as PlanAction,
    DomainTopicAction as TopicAction,
    DomainTopicApplyResult as TopicApplyResult,
    DomainTopicConfig as TopicConfig,
    DomainTopicMetadata as TopicMetadata,
    DomainTopicPlan as TopicPlan,
    DomainTopicPlanItem as TopicPlanItem,
    DomainTopicSpec as TopicSpec,
)
from app.topic.infrastructure.kafka_adapter import KafkaTopicAdapter
from app.topic.infrastructure.repository.audit_repository import MySQLAuditRepository
from app.topic.infrastructure.repository.mysql_repository import MySQLTopicMetadataRepository


class TestKafkaTopicAdapter:
    """KafkaTopicAdapter 테스트."""

    @pytest.fixture
    def mock_admin_client(self) -> MagicMock:
        """모의 AdminClient."""
        return MagicMock(spec=AdminClient)

    @pytest.fixture
    def adapter(self, mock_admin_client: MagicMock) -> KafkaTopicAdapter:
        """Kafka 어댑터."""
        return KafkaTopicAdapter(mock_admin_client)

    @pytest.fixture
    def sample_spec(self) -> TopicSpec:
        """샘플 토픽 명세."""
        config = TopicConfig(partitions=3, replication_factor=2)
        metadata = TopicMetadata(owner="data-team")

        return TopicSpec(
            name="dev.user.events",
            action=TopicAction.CREATE,
            config=config,
            metadata=metadata,
        )

    @pytest.mark.asyncio
    async def test_should_get_topic_metadata(
        self,
        adapter: KafkaTopicAdapter,
        mock_admin_client: MagicMock,
    ) -> None:
        """토픽 메타데이터를 조회해야 한다."""
        # Arrange
        topic_name = "dev.user.events"
        expected_metadata = {
            "partition_count": 3,
            "replication_factor": 2,
            "config": {"cleanup.policy": "delete"},
        }

        # describe_topics 메서드 모킹
        with patch.object(adapter, "describe_topics") as mock_describe:
            mock_describe.return_value = {topic_name: expected_metadata}

            # Act
            result = await adapter.get_topic_metadata(topic_name)

            # Assert
            assert result == expected_metadata
            mock_describe.assert_called_once_with([topic_name])

    @pytest.mark.asyncio
    async def test_should_return_none_for_nonexistent_topic(
        self,
        adapter: KafkaTopicAdapter,
    ) -> None:
        """존재하지 않는 토픽에 대해 None을 반환해야 한다."""
        # Arrange
        topic_name = "nonexistent.topic"

        with patch.object(adapter, "describe_topics") as mock_describe:
            mock_describe.return_value = {}

            # Act
            result = await adapter.get_topic_metadata(topic_name)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_should_create_topics_successfully(
        self,
        adapter: KafkaTopicAdapter,
        mock_admin_client: MagicMock,
        sample_spec: TopicSpec,
    ) -> None:
        """토픽을 성공적으로 생성해야 한다."""
        # Arrange
        future_mock = MagicMock()
        future_mock.result.return_value = None  # 성공

        mock_admin_client.create_topics.return_value = {"dev.user.events": future_mock}

        # Act
        result = await adapter.create_topics([sample_spec])

        # Assert
        assert result == {"dev.user.events": None}
        mock_admin_client.create_topics.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_topic_creation_failure(
        self,
        adapter: KafkaTopicAdapter,
        mock_admin_client: MagicMock,
        sample_spec: TopicSpec,
    ) -> None:
        """토픽 생성 실패를 처리해야 한다."""
        # Arrange
        error = Exception("Topic already exists")
        future_mock = MagicMock()
        future_mock.result.side_effect = error

        mock_admin_client.create_topics.return_value = {"dev.user.events": future_mock}

        # Act
        result = await adapter.create_topics([sample_spec])

        # Assert
        assert result["dev.user.events"] == error

    @pytest.mark.asyncio
    async def test_should_delete_topics_successfully(
        self,
        adapter: KafkaTopicAdapter,
        mock_admin_client: MagicMock,
    ) -> None:
        """토픽을 성공적으로 삭제해야 한다."""
        # Arrange
        topic_names = ["dev.user.events", "dev.order.events"]
        future_mock = MagicMock()
        future_mock.result.return_value = None  # 성공

        mock_admin_client.delete_topics.return_value = dict.fromkeys(topic_names, future_mock)

        # Act
        result = await adapter.delete_topics(topic_names)

        # Assert
        expected = dict.fromkeys(topic_names)
        assert result == expected
        mock_admin_client.delete_topics.assert_called_once_with(
            topic_names,
            operation_timeout=30.0,
            request_timeout=60.0,
        )

    @pytest.mark.asyncio
    async def test_should_handle_empty_specs_list(
        self,
        adapter: KafkaTopicAdapter,
        mock_admin_client: MagicMock,
    ) -> None:
        """빈 명세 리스트를 처리해야 한다."""
        # Act
        result = await adapter.create_topics([])

        # Assert
        assert result == {}
        mock_admin_client.create_topics.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_handle_specs_without_config(
        self,
        adapter: KafkaTopicAdapter,
        mock_admin_client: MagicMock,
    ) -> None:
        """설정이 없는 명세를 처리해야 한다."""
        # Arrange
        spec = TopicSpec(
            name="dev.test.topic",
            action=TopicAction.DELETE,
            reason="삭제",
        )

        # Act
        result = await adapter.create_topics([spec])

        # Assert
        assert result == {}
        mock_admin_client.create_topics.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_alter_topic_configs(
        self,
        adapter: KafkaTopicAdapter,
        mock_admin_client: MagicMock,
    ) -> None:
        """토픽 설정을 변경해야 한다."""
        # Arrange
        configs = {
            "dev.user.events": {"retention.ms": "86400000"},
            "dev.order.events": {"cleanup.policy": "compact"},
        }
        future_mock = MagicMock()
        future_mock.result.return_value = None  # 성공

        mock_admin_client.alter_configs.return_value = {
            f"TOPIC:{name}": future_mock for name in configs
        }

        # Act
        result = await adapter.alter_topic_configs(configs)

        # Assert
        expected = dict.fromkeys(configs.keys())
        assert result == expected
        mock_admin_client.alter_configs.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_create_partitions(
        self,
        adapter: KafkaTopicAdapter,
        mock_admin_client: MagicMock,
    ) -> None:
        """파티션을 생성해야 한다."""
        # Arrange
        partitions = {
            "dev.user.events": 6,
            "dev.order.events": 9,
        }
        future_mock = MagicMock()
        future_mock.result.return_value = None  # 성공

        mock_admin_client.create_partitions.return_value = dict.fromkeys(
            partitions.keys(), future_mock
        )

        # Act
        result = await adapter.create_partitions(partitions)

        # Assert
        expected = dict.fromkeys(partitions.keys())
        assert result == expected
        mock_admin_client.create_partitions.assert_called_once()


class TestMySQLTopicMetadataRepository:
    """MySQLTopicMetadataRepository 테스트."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """모의 데이터베이스 세션."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> MySQLTopicMetadataRepository:
        """MySQL 메타데이터 리포지토리."""
        return MySQLTopicMetadataRepository(mock_session)

    @pytest.fixture
    def sample_plan(self) -> TopicPlan:
        """샘플 토픽 계획."""
        item = TopicPlanItem(
            name="dev.user.events",
            action=PlanAction.CREATE,
            diff={"status": "new→created"},
            target_config={"partitions": "3", "replication.factor": "2"},
        )

        violation = PolicyViolation(
            resource_type=ResourceType.TOPIC,
            resource_name="dev.user.events",
            rule_id="naming_rule",
            message="토픽 이름이 권장 패턴과 다릅니다",
            severity=PolicySeverity.WARNING,
        )

        return TopicPlan(
            change_id="change-123",
            env=Environment.DEV,
            items=(item,),
            violations=(violation,),
        )

    @pytest.fixture
    def sample_apply_result(self) -> TopicApplyResult:
        """샘플 적용 결과."""
        return TopicApplyResult(
            change_id="change-123",
            env=Environment.DEV,
            applied=("dev.user.events",),
            skipped=(),
            failed=(),
            audit_id="audit-456",
        )

    @pytest.mark.asyncio
    async def test_should_save_plan(
        self,
        repository: MySQLTopicMetadataRepository,
        mock_session: AsyncMock,
        sample_plan: TopicPlan,
    ) -> None:
        """계획을 저장해야 한다."""
        # Arrange
        actor = "test-user"

        # Act
        await repository.save_plan(sample_plan, actor)

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_save_plan_error(
        self,
        repository: MySQLTopicMetadataRepository,
        mock_session: AsyncMock,
        sample_plan: TopicPlan,
    ) -> None:
        """계획 저장 에러를 처리해야 한다."""
        # Arrange
        mock_session.flush.side_effect = Exception("Database error")
        actor = "test-user"

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await repository.save_plan(sample_plan, actor)

    @pytest.mark.asyncio
    async def test_should_get_plan(
        self,
        repository: MySQLTopicMetadataRepository,
        mock_session: AsyncMock,
    ) -> None:
        """계획을 조회해야 한다."""
        # Arrange
        change_id = "change-123"

        # 모의 계획 모델 생성
        mock_plan_model = MagicMock()
        mock_plan_model.plan_data = {
            "change_id": change_id,
            "env": "dev",
            "items": [
                {
                    "name": "dev.user.events",
                    "action": "CREATE",
                    "diff": {"status": "new→created"},
                    "current_config": None,
                    "target_config": {"partitions": "3"},
                }
            ],
            "violations": [],
        }

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_plan_model
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_plan(change_id)

        # Assert
        assert result is not None
        assert result.change_id == change_id
        assert result.env == Environment.DEV
        assert len(result.items) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_return_none_for_nonexistent_plan(
        self,
        repository: MySQLTopicMetadataRepository,
        mock_session: AsyncMock,
    ) -> None:
        """존재하지 않는 계획에 대해 None을 반환해야 한다."""
        # Arrange
        change_id = "nonexistent-change"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_plan(change_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_should_save_apply_result(
        self,
        repository: MySQLTopicMetadataRepository,
        mock_session: AsyncMock,
        sample_apply_result: TopicApplyResult,
    ) -> None:
        """적용 결과를 저장해야 한다."""
        # Arrange
        actor = "test-user"

        # Act
        await repository.save_apply_result(sample_apply_result, actor)

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_get_topic_metadata(
        self,
        repository: MySQLTopicMetadataRepository,
        mock_session: AsyncMock,
    ) -> None:
        """토픽 메타데이터를 조회해야 한다."""
        # Arrange
        topic_name = "dev.user.events"

        mock_metadata_model = MagicMock()
        mock_metadata_model.owner = "data-team"
        mock_metadata_model.sla = "99.9%"
        mock_metadata_model.doc = "https://docs.example.com/topic"
        mock_metadata_model.tags = ["critical", "real-time"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_metadata_model
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_topic_metadata(topic_name)

        # Assert
        assert result is not None
        assert result["owner"] == "data-team"
        assert result["sla"] == "99.9%"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_save_topic_metadata(
        self,
        repository: MySQLTopicMetadataRepository,
        mock_session: AsyncMock,
    ) -> None:
        """토픽 메타데이터를 저장해야 한다."""
        # Arrange
        topic_name = "dev.user.events"
        metadata = {
            "owner": "data-team",
            "sla": "99.9%",
            "doc": "https://docs.example.com/topic",
            "tags": ["critical", "real-time"],
        }

        # Act
        await repository.save_topic_metadata(topic_name, metadata)

        # Assert
        mock_session.merge.assert_called_once()
        mock_session.flush.assert_called_once()


class TestMySQLAuditRepository:
    """MySQLAuditRepository 테스트."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """모의 데이터베이스 세션."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> MySQLAuditRepository:
        """MySQL 감사 리포지토리."""
        return MySQLAuditRepository(mock_session)

    @pytest.mark.asyncio
    async def test_should_log_topic_operation(
        self,
        repository: MySQLAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """토픽 작업을 감사 로그에 기록해야 한다."""
        # Arrange
        change_id = "change-123"
        action = "CREATE"
        target = "dev.user.events"
        actor = "test-user"
        status = "SUCCESS"
        message = "Topic created successfully"
        snapshot = {"partitions": 3, "replication_factor": 2}

        # 모의 감사 로그 모델
        mock_audit_log = MagicMock()
        mock_audit_log.id = 12345
        mock_session.add.return_value = None
        mock_session.flush.return_value = None

        # Act
        with patch(
            "app.topic.infrastructure.repository.audit_repository.AuditLogModel"
        ) as mock_model:
            mock_model.return_value = mock_audit_log

            result = await repository.log_topic_operation(
                change_id=change_id,
                action=action,
                target=target,
                actor=actor,
                status=status,
                message=message,
                snapshot=snapshot,
            )

        # Assert
        assert result == "12345"
        mock_session.add.assert_called_once_with(mock_audit_log)
        mock_session.flush.assert_called_once()

        # 모델 생성 인자 확인
        mock_model.assert_called_once_with(
            change_id=change_id,
            action=action,
            target=target,
            actor=actor,
            status=status,
            message=message,
            snapshot=snapshot,
        )

    @pytest.mark.asyncio
    async def test_should_handle_log_operation_error(
        self,
        repository: MySQLAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """감사 로그 기록 에러를 처리해야 한다."""
        # Arrange
        mock_session.flush.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await repository.log_topic_operation(
                change_id="change-123",
                action="CREATE",
                target="dev.user.events",
                actor="test-user",
                status="SUCCESS",
            )

    @pytest.mark.asyncio
    async def test_should_handle_none_snapshot(
        self,
        repository: MySQLAuditRepository,
        mock_session: AsyncMock,
    ) -> None:
        """None 스냅샷을 처리해야 한다."""
        # Arrange
        mock_audit_log = MagicMock()
        mock_audit_log.id = 12345

        # Act
        with patch(
            "app.topic.infrastructure.repository.audit_repository.AuditLogModel"
        ) as mock_model:
            mock_model.return_value = mock_audit_log

            result = await repository.log_topic_operation(
                change_id="change-123",
                action="CREATE",
                target="dev.user.events",
                actor="test-user",
                status="SUCCESS",
                snapshot=None,
            )

        # Assert
        assert result == "12345"
        # snapshot=None이 {}로 변환되는지 확인
        call_args = mock_model.call_args
        assert call_args[1]["snapshot"] == {}
