"""클러스터 및 브로커 관련 메트릭 수집기"""

from app.topic.domain.repositories.metrics_interfaces import IClusterMetricsRepository
from app.topic.infrastructure.adapter.kafka_metric_adapter import BaseMetricsCollector


class ClusterMetricsCollector(BaseMetricsCollector, IClusterMetricsRepository):
    """클러스터 및 브로커 관련 메트릭 수집기"""

    async def get_cluster_broker_count(self) -> int:
        """클러스터 브로커 수"""
        metrics = await self._get_snapshot()
        return metrics.cluster_metrics.broker_count if metrics else 0

    async def get_partition_to_broker_ratio(self) -> float:
        """파티션 수 대비 브로커 수 비율"""
        broker_count = await self.get_cluster_broker_count()
        partition_count = await self.get_total_partition_count()

        if broker_count == 0:
            return 0.0
        return round(partition_count / broker_count, 2)

    async def get_total_partition_count(self) -> int:
        """전체 파티션 수"""
        metrics = await self._get_snapshot()
        return metrics.cluster_metrics.total_partition_count if metrics else 0
