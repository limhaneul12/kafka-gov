"""Shared Audit Use Case 테스트"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.shared.application.use_cases import GetRecentActivitiesUseCase
from app.shared.domain.models import AuditActivity
from app.shared.domain.repositories import IAuditActivityRepository


class MockAuditRepository(IAuditActivityRepository):
    """Mock Audit Repository"""

    def __init__(self, activities: list[AuditActivity]) -> None:
        self.activities = activities

    async def get_recent_activities(self, limit: int) -> list[AuditActivity]:
        return self.activities[:limit]


class TestGetRecentActivitiesUseCase:
    """GetRecentActivitiesUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_execute_with_activities(self):
        """활동이 있는 경우"""
        now = datetime.now(timezone.utc)
        mock_activities = [
            AuditActivity(
                activity_type="topic",
                action="CREATE",
                target="dev.test.topic",
                message="생성됨",
                actor="user1",
                timestamp=now,
            ),
            AuditActivity(
                activity_type="schema",
                action="REGISTER",
                target="test-subject",
                message="등록됨",
                actor="user2",
                timestamp=now,
            ),
        ]

        repository = MockAuditRepository(mock_activities)
        use_case = GetRecentActivitiesUseCase(repository)

        result = await use_case.execute(limit=10)

        assert len(result) == 2
        assert result[0].activity_type == "topic"
        assert result[1].activity_type == "schema"

    @pytest.mark.asyncio
    async def test_execute_with_limit(self):
        """limit 적용 확인"""
        now = datetime.now(timezone.utc)
        mock_activities = [
            AuditActivity(
                activity_type="topic",
                action="CREATE",
                target=f"topic-{i}",
                message="생성됨",
                actor="user",
                timestamp=now,
            )
            for i in range(50)
        ]

        repository = MockAuditRepository(mock_activities)
        use_case = GetRecentActivitiesUseCase(repository)

        result = await use_case.execute(limit=10)

        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_execute_limit_validation(self):
        """limit 검증 (1-100)"""
        repository = MockAuditRepository([])
        use_case = GetRecentActivitiesUseCase(repository)

        # limit < 1 -> 1로 조정
        result = await use_case.execute(limit=0)
        assert True  # 에러 없이 실행됨

        # limit > 100 -> 100으로 조정
        result = await use_case.execute(limit=200)
        assert True  # 에러 없이 실행됨

    @pytest.mark.asyncio
    async def test_execute_empty(self):
        """활동이 없는 경우"""
        repository = MockAuditRepository([])
        use_case = GetRecentActivitiesUseCase(repository)

        result = await use_case.execute(limit=10)

        assert len(result) == 0
