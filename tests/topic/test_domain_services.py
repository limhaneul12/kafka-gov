"""Domain Services 테스트"""

from __future__ import annotations

import pytest

from app.topic.domain.models import (
    DomainPlanAction,
    DomainTopicAction,
)
from app.topic.domain.services import TopicDiffService, TopicPlannerService
from tests.topic.factories import (
    create_topic_batch,
    create_topic_config,
    create_topic_spec,
)


class TestTopicPlannerService:
    """TopicPlannerService 테스트"""

    @pytest.mark.asyncio
    async def test_create_plan_for_new_topics(
        self,
        mock_topic_repository,
        mock_policy_adapter,
    ):
        """새 토픽 생성 계획"""
        service = TopicPlannerService(mock_topic_repository, mock_policy_adapter)

        # 새 토픽들
        batch = create_topic_batch(
            specs=(
                create_topic_spec(name="dev.new1.topic"),
                create_topic_spec(name="dev.new2.topic"),
            ),
        )

        # Repository: 토픽이 존재하지 않음
        mock_topic_repository.describe_topics.return_value = {}

        # Policy: 위반 없음
        mock_policy_adapter.validate_topic_specs.return_value = []

        plan = await service.create_plan(batch, actor="test-user")

        assert plan.change_id == batch.change_id
        assert plan.env == batch.env
        assert len(plan.items) == 2
        assert all(item.action == DomainPlanAction.CREATE for item in plan.items)
        assert len(plan.violations) == 0

    @pytest.mark.asyncio
    async def test_create_plan_for_existing_topics(
        self,
        mock_topic_repository,
        mock_policy_adapter,
    ):
        """기존 토픽 수정 계획"""
        service = TopicPlannerService(mock_topic_repository, mock_policy_adapter)

        spec = create_topic_spec(
            name="dev.existing.topic",
            action=DomainTopicAction.UPDATE,
            config=create_topic_config(
                partitions=12,  # 증가
                replication_factor=2,
            ),
        )
        batch = create_topic_batch(specs=(spec,))

        # Repository: 기존 토픽 정보
        mock_topic_repository.describe_topics.return_value = {
            "dev.existing.topic": {
                "partition_count": 6,
                "config": {
                    "partitions": "6",
                    "replication_factor": "2",
                    "cleanup.policy": "delete",
                    "compression.type": "zstd",
                },
            }
        }

        mock_policy_adapter.validate_topic_specs.return_value = []

        plan = await service.create_plan(batch, actor="test-user")

        assert len(plan.items) == 1
        assert plan.items[0].action == DomainPlanAction.ALTER
        assert "partitions" in plan.items[0].diff

    @pytest.mark.asyncio
    async def test_create_plan_for_delete(
        self,
        mock_topic_repository,
        mock_policy_adapter,
    ):
        """토픽 삭제 계획"""
        service = TopicPlannerService(mock_topic_repository, mock_policy_adapter)

        spec = create_topic_spec(
            name="dev.old.topic",
            action=DomainTopicAction.DELETE,
            config=None,
            metadata=None,
            reason="Not needed anymore",
        )
        batch = create_topic_batch(specs=(spec,))

        # Repository: 토픽 존재
        mock_topic_repository.describe_topics.return_value = {
            "dev.old.topic": {
                "partition_count": 3,
                "config": {"partitions": "3", "replication_factor": "2"},
            }
        }

        mock_policy_adapter.validate_topic_specs.return_value = []

        plan = await service.create_plan(batch, actor="test-user")

        assert len(plan.items) == 1
        assert plan.items[0].action == DomainPlanAction.DELETE
        assert plan.items[0].name == "dev.old.topic"

    @pytest.mark.asyncio
    async def test_skip_delete_non_existing_topic(
        self,
        mock_topic_repository,
        mock_policy_adapter,
    ):
        """존재하지 않는 토픽 삭제는 스킵"""
        service = TopicPlannerService(mock_topic_repository, mock_policy_adapter)

        spec = create_topic_spec(
            name="dev.nonexist.topic",
            action=DomainTopicAction.DELETE,
            config=None,
            metadata=None,
            reason="Clean up",
        )
        batch = create_topic_batch(specs=(spec,))

        # Repository: 토픽 없음
        mock_topic_repository.describe_topics.return_value = {}

        mock_policy_adapter.validate_topic_specs.return_value = []

        plan = await service.create_plan(batch, actor="test-user")

        # 삭제할 토픽이 없으므로 아이템 없음
        assert len(plan.items) == 0

    @pytest.mark.asyncio
    async def test_skip_no_change_topics(
        self,
        mock_topic_repository,
        mock_policy_adapter,
    ):
        """변경 사항이 없는 토픽은 스킵"""
        service = TopicPlannerService(mock_topic_repository, mock_policy_adapter)

        spec = create_topic_spec(
            name="dev.unchanged.topic",
            action=DomainTopicAction.UPDATE,
            config=create_topic_config(
                partitions=6,
                replication_factor=2,
            ),
        )
        batch = create_topic_batch(specs=(spec,))

        # Repository: 동일한 설정
        mock_topic_repository.describe_topics.return_value = {
            "dev.unchanged.topic": {
                "partition_count": 6,
                "config": {
                    "partitions": "6",
                    "replication_factor": "2",
                    "cleanup.policy": "delete",
                    "compression.type": "zstd",
                },
            }
        }

        mock_policy_adapter.validate_topic_specs.return_value = []

        plan = await service.create_plan(batch, actor="test-user")

        # 변경 사항이 없으므로 아이템 없음
        assert len(plan.items) == 0

    @pytest.mark.asyncio
    async def test_plan_with_policy_violations(
        self,
        mock_topic_repository,
        mock_policy_adapter,
    ):
        """정책 위반이 있는 계획"""
        from app.policy.domain.models import (
            DomainPolicySeverity,
            DomainPolicyViolation,
            DomainResourceType,
        )

        service = TopicPlannerService(mock_topic_repository, mock_policy_adapter)

        batch = create_topic_batch(
            specs=(create_topic_spec(name="dev.test.topic"),),
        )

        mock_topic_repository.describe_topics.return_value = {}

        # Policy: 위반 발생
        violation = DomainPolicyViolation(
            resource_type=DomainResourceType.TOPIC,
            resource_name="dev.test.topic",
            rule_id="test.rule",
            message="Test violation",
            severity=DomainPolicySeverity.ERROR,
            field="name",
        )
        mock_policy_adapter.validate_topic_specs.return_value = [violation]

        plan = await service.create_plan(batch, actor="test-user")

        assert len(plan.violations) == 1
        assert plan.violations[0].message == "Test violation"


class TestTopicDiffService:
    """TopicDiffService 테스트"""

    def test_compare_configs_both_none(self):
        """둘 다 None인 경우"""
        diff = TopicDiffService.compare_configs(None, None)

        assert diff == {}

    def test_compare_configs_current_none(self):
        """현재 설정이 None (새 토픽)"""
        target = create_topic_config(partitions=6, replication_factor=2)

        diff = TopicDiffService.compare_configs(None, target)

        assert diff is not None
        assert diff["partitions"] == (None, 6)
        assert diff["replication_factor"] == (None, 2)

    def test_compare_configs_target_none(self):
        """대상 설정이 None (삭제)"""
        current = create_topic_config(partitions=6, replication_factor=2)

        diff = TopicDiffService.compare_configs(current, None)

        assert diff is not None
        assert diff["partitions"] == (6, None)
        assert diff["replication_factor"] == (2, None)

    def test_compare_configs_different(self):
        """다른 설정"""
        current = create_topic_config(
            partitions=6,
            replication_factor=2,
            retention_ms=86400000,
        )
        target = create_topic_config(
            partitions=12,
            replication_factor=2,
            retention_ms=604800000,
        )

        diff = TopicDiffService.compare_configs(current, target)

        assert diff is not None
        assert diff["partitions"] == (6, 12)
        assert "replication_factor" not in diff  # 동일
        assert diff["retention.ms"] == ("86400000", "604800000")

    def test_compare_configs_identical(self):
        """동일한 설정"""
        config = create_topic_config(partitions=6, replication_factor=2)

        diff = TopicDiffService.compare_configs(config, config)

        assert diff == {}

    def test_is_partition_increase_only(self):
        """파티션 증가 여부"""
        assert TopicDiffService.is_partition_increase_only(6, 12) is True
        assert TopicDiffService.is_partition_increase_only(6, 6) is True
        assert TopicDiffService.is_partition_increase_only(12, 6) is False

    def test_validate_config_changes_partition_decrease(self):
        """파티션 감소는 불가"""
        current = create_topic_config(partitions=12)
        target = create_topic_config(partitions=6)

        errors = TopicDiffService.validate_config_changes(current, target)

        assert len(errors) > 0
        assert any("Cannot decrease partitions" in e for e in errors)

    def test_validate_config_changes_replication_factor_change(self):
        """복제 팩터 변경은 불가"""
        current = create_topic_config(replication_factor=2)
        target = create_topic_config(replication_factor=3)

        errors = TopicDiffService.validate_config_changes(current, target)

        assert len(errors) > 0
        assert any("Cannot change replication factor" in e for e in errors)

    def test_validate_config_changes_valid(self):
        """정상적인 변경"""
        current = create_topic_config(
            partitions=6,
            replication_factor=2,
            retention_ms=86400000,
        )
        target = create_topic_config(
            partitions=12,  # 증가
            replication_factor=2,  # 동일
            retention_ms=604800000,  # 변경 가능
        )

        errors = TopicDiffService.validate_config_changes(current, target)

        assert len(errors) == 0

    def test_validate_config_changes_none_configs(self):
        """None 설정은 에러 없음"""
        errors1 = TopicDiffService.validate_config_changes(None, None)
        assert len(errors1) == 0

        config = create_topic_config()
        errors2 = TopicDiffService.validate_config_changes(None, config)
        assert len(errors2) == 0

        errors3 = TopicDiffService.validate_config_changes(config, None)
        assert len(errors3) == 0
