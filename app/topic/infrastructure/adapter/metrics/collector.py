"""통합 메트릭 수집기"""

from typing import Any

from kafka import KafkaAdminClient

from app.topic.domain.models.metrics import TopicMetrics

from .cluster import ClusterMetricsCollector
from .leader import LeaderDistributionCollector
from .partition import PartitionMetricsCollector
from .storage import StorageMetricsCollector


class TopicMetricsCollector:
    """통합 카프카 메트릭 수집기"""

    def __init__(self, admin_client: KafkaAdminClient, ttl_seconds: int = 15) -> None:
        self.partition_metrics = PartitionMetricsCollector(
            admin_client=admin_client, ttl_seconds=ttl_seconds
        )
        self.storage_metrics = StorageMetricsCollector(
            admin_client=admin_client, ttl_seconds=ttl_seconds
        )
        self.cluster_metrics = ClusterMetricsCollector(
            admin_client=admin_client, ttl_seconds=ttl_seconds
        )
        self.leader_metrics = LeaderDistributionCollector(
            admin_client=admin_client, ttl_seconds=ttl_seconds
        )

    async def get_all_topic_metrics(self) -> TopicMetrics | None:
        """전체 토픽 메트릭 조회"""
        return await self.partition_metrics._get_snapshot()

    async def refresh(self) -> None:
        """스냅샷 강제 갱신"""
        await self.partition_metrics.refresh()
        await self.storage_metrics.refresh()
        await self.cluster_metrics.refresh()
        await self.leader_metrics.refresh()

    async def get_topic_distribution_summary(self) -> dict[str, Any]:
        """토픽 분포 요약"""
        metrics = await self.partition_metrics._get_snapshot()
        if not metrics:
            return {}

        summary: dict[str, Any] = {
            "cluster_info": {
                "total_topics": len(metrics.topic_meta),
                "total_partitions": metrics.cluster_metrics.total_partition_count,
                "total_brokers": metrics.cluster_metrics.broker_count,
                "partition_to_broker_ratio": await self.cluster_metrics.get_partition_to_broker_ratio(),
            },
        }
        topics: dict[str, dict[str, int]] = {}
        summary["topics"] = topics

        for topic_name, topic_meta in metrics.topic_meta.items():
            partitions = topic_meta.partition_details
            if partitions:
                total_size = sum(p.partition_size for p in partitions)

                topics[topic_name] = {
                    "partition_count": len(partitions),
                    "total_size_bytes": total_size,
                    "avg_partition_size": int(round(total_size / len(partitions), 0)),
                }

        return summary

    # 위임 메서드들
    async def topic_partition_count(self, topic_name: str) -> int:
        return await self.partition_metrics.topic_partition_count(topic_name)

    async def topic_partition_size(self, topic_name: str) -> int:
        return await self.storage_metrics.topic_partition_size(topic_name)

    async def topic_max_partition_size(self, topic_name: str) -> int:
        return await self.storage_metrics.topic_max_partition_size(topic_name)

    async def topic_min_partition_size(self, topic_name: str) -> int:
        return await self.storage_metrics.topic_min_partition_size(topic_name)

    async def topic_avg_partition_size(self, topic_name: str) -> int:
        return await self.storage_metrics.topic_avg_partition_size(topic_name)

    async def get_cluster_broker_count(self) -> int:
        return await self.cluster_metrics.get_cluster_broker_count()

    async def get_total_partition_count(self) -> int:
        return await self.cluster_metrics.get_total_partition_count()

    async def get_partition_to_broker_ratio(self) -> float:
        return await self.cluster_metrics.get_partition_to_broker_ratio()

    async def get_leader_distribution(self) -> dict[int, int]:
        return await self.leader_metrics.get_leader_distribution()
