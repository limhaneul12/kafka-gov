"""Analysis 테스트용 fixture"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.analysis.domain.repositories import ICorrelationRepository


@pytest.fixture
def mock_correlation_repository() -> ICorrelationRepository:
    """Mock Correlation Repository"""
    mock = AsyncMock(spec=ICorrelationRepository)
    mock.find_by_schema.return_value = []
    mock.find_by_topic.return_value = None
    mock.save.return_value = None
    return mock
