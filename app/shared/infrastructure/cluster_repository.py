"""Shared Infrastructure - Kafka Cluster Repository"""

from __future__ import annotations

import logging

from confluent_kafka.admin import AdminClient

from app.shared.domain.models import BrokerInfo, ClusterStatus
from app.shared.domain.repositories import IClusterRepository

logger = logging.getLogger(__name__)


class KafkaClusterRepository(IClusterRepository):
    """Kafka 클러스터 정보 리포지토리 (AdminClient 기반)"""

    def __init__(self, admin_client: AdminClient) -> None:
        self.admin_client = admin_client

    async def get_cluster_status(self) -> ClusterStatus:
        """Kafka 클러스터 상태 조회"""
        try:
            # 클러스터 메타데이터 조회
            metadata = self.admin_client.list_topics(timeout=10)

            # 컨트롤러 ID 조회
            controller_id = metadata.controller_id

            # 브로커 정보 수집
            brokers: list[BrokerInfo] = [
                BrokerInfo(
                    broker_id=broker.id,
                    host=broker.host,
                    port=broker.port,
                    is_controller=(broker.id == controller_id),
                    leader_partition_count=sum(
                        1
                        for topic in metadata.topics.values()
                        for partition in topic.partitions.values()
                        if partition.leader == broker.id
                    ),
                    disk_usage_bytes=None,
                )
                for broker in metadata.brokers.values()
            ]

            # 전체 토픽/파티션 수 계산
            total_topics: int = len(metadata.topics)
            total_partitions: int = sum(len(topic.partitions) for topic in metadata.topics.values())

            # ClusterStatus 생성
            return ClusterStatus(
                cluster_id=metadata.cluster_id or "unknown",
                controller_id=controller_id,
                brokers=tuple(sorted(brokers, key=lambda b: b.broker_id)),
                total_topics=total_topics,
                total_partitions=total_partitions,
            )

        except Exception as e:
            logger.error(f"Failed to get cluster status: {e}")
            raise
