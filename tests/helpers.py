"""테스트 헬퍼 유틸리티."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from app.policy.domain.models import DomainEnvironment


def create_mock_user(user_id: str = "test_user") -> dict[str, Any]:
    """테스트용 사용자 모의 객체 생성."""
    return {
        "user_id": user_id,
        "username": f"{user_id}@example.com",
        "roles": ["user"],
        "is_active": True,
    }


def create_mock_kafka_admin() -> AsyncMock:
    """테스트용 Kafka AdminClient 모의 객체 생성."""
    mock_admin = AsyncMock()
    mock_admin.create_topics = AsyncMock(return_value={})
    mock_admin.delete_topics = AsyncMock(return_value={})
    mock_admin.describe_topics = AsyncMock(return_value={})
    mock_admin.list_topics = AsyncMock(return_value=MagicMock())
    return mock_admin


def create_test_timestamp() -> datetime:
    """테스트용 고정 타임스탬프 생성."""
    return datetime(2025, 9, 26, 23, 45, 0)


def get_test_environment() -> DomainEnvironment:
    """테스트용 환경 반환."""
    return DomainEnvironment.DEV


class MockAsyncContextManager:
    """비동기 컨텍스트 매니저 모의 객체."""

    def __init__(self, return_value: Any = None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
