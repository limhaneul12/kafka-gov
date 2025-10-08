"""Application Use Cases 테스트"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.topic.application.use_cases import (
    TopicBatchApplyUseCase,
    TopicBatchDryRunUseCase,
)
from app.topic.domain.models import DomainTopicAction
from tests.topic.factories import create_topic_batch, create_topic_plan, create_topic_spec


class TestTopicBatchDryRunUseCase:
    """TopicBatchDryRunUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_dry_run_success(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """정상적인 Dry-Run"""
        use_case = TopicBatchDryRunUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch(
            specs=(create_topic_spec(name="dev.test.topic"),),
        )

        plan = await use_case.execute("default", batch, actor="test-user")

        assert plan.change_id == batch.change_id
        assert len(plan.items) == 1

        # 감사 로그 기록 확인
        assert mock_audit_repository.log_topic_operation.call_count == 2  # STARTED, COMPLETED

        # 계획 저장 확인
        mock_metadata_repository.save_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_dry_run_failure(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """Dry-Run 실패"""
        use_case = TopicBatchDryRunUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch()

        # ConnectionManager 에러 발생
        mock_connection_manager.get_kafka_admin_client.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await use_case.execute("default", batch, actor="test-user")

        # 실패 감사 로그 기록 확인
        calls = mock_audit_repository.log_topic_operation.call_args_list
        assert any("FAILED" in str(call) for call in calls)


class TestTopicBatchApplyUseCase:
    """TopicBatchApplyUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_apply_create_success(
        self,
        mock_connection_manager,
        mock_admin_client,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """토픽 생성 적용"""
        # AdminClient의 create_topics future mock 설정
        mock_future = MagicMock()
        mock_future.result.return_value = None  # 성공
        mock_admin_client.create_topics.return_value = {"dev.test1.topic": mock_future}

        # describe_topics mock 설정 (새 토픽)
        mock_metadata = MagicMock()
        mock_metadata.topics = {}
        mock_admin_client.list_topics.return_value = mock_metadata

        use_case = TopicBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch(
            specs=(create_topic_spec(name="dev.test1.topic"),),
        )

        result = await use_case.execute("default", batch, actor="test-user")

        assert result.change_id == batch.change_id
        assert len(result.applied) == 1
        assert "dev.test1.topic" in result.applied

        # 결과 저장 확인
        mock_metadata_repository.save_apply_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_delete_success(
        self,
        mock_connection_manager,
        mock_admin_client,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """토픽 삭제 적용"""
        # AdminClient의 delete_topics future mock 설정
        mock_future = MagicMock()
        mock_future.result.return_value = None  # 성공
        mock_admin_client.delete_topics.return_value = {"dev.old.topic": mock_future}

        # describe_topics mock 설정 (기존 토픽)
        mock_metadata = MagicMock()
        mock_topic_metadata = MagicMock()
        mock_topic_metadata.partitions = {0: MagicMock()}
        mock_metadata.topics = {"dev.old.topic": mock_topic_metadata}
        mock_admin_client.list_topics.return_value = mock_metadata

        use_case = TopicBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        spec = create_topic_spec(
            name="dev.old.topic",
            action=DomainTopicAction.DELETE,
        )
        batch = create_topic_batch(specs=(spec,))

        result = await use_case.execute("default", batch, actor="test-user")

        assert len(result.applied) == 1
        assert "dev.old.topic" in result.applied

    @pytest.mark.asyncio
    async def test_apply_partial_failure(
        self,
        mock_connection_manager,
        mock_admin_client,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """일부 실패한 적용"""
        from unittest.mock import MagicMock

        # AdminClient의 create_topics future mock 설정 - 1개 성공, 1개 실패
        mock_success_future = MagicMock()
        mock_success_future.result.return_value = None  # 성공

        mock_fail_future = MagicMock()
        mock_fail_future.result.side_effect = Exception("Creation failed")  # 실패

        mock_admin_client.create_topics.return_value = {
            "dev.success.topic": mock_success_future,
            "dev.failure.topic": mock_fail_future,
        }

        # describe_topics mock 설정 (새 토픽)
        mock_metadata = MagicMock()
        mock_metadata.topics = {}
        mock_admin_client.list_topics.return_value = mock_metadata

        use_case = TopicBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch(
            specs=(
                create_topic_spec(name="dev.success.topic"),
                create_topic_spec(name="dev.failure.topic"),
            ),
        )

        result = await use_case.execute("default", batch, actor="test-user")

        assert len(result.applied) == 1
        assert len(result.failed) == 1
        assert result.failed[0]["name"] == "dev.failure.topic"

    @pytest.mark.asyncio
    async def test_apply_with_policy_violation(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """정책 위반으로 적용 차단"""
        use_case = TopicBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        # 잘못된 이름의 토픽 생성 시도 (정책 위반 - 예약어 사용)
        batch = create_topic_batch(
            specs=(create_topic_spec(name="dev.__consumer_offsets"),)  # 예약어 사용 (위반)
        )

        # 정책 검증에서 위반 발생 (내부적으로 처리됨)
        with pytest.raises(ValueError, match="Cannot apply due to policy violations"):
            await use_case.execute("default", batch, actor="test-user")

    @pytest.mark.asyncio
    async def test_apply_partition_change(
        self,
        mock_connection_manager,
        mock_admin_client,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """파티션 수 변경 적용"""
        from tests.topic.factories import create_topic_config

        # 기존 토픽 describe mock 설정
        mock_metadata = MagicMock()
        mock_topic_metadata = MagicMock()
        mock_partition_replicas = [MagicMock(), MagicMock()]  # replication_factor=2
        mock_partition_replicas[0].replicas = [1, 2]
        mock_topic_metadata.partitions = {
            i: mock_partition_replicas[i % 2] for i in range(6)
        }  # 파티션 6개
        mock_metadata.topics = {"dev.existing.topic": mock_topic_metadata}
        mock_admin_client.list_topics.return_value = mock_metadata

        # describe_configs mock 설정 - config 정보 포함
        from confluent_kafka.admin import ConfigResource, ConfigEntry

        mock_config_resource = ConfigResource(ConfigResource.Type.TOPIC, "dev.existing.topic")
        mock_config_future = MagicMock()
        mock_config_result = MagicMock()
        # ConfigEntry 목 객체 생성
        mock_config_entry = MagicMock()
        mock_config_entry.name = "partitions"
        mock_config_entry.value = "6"
        mock_config_result.values.return_value = [mock_config_entry]
        mock_config_future.result.return_value = mock_config_result
        mock_admin_client.describe_configs.return_value = {mock_config_resource: mock_config_future}

        # create_partitions future mock 설정
        mock_partition_future = MagicMock()
        mock_partition_future.result.return_value = None  # 성공
        mock_admin_client.create_partitions.return_value = {
            "dev.existing.topic": mock_partition_future
        }

        # alter_configs future mock 설정
        mock_alter_future = MagicMock()
        mock_alter_future.result.return_value = None  # 성공
        mock_admin_client.alter_configs.return_value = {mock_config_resource: mock_alter_future}

        use_case = TopicBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        spec = create_topic_spec(
            name="dev.existing.topic",
            action=DomainTopicAction.UPDATE,
            config=create_topic_config(partitions=12, replication_factor=2),
        )
        batch = create_topic_batch(specs=(spec,))

        result = await use_case.execute("default", batch, actor="test-user")

        assert len(result.applied) == 1
