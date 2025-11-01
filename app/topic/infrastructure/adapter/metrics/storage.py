"""저장용량 관련 메트릭 수집기"""

from app.topic.infrastructure.adapter.kafka_metric_adapter import BaseMetricsCollector


class StorageMetricsCollector(BaseMetricsCollector):
    """저장용량 관련 메트릭 수집기"""

    async def topic_partition_size(self, topic_name: str) -> int:
        """토픽의 전체 파티션 크기"""
        partitions = await self._get_topic_partitions(topic_name)
        return sum(p.partition_size for p in partitions)

    async def topic_max_partition_size(self, topic_name: str) -> int:
        """토픽의 가장 큰 파티션 크기"""
        partitions = await self._get_topic_partitions(topic_name)
        return max(p.partition_size for p in partitions) if partitions else 0

    async def topic_min_partition_size(self, topic_name: str) -> int:
        """토픽의 가장 작은 파티션 크기"""
        partitions = await self._get_topic_partitions(topic_name)
        return min(p.partition_size for p in partitions) if partitions else 0

    async def topic_avg_partition_size(self, topic_name: str) -> int:
        """토픽의 평균 파티션 크기"""
        partitions = await self._get_topic_partitions(topic_name)
        if not partitions:
            return 0
        return int(round(sum(p.partition_size for p in partitions) / len(partitions), 0))
