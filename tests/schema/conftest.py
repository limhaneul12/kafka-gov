"""Schema 테스트용 fixture"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.schema.domain.repositories.interfaces import ISchemaRegistryRepository


@pytest.fixture
def mock_registry_repository() -> ISchemaRegistryRepository:
    """Mock Schema Registry Repository"""
    mock = AsyncMock(spec=ISchemaRegistryRepository)
    mock.describe_subjects.return_value = {}
    mock.check_compatibility.return_value = None
    mock.register_schema.return_value = 1
    mock.delete_subject.return_value = None
    return mock
