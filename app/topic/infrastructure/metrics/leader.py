"""리더 분포 관련 메트릭 수집기"""

import asyncio

from app.topic.domain.repositories.metrics_interfaces import ILeaderDistributionRepository
from app.topic.infrastructure.adapter.kafka_metric_adapter import BaseMetricsCollector


class LeaderDistributionCollector(BaseMetricsCollector, ILeaderDistributionRepository):
    """리더 분포 관련 메트릭 수집기"""

    async def get_leader_distribution(self) -> dict[int, int]:
        """리더 분포 (브로커별 리더 파티션 수)"""
        metrics = await self._get_snapshot()
        if not metrics:
            return {}

        leader_distribution = {}

        # 토픽 메타데이터에서 리더 정보 수집 (비동기)
        topic_names = await asyncio.to_thread(self.admin.list_topics)
        topics_metadata = await asyncio.to_thread(self.admin.describe_topics, topic_names)

        for topic_metadata in topics_metadata:
            for partition in topic_metadata["partitions"]:
                leader = partition["leader"]
                if leader != -1:  # -1은 리더가 없는 경우
                    leader_distribution[leader] = leader_distribution.get(leader, 0) + 1

        return leader_distribution
