"""Domain Models 핵심 테스트"""

import pytest

from app.topic.domain.models import DomainCleanupPolicy, DomainTopicAction
from tests.topic.factories import create_topic_batch, create_topic_config, create_topic_spec


class TestDomainTopicConfig:
    """DomainTopicConfig 핵심 검증"""

    def test_valid_config(self):
        """정상 설정"""
        config = create_topic_config(
            partitions=12,
            replication_factor=3,
            cleanup_policy=DomainCleanupPolicy.COMPACT,
        )

        assert config.partitions == 12
        assert config.replication_factor == 3

    def test_validation(self):
        """입력값 검증"""
        with pytest.raises(ValueError):
            create_topic_config(partitions=0)

        with pytest.raises(ValueError):
            create_topic_config(replication_factor=0)

    def test_kafka_config_conversion(self):
        """Kafka 설정 변환"""
        config = create_topic_config(retention_ms=86400000)
        kafka_config = config.to_kafka_config()

        assert kafka_config["retention.ms"] == "86400000"


class TestDomainTopicSpec:
    """DomainTopicSpec 핵심 검증"""

    def test_valid_spec(self):
        """정상 명세"""
        spec = create_topic_spec(
            name="prod.orders.created",
            action=DomainTopicAction.CREATE,
        )

        assert spec.name == "prod.orders.created"
        assert spec.action == DomainTopicAction.CREATE
        assert spec.config is not None


class TestDomainTopicBatch:
    """DomainTopicBatch 핵심 검증"""

    def test_valid_batch(self):
        """정상 배치"""
        batch = create_topic_batch(
            specs=(
                create_topic_spec(name="dev.test1.topic"),
                create_topic_spec(name="dev.test2.topic"),
            ),
        )

        assert len(batch.specs) == 2
        assert batch.change_id is not None
