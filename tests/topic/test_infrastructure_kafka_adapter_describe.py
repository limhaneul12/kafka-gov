"""KafkaTopicAdapter.describe_topics 성공 경로 커버리지"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from confluent_kafka.admin import AdminClient

from app.topic.infrastructure.kafka_adapter import KafkaTopicAdapter


@pytest.fixture
def adapter() -> KafkaTopicAdapter:
    return KafkaTopicAdapter(MagicMock(spec=AdminClient))


class _FakeFutures(dict):
    def __init__(self, future: MagicMock) -> None:
        super().__init__()
        self._future = future

    def __getitem__(self, key):
        # 어떤 키로 접근하더라도 동일 future 반환
        return self._future


@pytest.mark.asyncio
async def test_describe_topics_success(adapter: KafkaTopicAdapter) -> None:
    """list_topics/describe_configs 정상 경로를 통해 결과를 구성해야 한다."""
    # metadata.topics[name] 모킹
    partition0 = SimpleNamespace(id=0, leader=1, replicas=[1, 2], isrs=[1, 2])
    topic_meta = SimpleNamespace(partitions={0: partition0})
    metadata = SimpleNamespace(topics={"dev.user.events": topic_meta})

    # list_topics 반환
    adapter.admin_client.list_topics.return_value = metadata  # type: ignore[attr-defined]

    # describe_configs 반환 (키 일치가 어려워 모든 키에 대해 동일 future 반환)
    future = MagicMock()
    cfg_entry_retention = SimpleNamespace(name="retention.ms", value="86400000")
    cfg_entry_cleanup = SimpleNamespace(name="cleanup.policy", value="delete")
    cfg_result = {"retention.ms": cfg_entry_retention, "cleanup.policy": cfg_entry_cleanup}
    future.result.return_value = cfg_result

    adapter.admin_client.describe_configs.return_value = _FakeFutures(future)  # type: ignore[attr-defined]

    result = await adapter.describe_topics(["dev.user.events"])
    assert result["dev.user.events"]["partition_count"] == 1
    assert result["dev.user.events"]["config"]["retention.ms"] == "86400000"
