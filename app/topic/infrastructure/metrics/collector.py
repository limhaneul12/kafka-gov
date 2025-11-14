"""통합 메트릭 수집기 (레거시 호환 래퍼)"""

from kafka import KafkaAdminClient
from redis.asyncio import Redis

from app.topic.domain.repositories.metrics_interfaces import IMetricsRepository
from app.topic.infrastructure.adapter.metrics.collector import (
    TopicMetricsCollector as AdapterCollector,
)


class TopicMetricsCollector(AdapterCollector, IMetricsRepository):
    """AdapterCollector를 래핑하여 기존 import 경로와 인터페이스를 유지합니다."""

    def __init__(
        self,
        admin_client: KafkaAdminClient,
        cluster_id: str,
        ttl_seconds: int = 15,
        redis: Redis | None = None,
    ) -> None:
        super().__init__(
            admin_client=admin_client,
            cluster_id=cluster_id,
            ttl_seconds=ttl_seconds,
            redis=redis,
        )
