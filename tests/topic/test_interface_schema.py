"""Interface Schema 테스트"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.topic.interface.schema import (
    TopicBatchRequest,
    TopicConfig,
    TopicItem,
    TopicMetadata,
)
from app.topic.interface.types import (
    CleanupPolicy,
    CompressionType,
    Environment,
    TopicAction,
)


class TestTopicMetadata:
    """TopicMetadata Pydantic 스키마 테스트"""

    def test_valid_metadata(self):
        """정상적인 메타데이터"""
        data = {
            "owner": "team-commerce",
            "sla": "P99<200ms",
            "doc": "https://wiki.company.com/orders",
            "tags": ["pii", "critical"],
        }

        metadata = TopicMetadata.model_validate(data)

        assert metadata.owner == "team-commerce"
        assert metadata.sla == "P99<200ms"
        assert metadata.doc == "https://wiki.company.com/orders"
        assert len(metadata.tags) == 2

    def test_owner_required(self):
        """owner는 필수"""
        data = {"sla": "P99<200ms"}

        with pytest.raises(ValidationError):
            TopicMetadata.model_validate(data)

    def test_owner_cannot_be_empty(self):
        """owner는 빈 문자열 불가"""
        data = {"owner": ""}

        with pytest.raises(ValidationError):
            TopicMetadata.model_validate(data)

    def test_optional_fields(self):
        """선택적 필드"""
        data = {"owner": "team-test"}

        metadata = TopicMetadata.model_validate(data)

        assert metadata.owner == "team-test"
        assert metadata.sla is None
        assert metadata.doc is None
        assert metadata.tags == []

    def test_extra_fields_forbidden(self):
        """추가 필드 금지"""
        data = {
            "owner": "team-test",
            "extra_field": "not allowed",
        }

        with pytest.raises(ValidationError):
            TopicMetadata.model_validate(data)

    def test_tags_max_length(self):
        """태그 최대 개수"""
        data = {
            "owner": "team-test",
            "tags": [f"tag{i}" for i in range(11)],  # 11개 (최대 10개)
        }

        with pytest.raises(ValidationError):
            TopicMetadata.model_validate(data)


class TestTopicConfig:
    """TopicConfig Pydantic 스키마 테스트"""

    def test_valid_config(self):
        """정상적인 설정"""
        data = {
            "partitions": 12,
            "replication_factor": 3,
            "cleanup_policy": "compact",
            "compression_type": "zstd",
            "retention_ms": 604800000,
            "min_insync_replicas": 2,
        }

        config = TopicConfig.model_validate(data)

        assert config.partitions == 12
        assert config.replication_factor == 3
        assert config.cleanup_policy == CleanupPolicy.COMPACT
        assert config.compression_type == CompressionType.ZSTD

    def test_partitions_required(self):
        """partitions 필수"""
        data = {
            "replication_factor": 3,
        }

        with pytest.raises(ValidationError):
            TopicConfig.model_validate(data)

    def test_partitions_must_be_positive(self):
        """partitions는 양수"""
        data = {
            "partitions": 0,
            "replication_factor": 2,
        }

        with pytest.raises(ValidationError):
            TopicConfig.model_validate(data)

    def test_min_insync_replicas_validation(self):
        """min_insync_replicas 검증"""
        data = {
            "partitions": 6,
            "replication_factor": 2,
            "min_insync_replicas": 3,  # replication_factor보다 큼
        }

        with pytest.raises(ValidationError, match="min_insync_replicas.*cannot be greater"):
            TopicConfig.model_validate(data)

    def test_default_values(self):
        """기본값"""
        data = {
            "partitions": 6,
            "replication_factor": 2,
        }

        config = TopicConfig.model_validate(data)

        assert config.cleanup_policy == CleanupPolicy.DELETE
        assert config.compression_type == CompressionType.ZSTD
        assert config.retention_ms is None

    def test_config_is_immutable(self):
        """설정은 불변"""
        data = {
            "partitions": 6,
            "replication_factor": 2,
        }

        config = TopicConfig.model_validate(data)

        with pytest.raises(ValidationError):
            config.partitions = 12  # type: ignore[misc]


class TestTopicItem:
    """TopicItem Pydantic 스키마 테스트"""

    def test_valid_create_item(self):
        """정상적인 생성 아이템"""
        data = {
            "name": "dev.test.topic",
            "action": "create",
            "config": {
                "partitions": 6,
                "replication_factor": 2,
            },
            "metadata": {
                "owner": "team-test",
            },
        }

        item = TopicItem.model_validate(data)

        assert item.name == "dev.test.topic"
        assert item.action == TopicAction.CREATE
        assert item.config is not None
        assert item.metadata is not None

    def test_valid_delete_item(self):
        """정상적인 삭제 아이템"""
        data = {
            "name": "dev.test.topic",
            "action": "delete",
            "reason": "Not needed anymore",
        }

        item = TopicItem.model_validate(data)

        assert item.name == "dev.test.topic"
        assert item.action == TopicAction.DELETE
        assert item.reason == "Not needed anymore"

    def test_delete_requires_reason(self):
        """DELETE는 reason 필수"""
        data = {
            "name": "dev.test.topic",
            "action": "delete",
        }

        with pytest.raises(ValidationError, match="reason is required for delete action"):
            TopicItem.model_validate(data)

    def test_delete_should_not_have_config(self):
        """DELETE는 config 불필요"""
        data = {
            "name": "dev.test.topic",
            "action": "delete",
            "config": {
                "partitions": 6,
                "replication_factor": 2,
            },
            "reason": "Clean up",
        }

        with pytest.raises(
            ValidationError, match="config should not be provided for delete action"
        ):
            TopicItem.model_validate(data)

    def test_create_requires_config(self):
        """CREATE는 config 필수"""
        data = {
            "name": "dev.test.topic",
            "action": "create",
            "metadata": {
                "owner": "team-test",
            },
        }

        with pytest.raises(ValidationError, match=r"config is required for.*CREATE"):
            TopicItem.model_validate(data)

    def test_create_requires_metadata(self):
        """CREATE는 metadata 필수"""
        data = {
            "name": "dev.test.topic",
            "action": "create",
            "config": {
                "partitions": 6,
                "replication_factor": 2,
            },
        }

        with pytest.raises(ValidationError, match=r"metadata is required for.*CREATE"):
            TopicItem.model_validate(data)


class TestTopicBatchRequest:
    """TopicBatchRequest Pydantic 스키마 테스트"""

    def test_valid_batch(self):
        """정상적인 배치"""
        data = {
            "kind": "TopicBatch",
            "env": "dev",
            "change_id": "test-001",
            "items": [
                {
                    "name": "dev.test.topic",
                    "action": "create",
                    "config": {
                        "partitions": 6,
                        "replication_factor": 2,
                    },
                    "metadata": {
                        "owner": "team-test",
                    },
                }
            ],
        }

        batch = TopicBatchRequest.model_validate(data)

        assert batch.env == Environment.DEV
        assert batch.change_id == "test-001"
        assert len(batch.items) == 1

    def test_items_cannot_be_empty(self):
        """items는 비어있을 수 없음"""
        data = {
            "env": "dev",
            "change_id": "test-001",
            "items": [],
        }

        with pytest.raises(ValidationError):
            TopicBatchRequest.model_validate(data)

    def test_duplicate_topic_names(self):
        """중복된 토픽 이름"""
        data = {
            "env": "dev",
            "change_id": "test-001",
            "items": [
                {
                    "name": "dev.test.topic",
                    "action": "create",
                    "config": {"partitions": 6, "replication_factor": 2},
                    "metadata": {"owner": "team-test"},
                },
                {
                    "name": "dev.test.topic",  # 중복
                    "action": "delete",
                    "reason": "Clean up",
                },
            ],
        }

        with pytest.raises(ValidationError, match="Duplicate topic names found"):
            TopicBatchRequest.model_validate(data)

    def test_environment_consistency(self):
        """환경 일관성"""
        data = {
            "env": "dev",
            "change_id": "test-001",
            "items": [
                {
                    "name": "prod.test.topic",  # 다른 환경
                    "action": "create",
                    "config": {"partitions": 6, "replication_factor": 2},
                    "metadata": {"owner": "team-test"},
                }
            ],
        }

        with pytest.raises(ValidationError, match="does not match batch environment"):
            TopicBatchRequest.model_validate(data)

    def test_max_items_limit(self):
        """최대 아이템 개수"""
        data = {
            "env": "dev",
            "change_id": "test-001",
            "items": [
                {
                    "name": f"dev.test{i}.topic",
                    "action": "create",
                    "config": {"partitions": 3, "replication_factor": 2},
                    "metadata": {"owner": "team-test"},
                }
                for i in range(101)  # 101개 (최대 100개)
            ],
        }

        with pytest.raises(ValidationError):
            TopicBatchRequest.model_validate(data)

    def test_default_kind(self):
        """기본 kind 값"""
        data = {
            "env": "dev",
            "change_id": "test-001",
            "items": [
                {
                    "name": "dev.test.topic",
                    "action": "create",
                    "config": {"partitions": 6, "replication_factor": 2},
                    "metadata": {"owner": "team-test"},
                }
            ],
        }

        batch = TopicBatchRequest.model_validate(data)

        assert batch.kind == "TopicBatch"

    def test_whitespace_stripping(self):
        """공백 제거"""
        data = {
            "env": "dev",
            "change_id": "  test-001  ",
            "items": [
                {
                    "name": "  dev.test.topic  ",
                    "action": "create",
                    "config": {"partitions": 6, "replication_factor": 2},
                    "metadata": {"owner": "  team-test  "},
                }
            ],
        }

        batch = TopicBatchRequest.model_validate(data)

        assert batch.change_id == "test-001"
        assert batch.items[0].name == "dev.test.topic"
        assert batch.items[0].metadata.owner == "team-test"  # type: ignore[union-attr]
