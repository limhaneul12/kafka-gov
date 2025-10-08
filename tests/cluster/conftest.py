"""Cluster 테스트용 fixture"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.cluster.domain.models import (
    KafkaCluster,
    ObjectStorage,
    SchemaRegistry,
    SecurityProtocol,
)
from app.cluster.domain.repositories import (
    IKafkaClusterRepository,
    IObjectStorageRepository,
    ISchemaRegistryRepository,
)


@pytest.fixture
def sample_kafka_cluster() -> KafkaCluster:
    """테스트용 Kafka 클러스터"""
    return KafkaCluster(
        cluster_id="test-cluster-1",
        name="Test Kafka Cluster",
        bootstrap_servers="localhost:9092",
        description="Test cluster",
        security_protocol=SecurityProtocol.PLAINTEXT,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_schema_registry() -> SchemaRegistry:
    """테스트용 Schema Registry"""
    return SchemaRegistry(
        registry_id="test-registry-1",
        name="Test Schema Registry",
        url="http://localhost:8081",
        description="Test registry",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_object_storage() -> ObjectStorage:
    """테스트용 Object Storage"""
    return ObjectStorage(
        storage_id="test-storage-1",
        name="Test MinIO",
        endpoint_url="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket_name="test-bucket",
        description="Test storage",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def mock_kafka_cluster_repo() -> IKafkaClusterRepository:
    """Mock Kafka Cluster Repository"""
    mock = AsyncMock(spec=IKafkaClusterRepository)
    mock.get_by_id.return_value = None
    mock.list_all.return_value = []
    mock.create.return_value = None
    mock.update.return_value = None
    mock.delete.return_value = None
    return mock


@pytest.fixture
def mock_schema_registry_repo() -> ISchemaRegistryRepository:
    """Mock Schema Registry Repository"""
    mock = AsyncMock(spec=ISchemaRegistryRepository)
    mock.get_by_id.return_value = None
    mock.list_all.return_value = []
    mock.create.return_value = None
    return mock


@pytest.fixture
def mock_object_storage_repo() -> IObjectStorageRepository:
    """Mock Object Storage Repository"""
    mock = AsyncMock(spec=IObjectStorageRepository)
    mock.get_by_id.return_value = None
    mock.list_all.return_value = []
    mock.create.return_value = None
    return mock
