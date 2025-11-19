"""Kafka 메트릭 수집 Adapter (Redis 멀티워커 캐싱 지원)

2단계 캐싱 전략:
    - L1 (메모리): 프로세스 내 빠른 조회, TTL 기반
    - L2 (Redis): 워커 간 공유, 중복 Kafka 호출 방지

사용 방법 (DI Container를 통한 주입):
    ```python
    from app.container import AppContainer

    async def example(cluster_id: str):
        # ConnectionManager를 통해 AdminClient 획득
        connection_manager = AppContainer.cluster_container.connection_manager()
        admin_client = await connection_manager.get_kafka_py_admin_client(cluster_id)

        # Factory를 통해 Collector 생성 (Redis 자동 주입)
        metrics_collector_factory = AppContainer.topic_container.metrics_collector()
        collector = metrics_collector_factory(
            admin_client=admin_client,
            cluster_id=cluster_id,
        )

        # 자동으로 L1 → L2 → Kafka 순서로 조회
        metrics = await collector.get_all_topic_metrics()
        return metrics
    ```
"""

import asyncio
import pickle
import time
from collections.abc import Iterable
from typing import Any

from kafka import KafkaAdminClient
from redis.asyncio import Redis

from app.topic.domain.models.metrics import (
    ClusterMetrics,
    PartitionDetails,
    TopicMeta,
    TopicMetrics,
)


class BaseMetricsCollector:
    """공통 메트릭 수집 기반 클래스"""

    def __init__(
        self,
        admin_client: KafkaAdminClient,
        cluster_id: str,
        ttl_seconds: int = 15,
        redis: Redis | None = None,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.admin = admin_client
        self.cluster_id = cluster_id
        self.redis = redis

        # L1 캐시 (메모리) - 인스턴스별 독립
        self._snapshot: TopicMetrics | None = None
        self._snapshot_time: float | None = None

    def _get_redis_key(self) -> str:
        """Redis 캐시 키 생성"""
        return f"metrics:cluster:{self.cluster_id}:snapshot"

    async def refresh(self) -> None:
        """스냅샷 강제 갱신 (L1 + L2 업데이트)"""
        self._snapshot = await self._collect_all_partition_info()
        self._snapshot_time = time.time()

        # L2: Redis 저장 (워커 간 공유)
        if self.redis and self.ttl_seconds > 0:
            key = self._get_redis_key()
            value = pickle.dumps(self._snapshot)
            await self.redis.setex(key, self.ttl_seconds, value)

    def _is_snapshot_expired(self) -> bool:
        """스냅샷 만료 여부 확인"""
        if self._snapshot_time is None:
            return True
        return time.time() - self._snapshot_time > self.ttl_seconds

    async def _get_snapshot(self) -> TopicMetrics | None:
        """2단계 캐시 조회: L1(메모리) → L2(Redis) → Kafka"""

        # L1: 메모리 캐시 (가장 빠름)
        if self._snapshot is not None and not self._is_snapshot_expired():
            return self._snapshot

        # L2: Redis 캐시 (워커 간 공유)
        if self.redis:
            key = self._get_redis_key()
            cached = await self.redis.get(key)
            if cached:
                self._snapshot = pickle.loads(cached)
                self._snapshot_time = time.time()
                return self._snapshot

        # 캐시 미스: Kafka에서 수집
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

        # 4. 로그 디렉토리 정보 평탄화 (comprehension 활용)
        log_dir_map = {
            (topic_info[0], partition_info[0]): {
                "size": partition_info[1],
                "offset_lag": partition_info[2],
                "is_future_key": partition_info[3],
            }
            for log_dir in log_dir_entries
            if log_dir[0] == 0  # error_code check
            for topic_info in log_dir[2]
            for partition_info in topic_info[1]
        }

        topic_meta: dict[str, TopicMeta] = {
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
