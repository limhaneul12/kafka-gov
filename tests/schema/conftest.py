"""Schema 테스트용 fixture"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.schema.domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaRegistryRepository,
)


@pytest.fixture
def mock_registry_repository() -> ISchemaRegistryRepository:
    """Mock Schema Registry Repository"""
    mock = AsyncMock(spec=ISchemaRegistryRepository)
    mock.describe_subjects.return_value = {}
    mock.check_compatibility.return_value = None
    mock.register_schema.return_value = 1
    mock.delete_subject.return_value = None
    return mock


@pytest.fixture
def mock_schema_metadata_repository() -> ISchemaMetadataRepository:
    """Mock Schema Metadata Repository"""
    mock = AsyncMock(spec=ISchemaMetadataRepository)
    mock.list_artifacts.return_value = []
    mock.record_artifact.return_value = None
    mock.delete_artifact_by_subject.return_value = None
    mock.save_plan.return_value = None
    mock.get_plan.return_value = None
    mock.save_apply_result.return_value = None
    mock.save_upload_result.return_value = None
    return mock


@pytest.fixture
def mock_schema_audit_repository() -> ISchemaAuditRepository:
    """Mock Schema Audit Repository"""
    mock = AsyncMock(spec=ISchemaAuditRepository)
    mock.log_operation.return_value = "test-log-id"
    return mock


@pytest.fixture
def mock_connection_manager(mock_registry_repository):
    """Mock Connection Manager for UseCase tests

    UseCase들이 ConnectionManager를 통해 registry/storage client를 얻도록 변경되었으므로
    ConnectionManager mock이 필요합니다.
    """
    from unittest.mock import AsyncMock, MagicMock

    mock_cm = AsyncMock()

    # get_schema_registry_client returns a mock registry client (AsyncMock으로 변경)
    mock_registry_client = AsyncMock()
    mock_registry_client.get_subjects = AsyncMock(return_value=[])
    mock_registry_client.get_latest_version = AsyncMock(return_value=None)
    mock_registry_client.test_compatibility = AsyncMock(return_value=True)
    mock_registry_client.register_schema = AsyncMock(return_value=1)
    mock_registry_client.delete_subject = AsyncMock(return_value=[])
    mock_registry_client.get_versions = AsyncMock(return_value=[])
    mock_registry_client.get_version = AsyncMock(return_value=None)
    mock_registry_client.set_config = AsyncMock(return_value=None)

    mock_cm.get_schema_registry_client = AsyncMock(return_value=mock_registry_client)

    # get_minio_client returns (client, bucket_name)
    mock_minio_client = MagicMock()
    mock_minio_client.put_object = MagicMock(return_value=None)
    mock_cm.get_minio_client = AsyncMock(return_value=(mock_minio_client, "test-bucket"))

    # get_storage_info returns storage info with base_url
    mock_storage_info = MagicMock()
    mock_storage_info.get_base_url = MagicMock(return_value="http://localhost:9000")
    mock_storage_info.endpoint_url = "localhost:9000"
    mock_cm.get_storage_info = AsyncMock(return_value=mock_storage_info)

    return mock_cm
