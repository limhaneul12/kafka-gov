"""통합 메트릭 수집기 (레거시 호환 래퍼)"""

from kafka import KafkaAdminClient

from app.topic.domain.repositories.metrics_interfaces import IMetricsRepository
from app.topic.infrastructure.adapter.metrics.collector import (
    TopicMetricsCollector as AdapterCollector,
)


class TopicMetricsCollector(AdapterCollector, IMetricsRepository):
    """AdapterCollector를 래핑하여 기존 import 경로와 인터페이스를 유지합니다."""

    def __init__(self, admin_client: KafkaAdminClient, ttl_seconds: int = 15) -> None:
        super().__init__(admin_client=admin_client, ttl_seconds=ttl_seconds)
