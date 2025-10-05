"""Shared Domain Repository Interfaces"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

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

    @abstractmethod
    async def get_activity_history(
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
            limit: 최대 조회 개수

        Returns:
            필터링된 활동 목록 (시간 역순)
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
