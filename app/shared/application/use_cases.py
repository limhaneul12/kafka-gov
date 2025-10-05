"""Shared Application Use Cases"""

from __future__ import annotations

from datetime import datetime

from app.shared.domain.models import AuditActivity, ClusterStatus
from app.shared.domain.repositories import IAuditActivityRepository, IClusterRepository


class GetRecentActivitiesUseCase:
    """최근 활동 조회 Use Case"""

    def __init__(self, audit_repository: IAuditActivityRepository) -> None:
        self.audit_repository = audit_repository

    async def execute(self, limit: int = 20) -> list[AuditActivity]:
        """
        최근 활동 조회

        Args:
            limit: 조회할 최대 개수 (1-100)

        Returns:
            최근 활동 목록
        """
        # 입력 검증
        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        # Repository를 통해 조회
        activities = await self.audit_repository.get_recent_activities(limit)

        return activities


class GetActivityHistoryUseCase:
    """활동 히스토리 조회 Use Case"""

    def __init__(self, audit_repository: IAuditActivityRepository) -> None:
        self.audit_repository = audit_repository

    async def execute(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        activity_type: str | None = None,
        action: str | None = None,
        actor: str | None = None,
        limit: int = 100,
    ) -> list[AuditActivity]:
        """
        활동 히스토리 조회 (필터링 지원)

        Args:
            from_date: 시작 날짜/시간
            to_date: 종료 날짜/시간
            activity_type: 활동 타입 ("topic" or "schema")
            action: 액션 타입
            actor: 수행자
            limit: 최대 조회 개수 (기본 100개, 최대 500개)

        Returns:
            필터링된 활동 목록 (시간 역순)
        """
        # 입력 검증
        if limit < 1:
            limit = 1
        elif limit > 500:
            limit = 500

        # Repository를 통해 조회
        activities = await self.audit_repository.get_activity_history(
            from_date=from_date,
            to_date=to_date,
            activity_type=activity_type,
            action=action,
            actor=actor,
            limit=limit,
        )

        return activities


class GetClusterStatusUseCase:
    """Kafka 클러스터 상태 조회 Use Case"""

    def __init__(self, cluster_repository: IClusterRepository) -> None:
        self.cluster_repository = cluster_repository

    async def execute(self) -> ClusterStatus:
        """
        Kafka 클러스터 상태 조회

        Returns:
            클러스터 상태 정보
        """
        return await self.cluster_repository.get_cluster_status()
