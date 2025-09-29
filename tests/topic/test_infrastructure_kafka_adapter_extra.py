"""KafkaTopicAdapter 추가 브랜치 커버리지 테스트"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from confluent_kafka.admin import AdminClient

from app.topic.domain.models import (
    DomainTopicAction as TopicAction,
    DomainTopicConfig as TopicConfig,
    DomainTopicMetadata as TopicMetadata,
    DomainTopicSpec as TopicSpec,
)
from app.topic.infrastructure.kafka_adapter import KafkaTopicAdapter


@pytest.fixture
def mock_admin_client() -> MagicMock:
    return MagicMock(spec=AdminClient)


@pytest.fixture
def adapter(mock_admin_client: MagicMock) -> KafkaTopicAdapter:
    return KafkaTopicAdapter(mock_admin_client)


@pytest.fixture
def sample_spec() -> TopicSpec:
    return TopicSpec(
        name="dev.update.topic",
        action=TopicAction.CREATE,
        config=TopicConfig(partitions=3, replication_factor=2),
        metadata=TopicMetadata(owner="data-team"),
    )


@pytest.mark.asyncio
async def test_alter_topic_configs_with_configresource_like_keys(
    adapter: KafkaTopicAdapter, mock_admin_client: MagicMock
) -> None:
    """alter_configs가 ConfigResource 유사 객체 키를 반환하는 경우 처리해야 한다."""
    future = MagicMock()
    future.result.return_value = None
    resource_like1 = MagicMock()
    resource_like1.name = "dev.user.events"
    resource_like2 = MagicMock()
    resource_like2.name = "dev.order.events"

    mock_admin_client.alter_configs.return_value = {
        resource_like1: future,
        resource_like2: future,
    }

    result = await adapter.alter_topic_configs(
        {
            "dev.user.events": {"retention.ms": "86400000"},
            "dev.order.events": {"cleanup.policy": "compact"},
        }
    )
    assert result == {"dev.user.events": None, "dev.order.events": None}


@pytest.mark.asyncio
async def test_create_topics_outer_error(
    adapter: KafkaTopicAdapter, mock_admin_client: MagicMock, sample_spec: TopicSpec
) -> None:
    mock_admin_client.create_topics.side_effect = Exception("boom")
    result = await adapter.create_topics([sample_spec])
    assert isinstance(result["dev.update.topic"], Exception)


@pytest.mark.asyncio
async def test_delete_topics_outer_error(
    adapter: KafkaTopicAdapter, mock_admin_client: MagicMock
) -> None:
    mock_admin_client.delete_topics.side_effect = Exception("boom")
    names = ["dev.user.events", "dev.order.events"]
    result = await adapter.delete_topics(names)
    assert set(result.keys()) == set(names)
    for v in result.values():
        assert isinstance(v, Exception)


@pytest.mark.asyncio
async def test_alter_topic_configs_outer_error(
    adapter: KafkaTopicAdapter, mock_admin_client: MagicMock
) -> None:
    mock_admin_client.alter_configs.side_effect = Exception("boom")
    configs = {"dev.user.events": {"retention.ms": "1000"}}
    result = await adapter.alter_topic_configs(configs)
    assert set(result.keys()) == {"dev.user.events"}
    assert isinstance(result["dev.user.events"], Exception)


@pytest.mark.asyncio
async def test_create_partitions_outer_error(
    adapter: KafkaTopicAdapter, mock_admin_client: MagicMock
) -> None:
    mock_admin_client.create_partitions.side_effect = Exception("boom")
    partitions = {"dev.user.events": 6}
    result = await adapter.create_partitions(partitions)
    assert set(result.keys()) == {"dev.user.events"}
    assert isinstance(result["dev.user.events"], Exception)


@pytest.mark.asyncio
async def test_describe_topics_empty_names_returns_empty(adapter: KafkaTopicAdapter) -> None:
    result = await adapter.describe_topics([])
    assert result == {}


@pytest.mark.asyncio
async def test_describe_topics_outer_exception_returns_empty(
    adapter: KafkaTopicAdapter, mock_admin_client: MagicMock
) -> None:
    mock_admin_client.list_topics.side_effect = Exception("boom")
    result = await adapter.describe_topics(["dev.user.events"])
    assert result == {}


@pytest.mark.asyncio
async def test_get_topic_metadata_handles_error(adapter: KafkaTopicAdapter) -> None:
    with patch.object(adapter, "describe_topics", side_effect=Exception("boom")):
        result = await adapter.get_topic_metadata("dev.user.events")
        assert result is None
