"""Connect 테스트용 fixture"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.cluster.domain.models import KafkaConnect
from app.cluster.domain.repositories import IKafkaConnectRepository
from app.connect.domain.repositories import IConnectorMetadataRepository
from app.connect.infrastructure.client import KafkaConnectRestClient


@pytest.fixture
def mock_kafka_connect() -> KafkaConnect:
    """Mock KafkaConnect 모델"""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return KafkaConnect(
        connect_id="test-connect",
        cluster_id="test-cluster",
        name="Test Connect",
        url="http://localhost:8083",
        is_active=True,
        description="Test Kafka Connect",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_connect_repository(mock_kafka_connect) -> IKafkaConnectRepository:
    """Mock Kafka Connect Repository"""
    mock = AsyncMock(spec=IKafkaConnectRepository)
    mock.get_by_id.return_value = mock_kafka_connect
    mock.get_by_cluster_id.return_value = [mock_kafka_connect]
    mock.list_all.return_value = [mock_kafka_connect]
    return mock


@pytest.fixture
def mock_connect_client() -> KafkaConnectRestClient:
    """Mock Kafka Connect Client"""
    mock = AsyncMock(spec=KafkaConnectRestClient)

    # 기본 응답 설정
    mock.list_connectors.return_value = ["test-connector"]
    mock.get_connector.return_value = {
        "name": "test-connector",
        "config": {"connector.class": "io.confluent.connect.s3.S3SinkConnector"},
        "tasks": [],
    }
    mock.get_connector_config.return_value = {
        "connector.class": "io.confluent.connect.s3.S3SinkConnector",
        "tasks.max": "1",
    }
    mock.get_connector_status.return_value = {
        "name": "test-connector",
        "connector": {"state": "RUNNING", "worker_id": "worker-1"},
        "tasks": [],
    }
    mock.create_connector.return_value = {"name": "test-connector"}
    mock.update_connector_config.return_value = {"name": "test-connector"}
    mock.delete_connector.return_value = None
    mock.restart_connector.return_value = None
    mock.pause_connector.return_value = None
    mock.resume_connector.return_value = None

    # Tasks
    mock.get_connector_tasks.return_value = [{"connector": "test-connector", "task": 0}]
    mock.get_task_status.return_value = {
        "id": 0,
        "state": "RUNNING",
        "worker_id": "worker-1",
    }
    mock.restart_task.return_value = None

    # Topics
    mock.get_connector_topics.return_value = {"topics": ["test-topic"]}
    mock.reset_connector_topics.return_value = None

    # Plugins
    mock.list_connector_plugins.return_value = [
        {"class": "io.confluent.connect.s3.S3SinkConnector", "type": "sink", "version": "11.0.6"}
    ]
    mock.validate_connector_config.return_value = {
        "name": "test",
        "error_count": 0,
        "groups": [],
        "configs": [],
    }

    return mock


@pytest.fixture
def mock_metadata_repository() -> IConnectorMetadataRepository:
    """Mock Connector Metadata Repository"""
    from datetime import datetime, timezone

    from app.connect.domain.models_metadata import ConnectorMetadata

    mock = AsyncMock(spec=IConnectorMetadataRepository)

    # 기본 메타데이터
    default_metadata = ConnectorMetadata(
        id="meta-123",
        connect_id="test-connect",
        connector_name="test-connector",
        team="data-platform",
        tags=["production", "critical"],
        description="Test connector",
        owner="admin@example.com",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock.get_metadata.return_value = default_metadata
    mock.save_metadata.return_value = default_metadata
    mock.delete_metadata.return_value = True
    mock.list_by_team.return_value = [default_metadata]

    return mock
