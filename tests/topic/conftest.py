"""Topic 테스트용 fixture"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

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
