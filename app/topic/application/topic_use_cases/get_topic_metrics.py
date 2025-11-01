"""토픽 메트릭 조회 use case"""

from typing import Any

from app.topic.domain.repositories.interfaces import IMetricsRepository


class GetTopicMetricsUseCase:
    """토픽 메트릭 조회 use case (스냅샷 기반)"""

    def __init__(self, metrics_repository: IMetricsRepository) -> None:
        self.metrics_repository = metrics_repository

    async def execute(self, cluster_id: str, topic_name: str | None = None) -> dict[str, Any]:
        """토픽 메트릭 조회 (최신 스냅샷 기준)

        Args:
            cluster_id: 클러스터 ID
            topic_name: 특정 토픽 이름 (None이면 전체 요약)

        Returns:
            메트릭 데이터
        """
        if topic_name:
            return await self.metrics_repository.get_latest_topic_metrics(cluster_id, topic_name)
        return await self.metrics_repository.get_latest_topic_distribution(cluster_id)


class GetClusterMetricsUseCase:
    """클러스터 메트릭 조회 use case (스냅샷 기반)"""

    def __init__(self, metrics_repository: IMetricsRepository) -> None:
        self.metrics_repository = metrics_repository

    async def execute(self, cluster_id: str) -> dict[str, Any]:
        """클러스터 메트릭 조회 (최신 스냅샷 기준)

        Returns:
            클러스터 메트릭 데이터
        """
        return await self.metrics_repository.get_latest_cluster_summary(cluster_id)
