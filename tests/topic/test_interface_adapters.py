"""Topic Interface Adapters 테스트"""

from __future__ import annotations

import pytest

from app.topic.domain.models import (
    DomainCleanupPolicy,
    DomainTopicAction,
)
from app.topic.interface.adapters import (
    TopicTypeAdapters,
    kafka_metadata_to_core_metadata,
    kafka_metadata_to_interface_config,
    safe_convert_item_to_spec,
    safe_convert_plan_to_response,
    safe_convert_request_to_batch,
)
from app.topic.interface.schemas import (
    TopicBatchRequest,
    TopicConfig,
    TopicItem,
    TopicMetadata,
)
from app.topic.interface.types import TopicAction

from .factories import create_topic_plan


class TestTopicTypeAdapters:
    """TopicTypeAdapters 클래스 테스트"""

    def test_convert_item_to_spec_success(self) -> None:
        """TopicItem → DomainTopicSpec 변환 성공"""
        # Given
        item = TopicItem(
            name="dev.test.topic",
            action=TopicAction.CREATE,
            config=TopicConfig(
                partitions=3,
                replication_factor=2,
                cleanup_policy="delete",
                retention_ms=86400000,
            ),
            metadata=TopicMetadata(
                owner="team-test",
                doc="https://wiki.test.com/topics/test",
                tags=["test", "dev"],
            ),
        )

        # When
        spec = TopicTypeAdapters.convert_item_to_spec(item)

        # Then
        assert spec.name == "dev.test.topic"
        assert spec.action == DomainTopicAction.CREATE
        assert spec.config is not None
        assert spec.config.partitions == 3
        assert spec.config.replication_factor == 2
        assert spec.config.cleanup_policy == DomainCleanupPolicy.DELETE
        assert spec.config.retention_ms == 86400000
        assert spec.metadata is not None
        assert spec.metadata.owner == "team-test"
        assert spec.metadata.doc == "https://wiki.test.com/topics/test"
        assert spec.metadata.tags == ("test", "dev")

    def test_convert_item_to_spec_delete_action(self) -> None:
        """DELETE 액션 변환 (config/metadata 없음)"""
        # Given
        item = TopicItem(
            name="dev.test.topic",
            action=TopicAction.DELETE,
        )

        # When
        spec = TopicTypeAdapters.convert_item_to_spec(item)

        # Then
        assert spec.name == "dev.test.topic"
        assert spec.action == DomainTopicAction.DELETE
        assert spec.config is None
        assert spec.metadata is None

    def test_convert_item_to_spec_minimal_config(self) -> None:
        """최소 설정만 있는 TopicItem 변환"""
        # Given
        item = TopicItem(
            name="dev.test.topic",
            action=TopicAction.CREATE,
            config=TopicConfig(
                partitions=1,
                replication_factor=1,
            ),
            metadata=TopicMetadata(
                owner="team-test",
            ),
        )

        # When
        spec = TopicTypeAdapters.convert_item_to_spec(item)

        # Then
        assert spec.config is not None
        assert spec.config.partitions == 1
        assert spec.config.replication_factor == 1
        assert spec.config.cleanup_policy == DomainCleanupPolicy.DELETE  # 기본값
        assert spec.metadata is not None
        assert spec.metadata.owner == "team-test"
        assert spec.metadata.tags == ()

    def test_convert_request_to_batch_success(self) -> None:
        """TopicBatchRequest → DomainTopicBatch 변환 성공"""
        # Given
        request = TopicBatchRequest(
            change_id="test-001",
            env="dev",
            items=[
                TopicItem(
                    name="dev.topic1",
                    action=TopicAction.CREATE,
                    config=TopicConfig(partitions=3, replication_factor=2),
                    metadata=TopicMetadata(owner="team1"),
                ),
                TopicItem(
                    name="dev.topic2",
                    action=TopicAction.DELETE,
                ),
            ],
        )

        # When
        batch = TopicTypeAdapters.convert_request_to_batch(request)

        # Then
        assert batch.change_id == "test-001"
        assert batch.env.value == "dev"
        assert len(batch.specs) == 2
        assert batch.specs[0].name == "dev.topic1"
        assert batch.specs[0].action == DomainTopicAction.CREATE
        assert batch.specs[1].name == "dev.topic2"
        assert batch.specs[1].action == DomainTopicAction.DELETE

    def test_convert_plan_to_response_success(self) -> None:
        """DomainTopicPlan → TopicBatchDryRunResponse 변환 성공"""
        # Given
        plan = create_topic_plan(
            change_id="test-001",
        )
        request = TopicBatchRequest(
            change_id="test-001",
            env="dev",
            items=[
                TopicItem(
                    name="dev.test.topic",
                    action=TopicAction.CREATE,
                    config=TopicConfig(partitions=3, replication_factor=2),
                    metadata=TopicMetadata(owner="team-test"),
                ),
            ],
        )

        # When
        response = TopicTypeAdapters.convert_plan_to_response(plan, request)

        # Then
        assert response.change_id == "test-001"
        assert response.env == "dev"
        assert len(response.plan) == 1
        assert response.summary is not None


class TestGlobalFunctions:
    """전역 함수 테스트"""

    def test_safe_convert_item_to_spec(self) -> None:
        """safe_convert_item_to_spec 함수 테스트"""
        # Given
        item = TopicItem(
            name="dev.test.topic",
            action=TopicAction.CREATE,
            config=TopicConfig(partitions=3, replication_factor=2),
            metadata=TopicMetadata(owner="team-test"),
        )

        # When
        spec = safe_convert_item_to_spec(item)

        # Then
        assert spec.name == "dev.test.topic"
        assert spec.action == DomainTopicAction.CREATE

    def test_safe_convert_request_to_batch(self) -> None:
        """safe_convert_request_to_batch 함수 테스트"""
        # Given
        request = TopicBatchRequest(
            change_id="test-001",
            env="dev",
            items=[
                TopicItem(
                    name="dev.topic1",
                    action=TopicAction.CREATE,
                    config=TopicConfig(partitions=3, replication_factor=2),
                    metadata=TopicMetadata(owner="team1"),
                ),
            ],
        )

        # When
        batch = safe_convert_request_to_batch(request)

        # Then
        assert batch.change_id == "test-001"
        assert len(batch.specs) == 1

    def test_safe_convert_plan_to_response(self) -> None:
        """safe_convert_plan_to_response 함수 테스트"""
        # Given
        plan = create_topic_plan()
        request = TopicBatchRequest(
            change_id="test-001",
            env="dev",
            items=[
                TopicItem(
                    name="dev.test.topic",
                    action=TopicAction.CREATE,
                    config=TopicConfig(partitions=3, replication_factor=2),
                    metadata=TopicMetadata(owner="team-test"),
                ),
            ],
        )

        # When
        response = safe_convert_plan_to_response(plan, request)

        # Then
        assert response.change_id == "test-001"


class TestKafkaMetadataToInterfaceConfig:
    """kafka_metadata_to_interface_config 함수 테스트"""

    def test_basic_conversion(self) -> None:
        """기본 메타데이터 변환"""
        # Given
        kafka_metadata = {
            "partition_count": 3,
            "replication_factor": 2,
            "config": {
                "cleanup.policy": "delete",
                "retention.ms": "86400000",
            },
        }

        # When
        config = kafka_metadata_to_interface_config(kafka_metadata)

        # Then
        assert config is not None
        assert config.partitions == 3
        assert config.replication_factor == 2
        assert config.cleanup_policy == "delete"
        assert config.retention_ms == 86400000

    def test_conversion_with_all_fields(self) -> None:
        """모든 필드가 있는 메타데이터 변환"""
        # Given
        kafka_metadata = {
            "partition_count": 5,
            "replication_factor": 3,
            "config": {
                "cleanup.policy": "compact",
                "retention.ms": "604800000",
                "min.insync.replicas": "2",
                "max.message.bytes": "1048576",
                "segment.ms": "3600000",
            },
        }

        # When
        config = kafka_metadata_to_interface_config(kafka_metadata)

        # Then
        assert config is not None
        assert config.partitions == 5
        assert config.replication_factor == 3
        assert config.cleanup_policy == "compact"
        assert config.retention_ms == 604800000
        assert config.min_insync_replicas == 2
        assert config.max_message_bytes == 1048576
        assert config.segment_ms == 3600000

    def test_conversion_with_missing_partitions(self) -> None:
        """partition_count가 없는 경우"""
        # Given
        kafka_metadata = {
            "replication_factor": 2,
            "config": {},
        }

        # When
        config = kafka_metadata_to_interface_config(kafka_metadata)

        # Then
        assert config is None

    def test_conversion_with_missing_replication_factor(self) -> None:
        """replication_factor가 없지만 replicas로 추론 가능"""
        # Given
        kafka_metadata = {
            "partition_count": 3,
            "leader_replicas": [0, 1, 2],
            "config": {},
        }

        # When
        config = kafka_metadata_to_interface_config(kafka_metadata)

        # Then
        assert config is not None
        assert config.partitions == 3
        assert config.replication_factor == 3

    def test_conversion_with_num_partitions_in_config(self) -> None:
        """partition_count 대신 config.num.partitions 사용"""
        # Given
        kafka_metadata = {
            "replication_factor": 2,
            "config": {
                "num.partitions": "4",
            },
        }

        # When
        config = kafka_metadata_to_interface_config(kafka_metadata)

        # Then
        assert config is not None
        assert config.partitions == 4
        assert config.replication_factor == 2

    def test_conversion_with_invalid_data(self) -> None:
        """잘못된 데이터 타입"""
        # Given
        kafka_metadata = {
            "partition_count": "invalid",
            "replication_factor": 2,
            "config": {},
        }

        # When
        config = kafka_metadata_to_interface_config(kafka_metadata)

        # Then
        assert config is None


class TestKafkaMetadataToCoreMetadata:
    """kafka_metadata_to_core_metadata 함수 테스트 (실제 반환 타입에 맞춤)"""

    def test_conversion_with_missing_partitions(self) -> None:
        """partition_count가 없는 경우"""
        # Given
        kafka_metadata = {
            "leader_replicas": [0, 1, 2],
            "created_at": "2024-01-01",
        }

        # When
        core_metadata = kafka_metadata_to_core_metadata(kafka_metadata)

        # Then
        assert core_metadata is None
