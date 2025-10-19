"""토픽 목록 조회 유스케이스"""

from __future__ import annotations

import logging
from typing import Any

from app.cluster.domain.services import IConnectionManager
from app.topic.infrastructure.kafka_adapter import KafkaTopicAdapter

from ...domain.models import TopicName
from ...domain.repositories.interfaces import ITopicMetadataRepository

KafkaMetaDescription = dict[TopicName, dict[str, Any]]
TopicDescription = list[dict[str, Any]]


class TopicListUseCase:
    """토픽 목록 조회 유스케이스 (멀티 클러스터 지원)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ITopicMetadataRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository

    async def execute(self, cluster_id: str) -> TopicDescription:
        """토픽 목록 조회"""
        # 1. ConnectionManager로 AdminClient 획득
        admin_client = await self.connection_manager.get_kafka_admin_client(cluster_id)

        # 2. Adapter 생성
        topic_repository = KafkaTopicAdapter(admin_client)

        # 3. Kafka에서 모든 토픽 이름 조회
        all_topics: list[TopicName] = await topic_repository.list_topics()

        # 4. Kafka에서 모든 토픽 상세 정보 배치 조회 (파티션수, 복제개수)
        topic_details: KafkaMetaDescription = await topic_repository.describe_topics(all_topics)

        # 3. DB 메타데이터와 Kafka 정보를 병합
        topics_with_metadata: TopicDescription = []
        for topic_name in all_topics:
            metadata = await self.metadata_repository.get_topic_metadata(topic_name)
            kafka_info = topic_details.get(topic_name, {})

            owner = metadata.get("owner") if metadata else None
            doc = metadata.get("doc") if metadata else None
            tags = metadata.get("tags", []) if metadata else []
            # metadata에서 environment 가져오기, 없으면 토픽명에서 추론
            environment = metadata.get("environment") if metadata else None
            if not environment:
                environment = self._infer_environment(topic_name)

            logger = logging.getLogger(__name__)
            logger.debug(
                f"[{cluster_id}] Topic {topic_name}: owner={owner}, doc={doc}, tags={tags}, env={environment}"
            )

            topics_with_metadata.append(
                {
                    "name": topic_name,
                    "owner": owner,
                    "doc": doc,
                    "tags": tags,
                    "partition_count": kafka_info.get("partition_count"),
                    "replication_factor": kafka_info.get("replication_factor"),
                    "environment": environment,
                }
            )

        return topics_with_metadata

    @staticmethod
    def _infer_environment(topic_name: str) -> str:
        """토픽 이름에서 환경 추론"""
        if topic_name.startswith("dev."):
            return "dev"
        if topic_name.startswith("stg."):
            return "stg"
        if topic_name.startswith("prod."):
            return "prod"
        return "unknown"
