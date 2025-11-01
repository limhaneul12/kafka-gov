"""Kafka 메트릭 수집 Adapter

사용 방법 (다른 모듈에서):
    ```python
    from app.container import AppContainer
    from app.topic.infrastructure.adapter.metrics.collector import TopicMetricsCollector

    async def example(cluster_id: str):
        # cluster_id로 kafka-python KafkaAdminClient 동적 획득
        connection_manager = AppContainer.cluster_container.connection_manager()
        admin_client = await connection_manager.get_kafka_py_admin_client(cluster_id)

        # 수집기 생성 및 사용
        collector = TopicMetricsCollector(admin_client=admin_client, ttl_seconds=60)
        await collector.refresh()
        metrics = await collector.get_all_topic_metrics()
        leader = await collector.get_leader_distribution()
        return metrics, leader
    ```
"""

import asyncio
import time
from collections.abc import Iterable
from typing import Any

from kafka import KafkaAdminClient

from app.topic.domain.models.metrics import (
    ClusterMetrics,
    PartitionDetails,
    TopicMeta,
    TopicMetrics,
)


class BaseMetricsCollector:
    """공통 메트릭 수집 기반 클래스"""

    def __init__(self, admin_client: KafkaAdminClient, ttl_seconds: int = 15) -> None:
        self.ttl_seconds = ttl_seconds
        self.admin = admin_client
        self._snapshot: TopicMetrics | None = None
        self._snapshot_time: float | None = None

    async def refresh(self) -> None:
        """스냅샷 강제 갱신."""
        self._snapshot = await self._collect_all_partition_info()
        self._snapshot_time = time.time()

    def _is_snapshot_expired(self) -> bool:
        """스냅샷 만료 여부 확인"""
        if self._snapshot_time is None:
            return True
        return time.time() - self._snapshot_time > self.ttl_seconds

    async def _get_snapshot(self) -> TopicMetrics | None:
        if self._snapshot is None or self._is_snapshot_expired():
            await self.refresh()
        return self._snapshot

    async def _collect_all_partition_info(self) -> TopicMetrics:
        """모든 파티션 정보 수집"""
        # 1. 클러스터 정보 가져오기 (비동기)
        cluster_metadata = await asyncio.to_thread(self.admin.describe_cluster)
        broker_count = len(cluster_metadata["brokers"])

        # 2. 토픽 목록 및 메타데이터 가져오기 (비동기)
        topic_names = await asyncio.to_thread(self.admin.list_topics)
        topics_metadata = await asyncio.to_thread(self.admin.describe_topics, topic_names)

        # 3. 로그 디렉토리 정보 가져오기 (비동기)
        log_dirs_response = await asyncio.to_thread(self.admin.describe_log_dirs)
        log_dir_entries: Iterable[Any] = getattr(log_dirs_response, "log_dirs", []) or []

        # 4. 로그 디렉토리 정보 평탄화 (빠른 조회용)
        log_dir_map = {}
        for log_dir in log_dir_entries:
            if log_dir[0] != 0:  # error_code check
                continue
            for topic_info in log_dir[2]:
                topic_name = topic_info[0]
                for partition_info in topic_info[1]:
                    partition_id = partition_info[0]
                    log_dir_map[(topic_name, partition_id)] = {
                        "size": partition_info[1],
                        "offset_lag": partition_info[2],
                        "is_future_key": partition_info[3],
                    }

        topic_meta = {
            topic_metadata["topic"]: TopicMeta(
                partition_details=[
                    PartitionDetails(
                        partition_index=partition["partition"],
                        partition_size=log_dir_map.get(
                            (topic_metadata["topic"], partition["partition"]), {}
                        ).get("size", 0),
                        offset_lag=log_dir_map.get(
                            (topic_metadata["topic"], partition["partition"]), {}
                        ).get("offset_lag", 0),
                        is_future_key=log_dir_map.get(
                            (topic_metadata["topic"], partition["partition"]), {}
                        ).get("is_future_key", False),
                        # 복제 정보 추가
                        leader=partition["leader"],
                        replicas=partition["replicas"],
                        isr=partition["isr"],
                    )
                    for partition in topic_metadata["partitions"]
                ]
            )
            for topic_metadata in topics_metadata
        }

        total_partition_count = sum(len(meta.partition_details) for meta in topic_meta.values())

        # 6. 클러스터 지표 생성
        cluster_metrics = ClusterMetrics(
            broker_count=broker_count,
            total_partition_count=total_partition_count,
            topics=topic_meta,
        )

        # 7. 로그 디렉토리 정보
        log_dir = next(
            (log_dir_info[1] for log_dir_info in log_dir_entries if log_dir_info[0] == 0),
            "",
        )

        return TopicMetrics(log_dir=log_dir, topic_meta=topic_meta, cluster_metrics=cluster_metrics)

    async def _get_topic_partitions(self, topic_name: str) -> list[PartitionDetails]:
        """토픽의 파티션 정보를 가져오는 헬퍼 메서드"""
        metrics = await self._get_snapshot()
        if not metrics or topic_name not in metrics.topic_meta:
            return []
        return metrics.topic_meta[topic_name].partition_details
