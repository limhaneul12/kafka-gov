"""Application Use Cases 테스트"""

from __future__ import annotations

import pytest

from app.topic.application.use_cases import (
    TopicBatchApplyUseCase,
    TopicBatchDryRunUseCase,
    TopicDetailUseCase,
    TopicPlanUseCase,
)
from app.topic.domain.models import DomainTopicAction
from tests.topic.factories import create_topic_batch, create_topic_plan, create_topic_spec


class TestTopicBatchDryRunUseCase:
    """TopicBatchDryRunUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_dry_run_success(
        self,
        mock_topic_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """정상적인 Dry-Run"""
        use_case = TopicBatchDryRunUseCase(
            mock_topic_repository,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch(
            specs=(create_topic_spec(name="dev.test.topic"),),
        )

        # Repository: 새 토픽
        mock_topic_repository.describe_topics.return_value = {}

        plan = await use_case.execute(batch, actor="test-user")

        assert plan.change_id == batch.change_id
        assert len(plan.items) == 1

        # 감사 로그 기록 확인
        assert mock_audit_repository.log_topic_operation.call_count == 2  # STARTED, COMPLETED

        # 계획 저장 확인
        mock_metadata_repository.save_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_dry_run_failure(
        self,
        mock_topic_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """Dry-Run 실패"""
        use_case = TopicBatchDryRunUseCase(
            mock_topic_repository,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch()

        # Repository 에러 발생
        mock_topic_repository.describe_topics.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await use_case.execute(batch, actor="test-user")

        # 실패 감사 로그 기록 확인
        calls = mock_audit_repository.log_topic_operation.call_args_list
        assert any("FAILED" in str(call) for call in calls)


class TestTopicBatchApplyUseCase:
    """TopicBatchApplyUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_apply_create_success(
        self,
        mock_topic_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """토픽 생성 적용"""
        use_case = TopicBatchApplyUseCase(
            mock_topic_repository,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch(
            specs=(create_topic_spec(name="dev.test1.topic"),),
        )

        # Repository: 토픽 생성
        mock_topic_repository.describe_topics.return_value = {}
        mock_topic_repository.create_topics.return_value = {
            "dev.test1.topic": None,
        }

        result = await use_case.execute(batch, actor="test-user")

        assert result.change_id == batch.change_id
        assert len(result.applied) == 1
        assert "dev.test1.topic" in result.applied

        # 결과 저장 확인
        mock_metadata_repository.save_apply_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_delete_success(
        self,
        mock_topic_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """토픽 삭제 적용"""
        use_case = TopicBatchApplyUseCase(
            mock_topic_repository,
            mock_metadata_repository,
            mock_audit_repository,
        )

        spec = create_topic_spec(
            name="dev.old.topic",
            action=DomainTopicAction.DELETE,
        )
        batch = create_topic_batch(specs=(spec,))

        # Repository: 토픽 삭제
        mock_topic_repository.describe_topics.return_value = {
            "dev.old.topic": {"partition_count": 3}
        }
        mock_topic_repository.delete_topics.return_value = {"dev.old.topic": None}

        result = await use_case.execute(batch, actor="test-user")

        assert len(result.applied) == 1
        assert "dev.old.topic" in result.applied

    @pytest.mark.asyncio
    async def test_apply_partial_failure(
        self,
        mock_topic_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """일부 실패한 적용"""
        use_case = TopicBatchApplyUseCase(
            mock_topic_repository,
            mock_metadata_repository,
            mock_audit_repository,
        )

        batch = create_topic_batch(
            specs=(
                create_topic_spec(name="dev.success.topic"),
                create_topic_spec(name="dev.failure.topic"),
            ),
        )

        # Repository: 토픽 생성
        mock_topic_repository.describe_topics.return_value = {}
        mock_topic_repository.create_topics.return_value = {
            "dev.success.topic": None,
            "dev.failure.topic": Exception("Creation failed"),
        }

        result = await use_case.execute(batch, actor="test-user")

        assert len(result.applied) == 1
        assert len(result.failed) == 1
        assert result.failed[0]["name"] == "dev.failure.topic"

    @pytest.mark.asyncio
    async def test_apply_with_policy_violation(
        self,
        mock_topic_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """정책 위반으로 적용 차단"""
        use_case = TopicBatchApplyUseCase(
            mock_topic_repository,
            mock_metadata_repository,
            mock_audit_repository,
        )

        # 잘못된 이름의 토픽 생성 시도 (정책 위반 - 예약어 사용)
        batch = create_topic_batch(
            specs=(create_topic_spec(name="dev.__consumer_offsets"),)  # 예약어 사용 (위반)
        )

        mock_topic_repository.describe_topics.return_value = {}

        # 정책 검증에서 위반 발생 (내부적으로 처리됨)
        with pytest.raises(ValueError, match="Cannot apply due to policy violations"):
            await use_case.execute(batch, actor="test-user")

    @pytest.mark.asyncio
    async def test_apply_partition_change(
        self,
        mock_topic_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """파티션 수 변경 적용"""
        use_case = TopicBatchApplyUseCase(
            mock_topic_repository,
            mock_metadata_repository,
            mock_audit_repository,
        )

        from tests.topic.factories import create_topic_config

        spec = create_topic_spec(
            name="dev.existing.topic",
            action=DomainTopicAction.UPDATE,
            config=create_topic_config(partitions=12, replication_factor=2),
        )
        batch = create_topic_batch(specs=(spec,))

        # 기존 토픽 (파티션 6개)
        mock_topic_repository.describe_topics.return_value = {
            "dev.existing.topic": {
                "partition_count": 6,
                "config": {"partitions": "6", "replication_factor": "2"},
            }
        }

        # 파티션 변경 성공
        mock_topic_repository.create_partitions.return_value = {"dev.existing.topic": None}
        mock_topic_repository.alter_topic_configs.return_value = {"dev.existing.topic": None}

        result = await use_case.execute(batch, actor="test-user")

        assert len(result.applied) == 1
        mock_topic_repository.create_partitions.assert_called_once()


class TestTopicDetailUseCase:
    """TopicDetailUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_get_topic_detail(
        self,
        mock_topic_repository,
        mock_metadata_repository,
    ):
        """토픽 상세 조회"""
        use_case = TopicDetailUseCase(
            mock_topic_repository,
            mock_metadata_repository,
        )

        # Kafka 정보
        mock_topic_repository.describe_topics.return_value = {
            "dev.test.topic": {
                "partition_count": 6,
                "config": {"retention.ms": "86400000"},
            }
        }

        # 메타데이터
        mock_metadata_repository.get_topic_metadata.return_value = {
            "owner": "team-test",
            "sla": "P99<200ms",
        }

        detail = await use_case.execute("dev.test.topic")

        assert detail is not None
        assert detail.name == "dev.test.topic"
        assert detail.kafka_metadata["partition_count"] == 6
        # metadata는 DomainTopicMetadata msgspec.Struct이므로 속성으로 접근
        assert detail.metadata.owner == "team-test"

    @pytest.mark.asyncio
    async def test_get_non_existing_topic(
        self,
        mock_topic_repository,
        mock_metadata_repository,
    ):
        """존재하지 않는 토픽"""
        use_case = TopicDetailUseCase(
            mock_topic_repository,
            mock_metadata_repository,
        )

        mock_topic_repository.describe_topics.return_value = {}

        detail = await use_case.execute("dev.nonexist.topic")

        assert detail is None


class TestTopicPlanUseCase:
    """TopicPlanUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_get_plan(self, mock_metadata_repository):
        """계획 조회"""
        use_case = TopicPlanUseCase(mock_metadata_repository)

        plan = create_topic_plan(change_id="test-001")
        mock_metadata_repository.get_plan.return_value = plan

        result = await use_case.execute("test-001")

        assert result is not None
        assert result.change_id == "test-001"

    @pytest.mark.asyncio
    async def test_get_non_existing_plan(self, mock_metadata_repository):
        """존재하지 않는 계획"""
        use_case = TopicPlanUseCase(mock_metadata_repository)

        mock_metadata_repository.get_plan.return_value = None

        result = await use_case.execute("nonexist-001")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_plan_meta(self, mock_metadata_repository):
        """계획 메타 정보 조회"""
        use_case = TopicPlanUseCase(mock_metadata_repository)

        meta = {
            "status": "applied",
            "created_at": "2025-09-30T10:00:00Z",
            "applied_at": "2025-09-30T10:05:00Z",
        }
        mock_metadata_repository.get_plan_meta.return_value = meta

        result = await use_case.get_meta("test-001")

        assert result is not None
        assert result["status"] == "applied"
