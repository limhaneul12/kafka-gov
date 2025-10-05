"""Shared Domain Repository Interfaces"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import AuditActivity, ClusterStatus


class IAuditActivityRepository(ABC):
    """감사 활동 조회 리포지토리 인터페이스"""

    @abstractmethod
    async def get_recent_activities(self, limit: int) -> list[AuditActivity]:
        """
        최근 활동 조회 (Topic + Schema 통합)

        Args:
            limit: 조회할 최대 개수

        Returns:
            최근 활동 목록 (시간 역순)
        """
        ...


class IClusterRepository(ABC):
    """Kafka 클러스터 정보 조회 리포지토리 인터페이스"""

    @abstractmethod
    async def get_cluster_status(self) -> ClusterStatus:
        """
        Kafka 클러스터 상태 조회

        Returns:
            클러스터 상태 정보 (브로커, 토픽, 파티션 수)
        """
        ...
