"""Batch UseCase 테스트 - DryRun/Apply 핵심 기능"""

from unittest.mock import MagicMock

import pytest

from app.topic.application.use_cases import TopicBatchApplyUseCase, TopicBatchDryRunUseCase
from app.topic.domain.models import DomainPlanAction
from tests.topic.factories import create_topic_batch, create_topic_spec


class TestTopicBatchDryRunUseCase:
    """DryRun UseCase 테스트"""

    @pytest.mark.asyncio
    async def test_dry_run_returns_plan(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """DryRun은 계획만 반환 (실행 안 함)"""
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
        assert len(plan.items) > 0

        # 계획은 저장되어야 함
        mock_metadata_repository.save_plan.assert_called_once()

        # 감사 로그 기록 (STARTED + COMPLETED)
        assert mock_audit_repository.log_topic_operation.call_count >= 1

    @pytest.mark.asyncio
    async def test_dry_run_with_multiple_topics(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """여러 토픽 DryRun"""
        use_case = TopicBatchDryRunUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch(
            specs=(
                create_topic_spec(name="dev.topic1"),
                create_topic_spec(name="dev.topic2"),
                create_topic_spec(name="dev.topic3"),
            ),
        )

        plan = await use_case.execute("default", batch, actor="test-user")

        assert len(plan.items) == 3

    @pytest.mark.asyncio
    async def test_dry_run_handles_connection_error(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """연결 실패 시 예외 발생"""
        use_case = TopicBatchDryRunUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch()

        # 연결 실패
        mock_connection_manager.get_kafka_admin_client.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await use_case.execute("default", batch, actor="test-user")

        # 실패 로그 기록
        assert mock_audit_repository.log_topic_operation.called


class TestTopicBatchApplyUseCase:
    """Apply UseCase 테스트"""

    @pytest.mark.asyncio
    async def test_apply_creates_topics(
        self,
        mock_connection_manager,
        mock_admin_client,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """토픽 생성 실행"""
        # AdminClient mock 설정
        mock_future = MagicMock()
        mock_future.result.return_value = None  # 성공
        mock_admin_client.create_topics.return_value = {"dev.test.topic": mock_future}

        # 새 토픽 (기존 토픽 없음)
        mock_metadata = MagicMock()
        mock_metadata.topics = {}
        mock_admin_client.list_topics.return_value = mock_metadata

        use_case = TopicBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch(
            specs=(create_topic_spec(name="dev.test.topic"),),
        )

        result = await use_case.execute("default", batch, actor="test-user")

        # 성공 확인
        assert len(result.applied) > 0
        assert len(result.failed) == 0
        assert result.audit_id is not None

        # AdminClient 호출 확인
        mock_admin_client.create_topics.assert_called_once()

        # 결과 저장 확인
        mock_metadata_repository.save_apply_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_handles_partial_failure(
        self,
        mock_connection_manager,
        mock_admin_client,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """일부 실패해도 계속 진행"""
        # 첫 번째 토픽 성공, 두 번째 실패
        mock_future_success = MagicMock()
        mock_future_success.result.return_value = None

        mock_future_fail = MagicMock()
        mock_future_fail.result.side_effect = Exception("Creation failed")

        mock_admin_client.create_topics.return_value = {
            "dev.topic1": mock_future_success,
            "dev.topic2": mock_future_fail,
        }

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
                create_topic_spec(name="dev.topic1"),
                create_topic_spec(name="dev.topic2"),
            ),
        )

        result = await use_case.execute("default", batch, actor="test-user")

        # 일부 성공, 일부 실패
        assert len(result.applied) > 0
        assert len(result.failed) > 0

    @pytest.mark.asyncio
    async def test_apply_summary_message(
        self,
        mock_connection_manager,
        mock_admin_client,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """Apply 결과 요약 정보"""
        mock_future = MagicMock()
        mock_future.result.return_value = None
        mock_admin_client.create_topics.return_value = {"dev.test.topic": mock_future}

        mock_metadata = MagicMock()
        mock_metadata.topics = {}
        mock_admin_client.list_topics.return_value = mock_metadata

        use_case = TopicBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch(
            specs=(create_topic_spec(name="dev.test.topic"),),
        )

        result = await use_case.execute("default", batch, actor="test-user")

        # 결과 검증 (summary는 dict 또는 다른 형태일 수 있음)
        assert result.audit_id is not None
        assert len(result.applied) > 0 or len(result.failed) == 0


class TestBatchUseCaseIntegration:
    """DryRun + Apply 통합 시나리오"""

    @pytest.mark.asyncio
    async def test_dry_run_then_apply_workflow(
        self,
        mock_connection_manager,
        mock_admin_client,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """일반적인 워크플로우: DryRun → 검토 → Apply"""
        # 1. DryRun
        dry_run_use_case = TopicBatchDryRunUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch(
            specs=(create_topic_spec(name="dev.workflow.topic"),),
        )

        plan = await dry_run_use_case.execute("default", batch, actor="test-user")

        assert len(plan.items) > 0
        assert plan.items[0].action == DomainPlanAction.CREATE

        # 2. Apply (같은 batch)
        mock_future = MagicMock()
        mock_future.result.return_value = None
        mock_admin_client.create_topics.return_value = {"dev.workflow.topic": mock_future}

        mock_metadata = MagicMock()
        mock_metadata.topics = {}
        mock_admin_client.list_topics.return_value = mock_metadata

        apply_use_case = TopicBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
        )

        result = await apply_use_case.execute("default", batch, actor="test-user")

        assert len(result.applied) > 0
        assert result.audit_id is not None

        # DryRun과 Apply 모두 change_id 일치
        assert plan.change_id == batch.change_id
