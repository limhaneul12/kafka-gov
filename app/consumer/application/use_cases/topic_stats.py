"""Consumer Group Topic Statistics Use Case

토픽별 집계 통계 조회
"""

from collections import defaultdict
from collections.abc import Awaitable, Callable

from confluent_kafka.admin import AdminClient

from app.consumer.domain.services import ConsumerDataCollector
from app.consumer.infrastructure.kafka_consumer_adapter import KafkaConsumerAdapter
from app.consumer.interface.schema.topic_stats_schema import (
    GroupTopicStatsResponse,
    TopicStatsResponse,
)


class GetGroupTopicStatsUseCase:
    """Consumer Group 토픽별 통계 Use Case - Backend에서 집계"""

    def __init__(self, admin_client_getter: Callable[[str], Awaitable[AdminClient]]) -> None:
        """Use case 생성자

        Args:
            admin_client_getter: cluster_id로 AdminClient를 가져오는 async 함수
        """
        self._admin_client_getter = admin_client_getter

    async def execute(self, cluster_id: str, group_id: str) -> GroupTopicStatsResponse:
        """토픽별 집계 통계 조회 - Backend에서 계산

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID

        Returns:
            GroupTopicStatsResponse: 토픽별 통계 (lag 내림차순)

        Raises:
            ValueError: AdminClient를 찾을 수 없거나 그룹이 존재하지 않음
        """
        # 1. AdminClient 및 Adapter 생성
        admin_client = await self._admin_client_getter(cluster_id)

        adapter = KafkaConsumerAdapter(admin_client)
        collector = ConsumerDataCollector(adapter, cluster_id)

        # 2. 실시간 Kafka 조회 - 파티션 데이터
        try:
            partitions = await collector.collect_partitions(group_id)
        except KeyError as e:
            raise ValueError(f"Consumer group not found: {group_id}") from e

        # 3. 토픽별로 집계 (Backend에서 계산)
        topic_map: dict[str, list[int]] = defaultdict(list)
        total_lag = 0

        for partition in partitions:
            lag = partition.lag or 0
            topic_map[partition.topic].append(lag)
            total_lag += lag

        # 4. 토픽별 통계 계산
        topic_stats: list[TopicStatsResponse] = []

        for topic, lags in topic_map.items():
            topic_total_lag = sum(lags)
            topic_stats.append(
                TopicStatsResponse(
                    topic=topic,
                    partition_count=len(lags),
                    total_lag=topic_total_lag,
                    avg_lag=topic_total_lag / len(lags) if lags else 0.0,
                    max_lag=max(lags) if lags else 0,
                    lag_share=topic_total_lag / total_lag if total_lag > 0 else 0.0,
                )
            )

        # 5. Total Lag 내림차순 정렬
        topic_stats.sort(key=lambda x: x.total_lag, reverse=True)

        return GroupTopicStatsResponse(
            group_id=group_id,
            cluster_id=cluster_id,
            total_lag=total_lag,
            topic_stats=topic_stats,
        )
