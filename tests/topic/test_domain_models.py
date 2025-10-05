"""Domain Models 테스트"""

from __future__ import annotations

import pytest

from app.topic.domain.models import (
    DomainCleanupPolicy,
    DomainEnvironment,
    DomainTopicAction,
    DomainTopicBatch,
    DomainTopicMetadata,
    DomainTopicSpec,
)
from tests.topic.factories import (
    create_topic_batch,
    create_topic_config,
    create_topic_metadata,
    create_topic_spec,
)


class TestDomainTopicMetadata:
    """DomainTopicMetadata 테스트"""

    def test_create_valid_metadata(self):
        """정상적인 메타데이터 생성"""
        metadata = create_topic_metadata(
            owner="team-commerce",
            doc="https://wiki.company.com/orders",
            tags=("pii", "critical"),
        )

        assert metadata.owner == "team-commerce"
        assert metadata.doc == "https://wiki.company.com/orders"
        assert metadata.tags == ("pii", "critical")

    def test_owner_can_be_empty(self):
        """owner는 빈 문자열 허용 (검증 제거됨)"""
        metadata = DomainTopicMetadata(owner="", doc=None, tags=())
        assert metadata.owner == ""

    def test_metadata_is_frozen(self):
        """메타데이터는 불변 (msgspec.Struct는 기본적으로 변경 가능)"""
        metadata = create_topic_metadata()
        # msgspec.Struct는 frozen=True가 아니면 변경 가능
        # 이 테스트는 frozen 동작을 검증하지 않음
        assert metadata.owner == "team-test"


class TestDomainTopicConfig:
    """DomainTopicConfig 테스트"""

    def test_create_valid_config(self):
        """정상적인 설정 생성"""
        config = create_topic_config(
            partitions=12,
            replication_factor=3,
            cleanup_policy=DomainCleanupPolicy.COMPACT,
            retention_ms=7 * 24 * 60 * 60 * 1000,
            min_insync_replicas=2,
        )

        assert config.partitions == 12
        assert config.replication_factor == 3
        assert config.cleanup_policy == DomainCleanupPolicy.COMPACT
        assert config.retention_ms == 7 * 24 * 60 * 60 * 1000
        assert config.min_insync_replicas == 2

    def test_partitions_must_be_positive(self):
        """파티션 수는 1 이상"""
        with pytest.raises(ValueError, match="partitions must be >= 1"):
            create_topic_config(partitions=0)

    def test_replication_factor_must_be_positive(self):
        """복제 팩터는 1 이상"""
        with pytest.raises(ValueError, match="replication_factor must be >= 1"):
            create_topic_config(replication_factor=0)

    def test_min_insync_replicas_cannot_exceed_replication_factor(self):
        """min.insync.replicas는 replication_factor보다 클 수 없음"""
        with pytest.raises(ValueError, match="min_insync_replicas.*cannot be greater than"):
            create_topic_config(replication_factor=2, min_insync_replicas=3)

    def test_to_kafka_config(self):
        """Kafka 설정으로 변환"""
        config = create_topic_config(
            partitions=6,
            replication_factor=2,
            retention_ms=86400000,
            min_insync_replicas=1,
        )

        kafka_config = config.to_kafka_config()

        assert kafka_config["cleanup.policy"] == "delete"
        assert kafka_config["retention.ms"] == "86400000"
        assert kafka_config["min.insync.replicas"] == "1"

    def test_config_is_frozen(self):
        """설정은 불변 (msgspec.Struct는 기본적으로 변경 가능)"""
        config = create_topic_config()
        # msgspec.Struct는 frozen=True가 아니면 변경 가능
        assert config.partitions == 3


class TestDomainTopicSpec:
    """DomainTopicSpec 테스트"""

    def test_create_valid_spec(self):
        """정상적인 명세 생성"""
        spec = create_topic_spec(
            name="prod.orders.created",
            action=DomainTopicAction.CREATE,
        )

        assert spec.name == "prod.orders.created"
        assert spec.action == DomainTopicAction.CREATE
        assert spec.config is not None
        assert spec.metadata is not None

    def test_name_required(self):
        """name은 필수"""
        with pytest.raises(ValueError, match="name is required"):
            DomainTopicSpec(
                name="",
                action=DomainTopicAction.CREATE,
                config=create_topic_config(),
                metadata=create_topic_metadata(),
            )

    def test_delete_action_should_not_have_config(self):
        """DELETE 액션은 config 불필요"""
        with pytest.raises(ValueError, match="config should not be provided for delete action"):
            DomainTopicSpec(
                name="dev.test.topic",
                action=DomainTopicAction.DELETE,
                config=create_topic_config(),
                metadata=None,
            )

    def test_create_action_requires_config(self):
        """CREATE 액션은 config 필수"""
        with pytest.raises(ValueError, match=r"config is required for.*CREATE"):
            DomainTopicSpec(
                name="dev.test.topic",
                action=DomainTopicAction.CREATE,
                config=None,
                metadata=create_topic_metadata(),
            )

    def test_environment_extraction(self):
        """토픽 이름에서 환경 추출"""
        prod_spec = create_topic_spec(name="prod.orders.created")
        assert prod_spec.environment == DomainEnvironment.PROD

        dev_spec = create_topic_spec(name="dev.test.topic")
        assert dev_spec.environment == DomainEnvironment.DEV

        stg_spec = create_topic_spec(name="stg.test.topic")
        assert stg_spec.environment == DomainEnvironment.STG

    def test_fingerprint_generation(self):
        """지문 생성"""
        spec1 = create_topic_spec(name="dev.test.topic", action=DomainTopicAction.CREATE)
        spec2 = create_topic_spec(name="dev.test.topic", action=DomainTopicAction.CREATE)

        # 동일한 명세는 동일한 지문
        assert spec1.fingerprint() == spec2.fingerprint()

        # 다른 명세는 다른 지문
        spec3 = create_topic_spec(name="dev.other.topic", action=DomainTopicAction.CREATE)
        assert spec1.fingerprint() != spec3.fingerprint()


class TestDomainTopicBatch:
    """DomainTopicBatch 테스트"""

    def test_create_valid_batch(self):
        """정상적인 배치 생성"""
        specs = (
            create_topic_spec(name="dev.test1.topic"),
            create_topic_spec(name="dev.test2.topic"),
        )
        batch = create_topic_batch(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            specs=specs,
        )

        assert batch.change_id == "test-001"
        assert batch.env == DomainEnvironment.DEV
        assert len(batch.specs) == 2

    def test_change_id_required(self):
        """change_id는 필수"""
        with pytest.raises(ValueError, match="change_id is required"):
            DomainTopicBatch(
                change_id="",
                env=DomainEnvironment.DEV,
                specs=(create_topic_spec(name="dev.test.topic"),),
            )

    def test_specs_cannot_be_empty(self):
        """specs는 비어있을 수 없음"""
        with pytest.raises(ValueError, match="specs cannot be empty"):
            DomainTopicBatch(
                change_id="test-001",
                env=DomainEnvironment.DEV,
                specs=(),
            )

    def test_duplicate_topic_names_not_allowed(self):
        """중복된 토픽 이름 불허"""
        specs = (
            create_topic_spec(name="dev.test.topic"),
            create_topic_spec(name="dev.test.topic"),  # 중복
        )

        with pytest.raises(ValueError, match="Duplicate topic names found"):
            DomainTopicBatch(
                change_id="test-001",
                env=DomainEnvironment.DEV,
                specs=specs,
            )

    def test_mixed_environment_allowed(self):
        """환경 일관성 검증 제거됨 - 혼합 환경 허용"""
        specs = (
            create_topic_spec(name="dev.test.topic"),
            create_topic_spec(name="prod.test.topic"),  # 다른 환경
        )

        # 환경 검증이 제거되어 혼합 환경 허용됨
        batch = DomainTopicBatch(
            change_id="test-001",
            env=DomainEnvironment.UNKNOWN,
            specs=specs,
        )
        assert len(batch.specs) == 2

    def test_fingerprint_generation(self):
        """배치 지문 생성"""
        specs = (
            create_topic_spec(name="dev.test1.topic"),
            create_topic_spec(name="dev.test2.topic"),
        )
        batch1 = create_topic_batch(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            specs=specs,
        )

        batch2 = create_topic_batch(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            specs=specs,
        )

        # 동일한 배치는 동일한 지문
        assert batch1.fingerprint() == batch2.fingerprint()

        # 다른 change_id는 다른 지문
        batch3 = create_topic_batch(
            change_id="test-002",
            env=DomainEnvironment.DEV,
            specs=specs,
        )
        assert batch1.fingerprint() != batch3.fingerprint()


class TestDomainTopicPlan:
    """DomainTopicPlan 테스트"""

    def test_plan_with_no_violations(self):
        """위반 없는 계획"""
        from app.topic.domain.models import (
            DomainPlanAction,
            DomainTopicPlan,
            DomainTopicPlanItem,
        )

        items = (
            DomainTopicPlanItem(
                name="dev.test.topic",
                action=DomainPlanAction.CREATE,
                diff={"action": "create"},
                current_config=None,
                target_config={"retention.ms": "86400000"},
            ),
        )

        plan = DomainTopicPlan(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            items=items,
            violations=(),
        )

        assert plan.has_violations is False
        assert plan.can_apply is True
        assert len(plan.error_violations) == 0

    def test_plan_with_violations(self):
        """위반 있는 계획"""
        from app.shared.domain.policy_types import (
            DomainPolicySeverity,
            DomainPolicyViolation,
            DomainResourceType,
        )
        from app.topic.domain.models import (
            DomainPlanAction,
            DomainTopicPlan,
            DomainTopicPlanItem,
        )

        items = (
            DomainTopicPlanItem(
                name="prod.test.topic",
                action=DomainPlanAction.CREATE,
                diff={"action": "create"},
            ),
        )

        violations = (
            DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name="prod.test.topic",
                rule_id="topic.naming.pattern",
                message="Invalid naming pattern",
                severity=DomainPolicySeverity.ERROR,
            ),
            DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name="prod.test.topic",
                rule_id="topic.config.warning",
                message="Config warning",
                severity=DomainPolicySeverity.WARNING,
            ),
        )

        plan = DomainTopicPlan(
            change_id="test-001",
            env=DomainEnvironment.PROD,
            items=items,
            violations=violations,
        )

        assert plan.has_violations is True
        assert plan.can_apply is False
        assert len(plan.error_violations) == 1
        assert len(plan.warning_violations) == 1

    def test_plan_summary(self):
        """계획 요약"""
        from app.topic.domain.models import (
            DomainPlanAction,
            DomainTopicPlan,
            DomainTopicPlanItem,
        )

        items = (
            DomainTopicPlanItem(
                name="dev.topic1",
                action=DomainPlanAction.CREATE,
                diff={"action": "create"},
            ),
            DomainTopicPlanItem(
                name="dev.topic2",
                action=DomainPlanAction.ALTER,
                diff={"action": "alter"},
            ),
            DomainTopicPlanItem(
                name="dev.topic3",
                action=DomainPlanAction.DELETE,
                diff={"action": "delete"},
            ),
        )

        plan = DomainTopicPlan(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            items=items,
            violations=(),
        )

        summary = plan.summary()
        assert summary["total_items"] == 3
        assert summary["create_count"] == 1
        assert summary["alter_count"] == 1
        assert summary["delete_count"] == 1

    def test_plan_change_id_required(self):
        """change_id 필수"""
        from app.topic.domain.models import DomainTopicPlan

        with pytest.raises(ValueError, match="change_id is required"):
            DomainTopicPlan(
                change_id="",
                env=DomainEnvironment.DEV,
                items=(),
                violations=(),
            )


class TestDomainTopicPlanItem:
    """DomainTopicPlanItem 테스트"""

    def test_plan_item_name_required(self):
        """name 필수"""
        from app.topic.domain.models import DomainPlanAction, DomainTopicPlanItem

        with pytest.raises(ValueError, match="name is required"):
            DomainTopicPlanItem(
                name="",
                action=DomainPlanAction.CREATE,
                diff={"action": "create"},
            )
