"""파티션 수 관련 메트릭 수집기"""

from app.topic.infrastructure.adapter.kafka_metric_adapter import BaseMetricsCollector


class PartitionMetricsCollector(BaseMetricsCollector):
    """파티션 수 관련 메트릭 수집기"""

    async def topic_partition_count(self, topic_name: str) -> int:
        """토픽의 파티션 수"""
        partitions = await self._get_topic_partitions(topic_name)
        return len(partitions)

    async def get_total_partition_count(self) -> int:
        """전체 파티션 수"""
        metrics = await self._get_snapshot()
        return metrics.cluster_metrics.total_partition_count if metrics else 0
