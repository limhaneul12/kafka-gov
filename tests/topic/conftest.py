"""Topic 테스트용 fixture"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.cluster.domain.services import IConnectionManager
from app.topic.domain.repositories.interfaces import (
    IAuditRepository,
    ITopicMetadataRepository,
    ITopicRepository,
)


@pytest.fixture
def mock_topic_repository() -> ITopicRepository:
    """Mock Topic Repository"""
    mock = AsyncMock(spec=ITopicRepository)
    mock.describe_topics.return_value = {}
    mock.create_topics.return_value = {}
    mock.delete_topics.return_value = {}
    mock.alter_topic_configs.return_value = {}
    mock.create_partitions.return_value = {}
    return mock


@pytest.fixture
def mock_metadata_repository() -> ITopicMetadataRepository:
    """Mock Metadata Repository"""
    mock = AsyncMock(spec=ITopicMetadataRepository)
    mock.save_plan.return_value = None
    mock.get_plan.return_value = None
    mock.save_apply_result.return_value = None
    mock.get_topic_metadata.return_value = None
    return mock


@pytest.fixture
def mock_audit_repository() -> IAuditRepository:
    """Mock Audit Repository"""
    mock = AsyncMock(spec=IAuditRepository)
    mock.log_topic_operation.return_value = "audit-123"
    return mock


@pytest.fixture
def mock_admin_client() -> MagicMock:
    """Mock Kafka AdminClient (KafkaTopicAdapter에서 사용)"""
    mock = MagicMock()

    # list_topics 메서드 mock
    mock_metadata = MagicMock()
    mock_metadata.topics = {}
    mock.list_topics.return_value = mock_metadata

    # create_topics 메서드 mock (futures 반환)
    mock.create_topics.return_value = {}

    # delete_topics 메서드 mock (futures 반환)
    mock.delete_topics.return_value = {}

    # alter_configs 메서드 mock (futures 반환)
    mock.alter_configs.return_value = {}

    # create_partitions 메서드 mock (futures 반환)
    mock.create_partitions.return_value = {}

    # describe_configs 메서드 mock (futures 반환)
    mock.describe_configs.return_value = {}

    return mock


@pytest.fixture
def mock_connection_manager(mock_admin_client) -> IConnectionManager:
    """Mock Connection Manager (멀티 클러스터 지원)"""
    mock = AsyncMock(spec=IConnectionManager)
    # get_kafka_admin_client가 호출되면 Mock AdminClient 반환
    mock.get_kafka_admin_client.return_value = mock_admin_client
    return mock
