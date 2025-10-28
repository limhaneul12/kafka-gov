"""Consumer Group Live Collector

실시간 모니터링 데이터 수집 서비스
"""

from datetime import UTC, datetime

from confluent_kafka.admin import AdminClient

from app.consumer.domain.services import ConsumerDataCollector, ConsumerMetricsCalculator
from app.consumer.infrastructure.kafka_consumer_adapter import KafkaConsumerAdapter
from app.consumer.interface.schema.live_schema import (
    ConsumerGroupLiveSnapshot,
    LagStatsLive,
    MemberLiveInfo,
    PartitionLiveInfo,
)


class ConsumerGroupLiveCollector:
    """실시간 Consumer Group 데이터 수집기

    책임:
    - 단일 타임스탬프로 일관된 스냅샷 수집
    - 경량 데이터 구조로 변환
    - Stuck/Spike 감지
    """

    # Threshold 설정
    STUCK_LAG_THRESHOLD = 10_000
    LAG_SPIKE_THRESHOLD = 50_000

    def __init__(
        self,
        admin_client: AdminClient,
        cluster_id: str,
    ) -> None:
        """
        Args:
            admin_client: Kafka AdminClient
            cluster_id: 클러스터 ID
        """
        self._admin_client = admin_client
        self._cluster_id = cluster_id
        self._adapter = KafkaConsumerAdapter(admin_client)
        self._collector = ConsumerDataCollector(self._adapter, cluster_id)
        self._calculator = ConsumerMetricsCalculator()

    async def collect_live_snapshot(self, group_id: str) -> ConsumerGroupLiveSnapshot:
        """실시간 스냅샷 수집

        단일 타임스탬프로 모든 데이터를 수집하여 일관성 보장

        Args:
            group_id: Consumer Group ID

        Returns:
            ConsumerGroupLiveSnapshot

        Raises:
            KeyError: 그룹이 존재하지 않음
        """
        # 단일 타임스탬프
        ts = datetime.now(UTC)

        # 1. 기본 데이터 수집
        group = await self._collector.collect_group(group_id)
        members = await self._collector.collect_members(group_id)
        partitions = await self._collector.collect_partitions(group_id)

        # 2. 경량 구조로 변환
        partition_infos = [
            PartitionLiveInfo(
                topic=p.topic,
                partition=p.partition,
                lag=p.lag,
                committed_offset=p.committed_offset,
                latest_offset=p.latest_offset,
                assigned_member_id=p.assigned_member_id,
            )
            for p in partitions
        ]

        member_infos = [
            MemberLiveInfo(
                member_id=m.member_id,
                client_id=m.client_id,
                partition_count=len([p for p in partitions if p.assigned_member_id == m.member_id]),
            )
            for m in members
        ]

        # 3. Lag 통계
        lag_stats = LagStatsLive(
            total_lag=group.lag_stats.total_lag,
            mean_lag=group.lag_stats.mean_lag,
            p50_lag=group.lag_stats.p50_lag,
            p95_lag=group.lag_stats.p95_lag,
            max_lag=group.lag_stats.max_lag,
            partition_count=group.lag_stats.partition_count,
        )

        # 4. Fairness 계산
        fairness = self._calculator.calculate_fairness(members, partitions)

        # 5. Stuck 감지
        stuck_count = sum(1 for p in partitions if p.lag and p.lag > self.STUCK_LAG_THRESHOLD)

        # 6. 이벤트 플래그
        is_rebalancing = group.state.value == "Rebalancing"
        has_lag_spike = group.lag_stats.max_lag > self.LAG_SPIKE_THRESHOLD

        return ConsumerGroupLiveSnapshot(
            timestamp=ts,
            cluster_id=self._cluster_id,
            group_id=group_id,
            state=group.state.value,
            member_count=group.member_count,
            topic_count=group.topic_count,
            partition_assignor=group.partition_assignor.value if group.partition_assignor else None,
            lag_stats=lag_stats,
            partitions=partition_infos,
            members=member_infos,
            fairness_gini=fairness.gini_coefficient,
            stuck_count=stuck_count,
            is_rebalancing=is_rebalancing,
            has_lag_spike=has_lag_spike,
        )
