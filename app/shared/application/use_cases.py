"""Shared Application Use Cases"""

from __future__ import annotations

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
