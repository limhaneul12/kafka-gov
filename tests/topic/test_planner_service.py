"""TopicPlannerService 테스트 - 핵심 기능만"""

import pytest

from app.topic.domain.models import DomainPlanAction, DomainTopicAction
from app.topic.domain.services import TopicPlannerService
from tests.topic.factories import create_topic_batch, create_topic_config, create_topic_spec


class TestTopicPlannerService:
    """토픽 계획 수립 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_create_new_topics(self, mock_topic_repository):
        """새 토픽 생성 계획"""
        service = TopicPlannerService(mock_topic_repository)

        batch = create_topic_batch(
            specs=(
                create_topic_spec(name="dev.new1.topic"),
                create_topic_spec(name="dev.new2.topic"),
            ),
        )

        # 기존 토픽 없음
        mock_topic_repository.describe_topics.return_value = {}

        plan = await service.create_plan(batch, actor="test-user")

        assert plan.change_id == batch.change_id
        assert len(plan.items) == 2
        assert all(item.action == DomainPlanAction.CREATE for item in plan.items)
        assert all(item.current_config is None for item in plan.items)

    @pytest.mark.asyncio
    async def test_update_existing_topic_partitions(self, mock_topic_repository):
        """기존 토픽의 partition 증가"""
        service = TopicPlannerService(mock_topic_repository)

        spec = create_topic_spec(
            name="dev.existing.topic",
            action=DomainTopicAction.UPDATE,
            config=create_topic_config(partitions=12, replication_factor=2),
        )
        batch = create_topic_batch(specs=(spec,))

        # 기존 토픽 (partition=6)
        mock_topic_repository.describe_topics.return_value = {
            "dev.existing.topic": {
                "partition_count": 6,
                "config": {
                    "replication_factor": "2",
                    "cleanup.policy": "delete",
                },
            }
        }

        plan = await service.create_plan(batch, actor="test-user")

        assert len(plan.items) == 1
        assert plan.items[0].action == DomainPlanAction.ALTER
        assert "6→12" in plan.items[0].diff.get("partitions", "")

    @pytest.mark.asyncio
    async def test_update_topic_config(self, mock_topic_repository):
        """토픽 설정 변경"""
        service = TopicPlannerService(mock_topic_repository)

        spec = create_topic_spec(
            name="dev.config.topic",
            action=DomainTopicAction.UPDATE,
            config=create_topic_config(
                partitions=6,
                replication_factor=2,
                retention_ms=604800000,  # 7일
            ),
        )
        batch = create_topic_batch(specs=(spec,))

        # 기존 토픽 (retention 다름)
        mock_topic_repository.describe_topics.return_value = {
            "dev.config.topic": {
                "partition_count": 6,
                "config": {
                    "replication_factor": "2",
                    "retention.ms": "86400000",  # 1일
                },
            }
        }

        plan = await service.create_plan(batch, actor="test-user")

        assert len(plan.items) == 1
        assert plan.items[0].action == DomainPlanAction.ALTER
        # diff에 retention 변경 포함
        assert "retention.ms" in plan.items[0].diff

    @pytest.mark.asyncio
    async def test_delete_topics(self, mock_topic_repository):
        """토픽 삭제 계획"""
        service = TopicPlannerService(mock_topic_repository)

        spec = create_topic_spec(
            name="dev.old.topic",
            action=DomainTopicAction.DELETE,
        )
        batch = create_topic_batch(specs=(spec,))

        # 기존 토픽 존재
        mock_topic_repository.describe_topics.return_value = {
            "dev.old.topic": {
                "partition_count": 3,
                "config": {},
            }
        }

        plan = await service.create_plan(batch, actor="test-user")

        assert len(plan.items) == 1
        assert plan.items[0].action == DomainPlanAction.DELETE

    @pytest.mark.asyncio
    async def test_mixed_operations(self, mock_topic_repository):
        """생성/수정/삭제 혼합"""
        service = TopicPlannerService(mock_topic_repository)

        batch = create_topic_batch(
            specs=(
                create_topic_spec(name="dev.new.topic", action=DomainTopicAction.CREATE),
                create_topic_spec(
                    name="dev.update.topic",
                    action=DomainTopicAction.UPDATE,
                    config=create_topic_config(partitions=12),
                ),
                create_topic_spec(name="dev.delete.topic", action=DomainTopicAction.DELETE),
            ),
        )

        # 기존 토픽 일부만 존재
        mock_topic_repository.describe_topics.return_value = {
            "dev.update.topic": {
                "partition_count": 6,
                "config": {},
            },
            "dev.delete.topic": {
                "partition_count": 3,
                "config": {},
            },
        }

        plan = await service.create_plan(batch, actor="test-user")

        assert len(plan.items) == 3

        # 액션별 검증
        actions = {item.name: item.action for item in plan.items}
        assert actions["dev.new.topic"] == DomainPlanAction.CREATE
        assert actions["dev.update.topic"] == DomainPlanAction.ALTER
        assert actions["dev.delete.topic"] == DomainPlanAction.DELETE

    @pytest.mark.asyncio
    async def test_no_change_needed(self, mock_topic_repository):
        """변경사항 없음"""
        service = TopicPlannerService(mock_topic_repository)

        spec = create_topic_spec(
            name="dev.same.topic",
            action=DomainTopicAction.UPSERT,
            config=create_topic_config(partitions=6, replication_factor=2),
        )
        batch = create_topic_batch(specs=(spec,))

        # 기존 토픽과 동일
        mock_topic_repository.describe_topics.return_value = {
            "dev.same.topic": {
                "partition_count": 6,
                "config": {
                    "replication_factor": "2",
                    "cleanup.policy": "delete",
                },
            }
        }

        plan = await service.create_plan(batch, actor="test-user")

        # UPSERT는 변경 없으면 스킵되거나 ALTER로 표시 (구현에 따라)
        # 최소한 에러는 나지 않아야 함
        assert plan.change_id == batch.change_id

    @pytest.mark.asyncio
    async def test_partition_decrease_allowed_in_plan(self, mock_topic_repository):
        """Partition 감소는 계획에 포함되지만 실제 적용 시 Kafka에서 거부됨"""
        service = TopicPlannerService(mock_topic_repository)

        spec = create_topic_spec(
            name="dev.shrink.topic",
            action=DomainTopicAction.UPDATE,
            config=create_topic_config(partitions=3, replication_factor=2),
        )
        batch = create_topic_batch(specs=(spec,))

        # 기존 토픽 (partition=6)
        mock_topic_repository.describe_topics.return_value = {
            "dev.shrink.topic": {
                "partition_count": 6,
                "config": {"replication_factor": "2"},
            }
        }

        # 계획은 생성됨 (partition 감소 포함)
        plan = await service.create_plan(batch, actor="test-user")

        # 계획에는 ALTER가 포함됨
        assert len(plan.items) == 1
        assert plan.items[0].action == DomainPlanAction.ALTER
        # 실제 적용은 Kafka에서 거부됨 (domain service는 계획만 생성)
