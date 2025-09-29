"""Topic 도메인 레이어 테스트."""

from __future__ import annotations

import pytest

from app.policy.domain.models import (
    DomainPolicySeverity as PolicySeverity,
    DomainPolicyViolation as PolicyViolation,
    DomainResourceType as ResourceType,
)
from app.topic.domain.models import (
    DomainCleanupPolicy as CleanupPolicy,
    DomainCompressionType as CompressionType,
    DomainEnvironment as Environment,
    DomainPlanAction as PlanAction,
    DomainTopicAction as TopicAction,
    DomainTopicApplyResult as TopicApplyResult,
    DomainTopicBatch as TopicBatch,
    DomainTopicConfig as TopicConfig,
    DomainTopicMetadata as TopicMetadata,
    DomainTopicPlan as TopicPlan,
    DomainTopicPlanItem as TopicPlanItem,
    DomainTopicSpec as TopicSpec,
)


class TestTopicMetadata:
    """TopicMetadata 값 객체 테스트."""

    def test_should_create_metadata_with_required_fields(self) -> None:
        """필수 필드로 메타데이터를 생성해야 한다."""
        # Arrange & Act
        metadata = TopicMetadata(owner="data-team")

        # Assert
        assert metadata.owner == "data-team"
        assert metadata.sla is None
        assert metadata.doc is None
        assert metadata.tags == ()

    def test_should_create_metadata_with_all_fields(self) -> None:
        """모든 필드로 메타데이터를 생성해야 한다."""
        # Arrange & Act
        metadata = TopicMetadata(
            owner="data-team",
            sla="99.9%",
            doc="https://docs.example.com/topic",
            tags=("critical", "real-time"),
        )

        # Assert
        assert metadata.owner == "data-team"
        assert metadata.sla == "99.9%"
        assert metadata.doc == "https://docs.example.com/topic"
        assert metadata.tags == ("critical", "real-time")

    def test_should_raise_error_when_owner_is_empty(self) -> None:
        """owner가 비어있으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="owner is required"):
            TopicMetadata(owner="")

    def test_should_be_immutable(self) -> None:
        """불변 객체여야 한다."""
        # Arrange
        metadata = TopicMetadata(owner="data-team")

        # Act & Assert
        with pytest.raises(AttributeError):
            metadata.owner = "new-team"  # type: ignore


class TestTopicConfig:
    """TopicConfig 값 객체 테스트."""

    def test_should_create_config_with_required_fields(self) -> None:
        """필수 필드로 설정을 생성해야 한다."""
        # Arrange & Act
        config = TopicConfig(partitions=3, replication_factor=2)

        # Assert
        assert config.partitions == 3
        assert config.replication_factor == 2
        assert config.cleanup_policy == CleanupPolicy.DELETE
        assert config.compression_type == CompressionType.ZSTD

    def test_should_create_config_with_all_fields(self) -> None:
        """모든 필드로 설정을 생성해야 한다."""
        # Arrange & Act
        config = TopicConfig(
            partitions=6,
            replication_factor=3,
            cleanup_policy=CleanupPolicy.COMPACT,
            compression_type=CompressionType.LZ4,
            retention_ms=86400000,
            min_insync_replicas=2,
            max_message_bytes=1048576,
            segment_ms=604800000,
        )

        # Assert
        assert config.partitions == 6
        assert config.replication_factor == 3
        assert config.cleanup_policy == CleanupPolicy.COMPACT
        assert config.compression_type == CompressionType.LZ4
        assert config.retention_ms == 86400000
        assert config.min_insync_replicas == 2
        assert config.max_message_bytes == 1048576
        assert config.segment_ms == 604800000

    def test_should_raise_error_when_partitions_invalid(self) -> None:
        """파티션 수가 유효하지 않으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="partitions must be >= 1"):
            TopicConfig(partitions=0, replication_factor=2)

    def test_should_raise_error_when_replication_factor_invalid(self) -> None:
        """복제 팩터가 유효하지 않으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="replication_factor must be >= 1"):
            TopicConfig(partitions=3, replication_factor=0)

    def test_should_convert_to_kafka_config(self) -> None:
        """Kafka 설정 딕셔너리로 변환해야 한다."""
        # Arrange
        config = TopicConfig(
            partitions=3,
            replication_factor=2,
            cleanup_policy=CleanupPolicy.COMPACT,
            compression_type=CompressionType.LZ4,
            retention_ms=86400000,
            min_insync_replicas=2,
        )

        # Act
        kafka_config = config.to_kafka_config()

        # Assert
        expected = {
            "cleanup.policy": "compact",
            "compression.type": "lz4",
            "retention.ms": "86400000",
            "min.insync.replicas": "2",
        }
        assert kafka_config == expected

    def test_should_convert_to_kafka_config_with_minimal_fields(self) -> None:
        """최소 필드만으로 Kafka 설정을 변환해야 한다."""
        # Arrange
        config = TopicConfig(partitions=3, replication_factor=2)

        # Act
        kafka_config = config.to_kafka_config()

        # Assert
        expected = {
            "cleanup.policy": "delete",
            "compression.type": "zstd",
        }
        assert kafka_config == expected


class TestTopicSpec:
    """TopicSpec 엔티티 테스트."""

    @pytest.fixture
    def sample_config(self) -> TopicConfig:
        """샘플 토픽 설정."""
        return TopicConfig(partitions=3, replication_factor=2)

    @pytest.fixture
    def sample_metadata(self) -> TopicMetadata:
        """샘플 토픽 메타데이터."""
        return TopicMetadata(owner="data-team")

    def test_should_create_spec_for_create_action(
        self, sample_config: TopicConfig, sample_metadata: TopicMetadata
    ) -> None:
        """CREATE 액션으로 명세를 생성해야 한다."""
        # Arrange & Act
        spec = TopicSpec(
            name="dev.user.events",
            action=TopicAction.CREATE,
            config=sample_config,
            metadata=sample_metadata,
        )

        # Assert
        assert spec.name == "dev.user.events"
        assert spec.action == TopicAction.CREATE
        assert spec.config == sample_config
        assert spec.metadata == sample_metadata
        assert spec.reason is None

    def test_should_create_spec_for_delete_action(self) -> None:
        """DELETE 액션으로 명세를 생성해야 한다."""
        # Arrange & Act
        spec = TopicSpec(
            name="dev.deprecated.topic",
            action=TopicAction.DELETE,
            reason="더 이상 사용하지 않음",
        )

        # Assert
        assert spec.name == "dev.deprecated.topic"
        assert spec.action == TopicAction.DELETE
        assert spec.config is None
        assert spec.metadata is None
        assert spec.reason == "더 이상 사용하지 않음"

    def test_should_raise_error_when_name_is_empty(self) -> None:
        """이름이 비어있으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="name is required"):
            TopicSpec(name="", action=TopicAction.CREATE)

    def test_should_raise_error_when_delete_without_reason(self) -> None:
        """DELETE 액션에서 reason이 없으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="reason is required for delete action"):
            TopicSpec(name="dev.test.topic", action=TopicAction.DELETE)

    def test_should_raise_error_when_delete_with_config(self, sample_config: TopicConfig) -> None:
        """DELETE 액션에서 config가 제공되면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="config should not be provided for delete action"):
            TopicSpec(
                name="dev.test.topic",
                action=TopicAction.DELETE,
                config=sample_config,
                reason="삭제",
            )

    def test_should_raise_error_when_create_without_config(
        self, sample_metadata: TopicMetadata
    ) -> None:
        """CREATE 액션에서 config가 없으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(
            ValueError,
            match=r"config is required for (DomainTopicAction\.|TopicAction\.)?CREATE action",
        ):
            TopicSpec(
                name="dev.test.topic",
                action=TopicAction.CREATE,
                metadata=sample_metadata,
            )

    def test_should_raise_error_when_create_without_metadata(
        self, sample_config: TopicConfig
    ) -> None:
        """CREATE 액션에서 metadata가 없으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(
            ValueError,
            match=r"metadata is required for (DomainTopicAction\.|TopicAction\.)?CREATE action",
        ):
            TopicSpec(
                name="dev.test.topic",
                action=TopicAction.CREATE,
                config=sample_config,
            )

    def test_should_extract_environment_from_name(
        self, sample_config: TopicConfig, sample_metadata: TopicMetadata
    ) -> None:
        """토픽 이름에서 환경을 추출해야 한다."""
        # Arrange
        spec = TopicSpec(
            name="prod.user.events",
            action=TopicAction.CREATE,
            config=sample_config,
            metadata=sample_metadata,
        )

        # Act & Assert
        assert spec.environment == Environment.PROD

    def test_should_generate_fingerprint(
        self, sample_config: TopicConfig, sample_metadata: TopicMetadata
    ) -> None:
        """명세 지문을 생성해야 한다."""
        # Arrange
        spec = TopicSpec(
            name="dev.user.events",
            action=TopicAction.CREATE,
            config=sample_config,
            metadata=sample_metadata,
        )

        # Act
        fingerprint = spec.fingerprint()

        # Assert
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 16

    def test_should_generate_same_fingerprint_for_same_spec(
        self, sample_config: TopicConfig, sample_metadata: TopicMetadata
    ) -> None:
        """동일한 명세는 동일한 지문을 생성해야 한다."""
        # Arrange
        spec1 = TopicSpec(
            name="dev.user.events",
            action=TopicAction.CREATE,
            config=sample_config,
            metadata=sample_metadata,
        )
        spec2 = TopicSpec(
            name="dev.user.events",
            action=TopicAction.CREATE,
            config=sample_config,
            metadata=sample_metadata,
        )

        # Act & Assert
        assert spec1.fingerprint() == spec2.fingerprint()


class TestTopicBatch:
    """TopicBatch 엔티티 테스트."""

    @pytest.fixture
    def sample_specs(self) -> tuple[TopicSpec, ...]:
        """샘플 토픽 명세들."""
        config = TopicConfig(partitions=3, replication_factor=2)
        metadata = TopicMetadata(owner="data-team")

        return (
            TopicSpec(
                name="dev.user.events",
                action=TopicAction.CREATE,
                config=config,
                metadata=metadata,
            ),
            TopicSpec(
                name="dev.order.events",
                action=TopicAction.UPSERT,
                config=config,
                metadata=metadata,
            ),
        )

    def test_should_create_batch_with_valid_specs(
        self, sample_specs: tuple[TopicSpec, ...]
    ) -> None:
        """유효한 명세들로 배치를 생성해야 한다."""
        # Arrange & Act
        batch = TopicBatch(
            change_id="change-123",
            env=Environment.DEV,
            specs=sample_specs,
        )

        # Assert
        assert batch.change_id == "change-123"
        assert batch.env == Environment.DEV
        assert batch.specs == sample_specs

    def test_should_raise_error_when_change_id_is_empty(
        self, sample_specs: tuple[TopicSpec, ...]
    ) -> None:
        """change_id가 비어있으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="change_id is required"):
            TopicBatch(change_id="", env=Environment.DEV, specs=sample_specs)

    def test_should_raise_error_when_specs_is_empty(self) -> None:
        """specs가 비어있으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="specs cannot be empty"):
            TopicBatch(change_id="change-123", env=Environment.DEV, specs=())

    def test_should_raise_error_when_duplicate_topic_names(self) -> None:
        """중복된 토픽 이름이 있으면 에러를 발생시켜야 한다."""
        # Arrange
        config = TopicConfig(partitions=3, replication_factor=2)
        metadata = TopicMetadata(owner="data-team")

        specs = (
            TopicSpec(
                name="dev.user.events",
                action=TopicAction.CREATE,
                config=config,
                metadata=metadata,
            ),
            TopicSpec(
                name="dev.user.events",  # 중복
                action=TopicAction.UPDATE,
                config=config,
                metadata=metadata,
            ),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Duplicate topic names found"):
            TopicBatch(change_id="change-123", env=Environment.DEV, specs=specs)

    def test_should_raise_error_when_environment_mismatch(self) -> None:
        """환경이 일치하지 않으면 에러를 발생시켜야 한다."""
        # Arrange
        config = TopicConfig(partitions=3, replication_factor=2)
        metadata = TopicMetadata(owner="data-team")

        specs = (
            TopicSpec(
                name="prod.user.events",  # PROD 환경
                action=TopicAction.CREATE,
                config=config,
                metadata=metadata,
            ),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="does not match batch environment"):
            TopicBatch(change_id="change-123", env=Environment.DEV, specs=specs)

    def test_should_generate_fingerprint(self, sample_specs: tuple[TopicSpec, ...]) -> None:
        """배치 지문을 생성해야 한다."""
        # Arrange
        batch = TopicBatch(
            change_id="change-123",
            env=Environment.DEV,
            specs=sample_specs,
        )

        # Act
        fingerprint = batch.fingerprint()

        # Assert
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 16


class TestTopicPlanItem:
    """TopicPlanItem 값 객체 테스트."""

    def test_should_create_plan_item(self) -> None:
        """계획 아이템을 생성해야 한다."""
        # Arrange & Act
        item = TopicPlanItem(
            name="dev.user.events",
            action=PlanAction.CREATE,
            diff={"partitions": "3", "replication.factor": "2"},
            target_config={"partitions": "3", "replication.factor": "2"},
        )

        # Assert
        assert item.name == "dev.user.events"
        assert item.action == PlanAction.CREATE
        assert item.diff == {"partitions": "3", "replication.factor": "2"}
        assert item.current_config is None
        assert item.target_config == {"partitions": "3", "replication.factor": "2"}

    def test_should_raise_error_when_name_is_empty(self) -> None:
        """이름이 비어있으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="name is required"):
            TopicPlanItem(name="", action=PlanAction.CREATE, diff={})


class TestTopicPlan:
    """TopicPlan 엔티티 테스트."""

    @pytest.fixture
    def sample_items(self) -> tuple[TopicPlanItem, ...]:
        """샘플 계획 아이템들."""
        return (
            TopicPlanItem(
                name="dev.user.events",
                action=PlanAction.CREATE,
                diff={"partitions": "3"},
            ),
            TopicPlanItem(
                name="dev.order.events",
                action=PlanAction.ALTER,
                diff={"retention.ms": "86400000"},
            ),
        )

    @pytest.fixture
    def sample_violations(self) -> tuple[PolicyViolation, ...]:
        """샘플 정책 위반들."""
        return (
            PolicyViolation(
                resource_type=ResourceType.TOPIC,
                resource_name="dev.user.events",
                rule_id="naming_rule",
                message="토픽 이름이 권장 패턴과 다릅니다",
                severity=PolicySeverity.WARNING,
            ),
            PolicyViolation(
                resource_type=ResourceType.TOPIC,
                resource_name="dev.order.events",
                rule_id="partition_rule",
                message="파티션 수가 너무 적습니다",
                severity=PolicySeverity.ERROR,
            ),
        )

    def test_should_create_plan_without_violations(
        self, sample_items: tuple[TopicPlanItem, ...]
    ) -> None:
        """위반 없이 계획을 생성해야 한다."""
        # Arrange & Act
        plan = TopicPlan(
            change_id="change-123",
            env=Environment.DEV,
            items=sample_items,
            violations=(),
        )

        # Assert
        assert plan.change_id == "change-123"
        assert plan.env == Environment.DEV
        assert plan.items == sample_items
        assert plan.violations == ()

    def test_should_create_plan_with_violations(
        self,
        sample_items: tuple[TopicPlanItem, ...],
        sample_violations: tuple[PolicyViolation, ...],
    ) -> None:
        """위반과 함께 계획을 생성해야 한다."""
        # Arrange & Act
        plan = TopicPlan(
            change_id="change-123",
            env=Environment.DEV,
            items=sample_items,
            violations=sample_violations,
        )

        # Assert
        assert plan.change_id == "change-123"
        assert plan.env == Environment.DEV
        assert plan.items == sample_items
        assert plan.violations == sample_violations

    def test_should_raise_error_when_change_id_is_empty(
        self, sample_items: tuple[TopicPlanItem, ...]
    ) -> None:
        """change_id가 비어있으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="change_id is required"):
            TopicPlan(change_id="", env=Environment.DEV, items=sample_items, violations=())

    def test_should_detect_violations(
        self,
        sample_items: tuple[TopicPlanItem, ...],
        sample_violations: tuple[PolicyViolation, ...],
    ) -> None:
        """위반 사항을 감지해야 한다."""
        # Arrange
        plan = TopicPlan(
            change_id="change-123",
            env=Environment.DEV,
            items=sample_items,
            violations=sample_violations,
        )

        # Act & Assert
        assert plan.has_violations is True

    def test_should_categorize_violations_by_severity(
        self,
        sample_items: tuple[TopicPlanItem, ...],
        sample_violations: tuple[PolicyViolation, ...],
    ) -> None:
        """심각도별로 위반을 분류해야 한다."""
        # Arrange
        plan = TopicPlan(
            change_id="change-123",
            env=Environment.DEV,
            items=sample_items,
            violations=sample_violations,
        )

        # Act & Assert
        assert len(plan.error_violations) == 1
        assert plan.error_violations[0].severity == PolicySeverity.ERROR
        assert len(plan.warning_violations) == 1
        assert plan.warning_violations[0].severity == PolicySeverity.WARNING

    def test_should_determine_apply_eligibility(
        self, sample_items: tuple[TopicPlanItem, ...]
    ) -> None:
        """적용 가능 여부를 판단해야 한다."""
        # Arrange - 경고만 있는 경우
        warning_violation = PolicyViolation(
            resource_type=ResourceType.TOPIC,
            resource_name="dev.user.events",
            rule_id="naming_rule",
            message="경고 메시지",
            severity=PolicySeverity.WARNING,
        )
        plan_with_warning = TopicPlan(
            change_id="change-123",
            env=Environment.DEV,
            items=sample_items,
            violations=(warning_violation,),
        )

        # 에러가 있는 경우
        error_violation = PolicyViolation(
            resource_type=ResourceType.TOPIC,
            resource_name="dev.user.events",
            rule_id="partition_rule",
            message="에러 메시지",
            severity=PolicySeverity.ERROR,
        )
        plan_with_error = TopicPlan(
            change_id="change-456",
            env=Environment.DEV,
            items=sample_items,
            violations=(error_violation,),
        )

        # Act & Assert
        assert plan_with_warning.can_apply is True
        assert plan_with_error.can_apply is False

    def test_should_generate_summary(self, sample_items: tuple[TopicPlanItem, ...]) -> None:
        """계획 요약을 생성해야 한다."""
        # Arrange
        plan = TopicPlan(
            change_id="change-123",
            env=Environment.DEV,
            items=sample_items,
            violations=(),
        )

        # Act
        summary = plan.summary()

        # Assert
        expected = {
            "total_items": 2,
            "create_count": 1,
            "alter_count": 1,
            "delete_count": 0,
            "violation_count": 0,
        }
        assert summary == expected


class TestTopicApplyResult:
    """TopicApplyResult 엔티티 테스트."""

    def test_should_create_apply_result(self) -> None:
        """적용 결과를 생성해야 한다."""
        # Arrange & Act
        result = TopicApplyResult(
            change_id="change-123",
            env=Environment.DEV,
            applied=("dev.user.events", "dev.order.events"),
            skipped=("dev.deprecated.topic",),
            failed=({"topic": "dev.invalid.topic", "error": "Invalid configuration"},),
            audit_id="audit-456",
        )

        # Assert
        assert result.change_id == "change-123"
        assert result.env == Environment.DEV
        assert result.applied == ("dev.user.events", "dev.order.events")
        assert result.skipped == ("dev.deprecated.topic",)
        assert len(result.failed) == 1
        assert result.audit_id == "audit-456"

    def test_should_raise_error_when_change_id_is_empty(self) -> None:
        """change_id가 비어있으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="change_id is required"):
            TopicApplyResult(
                change_id="",
                env=Environment.DEV,
                applied=(),
                skipped=(),
                failed=(),
                audit_id="audit-456",
            )

    def test_should_raise_error_when_audit_id_is_empty(self) -> None:
        """audit_id가 비어있으면 에러를 발생시켜야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="audit_id is required"):
            TopicApplyResult(
                change_id="change-123",
                env=Environment.DEV,
                applied=(),
                skipped=(),
                failed=(),
                audit_id="",
            )

    def test_should_generate_summary(self) -> None:
        """적용 결과 요약을 생성해야 한다."""
        # Arrange
        result = TopicApplyResult(
            change_id="change-123",
            env=Environment.DEV,
            applied=("dev.user.events", "dev.order.events"),
            skipped=("dev.deprecated.topic",),
            failed=({"topic": "dev.invalid.topic", "error": "Invalid configuration"},),
            audit_id="audit-456",
        )

        # Act
        summary = result.summary()

        # Assert
        expected = {
            "total_items": 4,
            "applied_count": 2,
            "skipped_count": 1,
            "failed_count": 1,
        }
        assert summary == expected
