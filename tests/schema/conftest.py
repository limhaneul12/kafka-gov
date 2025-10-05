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
