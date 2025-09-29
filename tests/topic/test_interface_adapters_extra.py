"""Topic 인터페이스 어댑터 추가 테스트 (커버리지 보강)"""

from __future__ import annotations

from app.topic.interface.adapters import (
    kafka_metadata_to_core_metadata,
    kafka_metadata_to_interface_config,
    safe_convert_item_to_spec,
)
from app.topic.interface.schema import TopicItem


def test_kafka_metadata_to_interface_config_with_replicas_fallback() -> None:
    """replication_factor가 없을 때 leader_replicas 길이로 유도해야 한다."""
    kafka_metadata = {
        "partition_count": 3,
        "leader_replicas": [1, 2, 3],
        "config": {
            "cleanup.policy": "delete",
            "compression.type": "zstd",
            "retention.ms": "86400000",
        },
    }
    cfg = kafka_metadata_to_interface_config(kafka_metadata)
    assert cfg is not None
    assert cfg.partitions == 3
    assert cfg.replication_factor == 3
    assert cfg.retention_ms == 86400000


def test_kafka_metadata_to_interface_config_returns_none_when_missing_essentials() -> None:
    """필수 값(partitions/replication_factor)을 만들 수 없으면 None을 반환해야 한다."""
    kafka_metadata = {
        # partition_count 없음, config에도 num.partitions 없음
        "config": {"retention.ms": "1000"},
    }
    assert kafka_metadata_to_interface_config(kafka_metadata) is None


def test_kafka_metadata_to_core_metadata_with_config_partition_fallback() -> None:
    """partition_count가 없으면 config[num.partitions]를 사용해야 한다."""
    kafka_metadata = {
        "config": {"num.partitions": "5"},
        "leader_replicas": [1, 2],
        "created_at": "2025-09-25T10:00:00Z",
    }
    meta = kafka_metadata_to_core_metadata(kafka_metadata)
    assert meta is not None
    assert meta.partition_count == 5
    assert meta.leader_replicas == [1, 2]


def test_kafka_metadata_to_core_metadata_returns_none_when_no_partitions() -> None:
    """partition 정보를 도출할 수 없으면 None을 반환해야 한다."""
    kafka_metadata = {"config": {}}
    assert kafka_metadata_to_core_metadata(kafka_metadata) is None


def test_convert_delete_item_without_config_and_metadata() -> None:
    """DELETE 아이템에서 config/metadata가 없을 때 변환 분기를 커버한다."""
    item = TopicItem.model_validate(
        {
            "name": "dev.to.delete",
            "action": "delete",
            "reason": "cleanup",
        }
    )
    spec = safe_convert_item_to_spec(item)
    assert spec.name == "dev.to.delete"
    assert spec.reason == "cleanup"
