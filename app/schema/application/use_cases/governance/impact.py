"""영향도 그래프 조회 유스케이스"""

from __future__ import annotations

import logging

from app.cluster.domain.services import IConnectionManager
from app.schema.domain.models import (
    GraphLink,
    GraphNode,
    ImpactGraph,
    SubjectName,
)
from app.shared.domain.subject_utils import SubjectStrategy, extract_topics_from_subject
from app.topic.infrastructure.adapter.kafka_adapter import KafkaTopicAdapter


class GetImpactGraphUseCase:
    """영향도 그래프 조회 유스케이스"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
    ) -> None:
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)

    async def execute(self, registry_id: str, subject: SubjectName) -> ImpactGraph:
        """영향도 그래프 조회"""
        nodes: list[GraphNode] = []
        links: list[GraphLink] = []

        # 1. 중심 노드 (Schema)
        schema_node_id = f"schema:{subject}"
        nodes.append(
            GraphNode(id=schema_node_id, type="SCHEMA", label=subject, metadata={"layer": "schema"})
        )

        # 2. 토픽 추출 및 검색
        all_clusters = await self.connection_manager.kafka_cluster_repo.list_all()
        cluster_id = next((c.cluster_id for c in all_clusters if c.is_active), "default")

        repo_topics: list[str] = []
        try:
            admin_client = await self.connection_manager.get_kafka_admin_client(cluster_id)
            adapter = KafkaTopicAdapter(admin_client)
            repo_topics = await adapter.list_topics()
            if not repo_topics:
                self.logger.warning(
                    f"Cluster '{cluster_id}' returned 0 topics. Impact graph will use guesses."
                )
        except (TimeoutError, RuntimeError, ConnectionError, AttributeError, ValueError) as e:
            self.logger.error(f"Failed to list topics for cluster {cluster_id}: {e!s}")

        # 실제 매치되는 토픽 검색 (Fuzzy Match - Case Insensitive)
        sub_str = str(subject).lower()
        real_matches = [t for t in repo_topics if sub_str in t.lower()]

        if real_matches:
            found_topics = real_matches
        else:
            found_topics = extract_topics_from_subject(subject, SubjectStrategy.TOPIC_NAME)
            self.logger.debug(f"No real topics matched. Using guessed topic: {found_topics}")

        for topic in found_topics:
            t_id = f"topic:{topic}"
            nodes.append(GraphNode(id=t_id, type="TOPIC", label=topic, metadata={"layer": "topic"}))
            links.append(GraphLink(source=schema_node_id, target=t_id, relation="WRITES_TO"))

        return ImpactGraph(subject=subject, nodes=nodes, links=links)
