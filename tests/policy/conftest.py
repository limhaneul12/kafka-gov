"""Policy 테스트용 fixture"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.policy.domain.repository import IPolicyRepository


@pytest.fixture
def mock_policy_repository() -> IPolicyRepository:
    """Mock Policy Repository"""
    mock = AsyncMock(spec=IPolicyRepository)
    mock.get_policy.return_value = None
    mock.list_policies.return_value = []
    return mock
