"""영향도 그래프 조회 유스케이스"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from app.cluster.domain.services import IConnectionManager
from app.consumer.application.use_cases.query import GetTopicConsumersUseCase
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
        get_topic_consumers_use_case: GetTopicConsumersUseCase,
    ) -> None:
        self.connection_manager = connection_manager
        self.get_topic_consumers_use_case = get_topic_consumers_use_case
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

        # 실제 매칭이 있으면 그것만, 없으면 명명 규칙으로 추측
        active_real_matches = []
        if real_matches:
            try:
                # 메시지 존재 여부 확인을 위해 log_dir 사이즈 체크 (kafka-python 사용)
                py_admin = await self.connection_manager.get_kafka_py_admin_client(cluster_id)
                response = await asyncio.to_thread(py_admin.describe_log_dirs)

                # 토픽별 사이즈 맵 생성
                topic_size_map = {}
                log_dir_entries = getattr(response, "log_dirs", [])
                for entry in log_dir_entries:
                    if entry[0] != 0:
                        continue  # 에러 발생한 디렉토리 스킵
                    for topic_data in entry[2]:
                        t_name = topic_data[0]
                        if t_name not in real_matches:
                            continue
                        total_size = sum(p[1] for p in topic_data[1])
                        topic_size_map[t_name] = topic_size_map.get(t_name, 0) + total_size

                # 필터링: 메시지가 있거나(size > 0) 컨슈머가 붙어있는 토픽만 유지
                for topic in real_matches:
                    # 1. 컨슈머 체크
                    c_mapping = None
                    with contextlib.suppress(Exception):
                        c_mapping = await self.get_topic_consumers_use_case.execute(
                            cluster_id, topic
                        )

                    has_consumers = bool(c_mapping and c_mapping.consumer_groups)
                    has_data = topic_size_map.get(topic, 0) > 0

                    if has_data or has_consumers:
                        active_real_matches.append(topic)
                        self.logger.debug(
                            f"Topic '{topic}' is active (data={has_data}, consumers={has_consumers})."
                        )
                    else:
                        self.logger.debug(
                            f"Topic '{topic}' is inactive (0 bytes, 0 consumers). Excluding from graph."
                        )

                found_topics = (
                    active_real_matches if active_real_matches else real_matches[:1]
                )  # 다 비었으면 최소 하나는 보여줌
            except Exception as e:
                self.logger.error(f"Failed to check topic activity: {e}")
                found_topics = real_matches
        else:
            found_topics = extract_topics_from_subject(subject, SubjectStrategy.TOPIC_NAME)
            self.logger.debug(f"No real topics matched. Using guessed topic: {found_topics}")

        for topic in found_topics:
            consumer_mapping = None
            with contextlib.suppress(Exception):
                consumer_mapping = await self.get_topic_consumers_use_case.execute(
                    cluster_id, topic
                )

            t_id = f"topic:{topic}"
            nodes.append(GraphNode(id=t_id, type="TOPIC", label=topic, metadata={"layer": "topic"}))
            links.append(GraphLink(source=schema_node_id, target=t_id, relation="WRITES_TO"))

            if consumer_mapping and consumer_mapping.consumer_groups:
                # 중복되지 않은 신규 컨슈머 그룹 추출
                seen_ids = {n.id for n in nodes}
                new_groups = [
                    g
                    for g in consumer_mapping.consumer_groups
                    if f"consumer:{g['group_id']}" not in seen_ids
                ]

                nodes.extend(
                    [
                        GraphNode(
                            id=f"consumer:{g['group_id']}",
                            type="CONSUMER",
                            label=g["group_id"],
                            metadata={
                                "layer": "app",
                                "state": g.get("state", "unknown"),
                                "members": g.get("member_count", 0),
                            },
                        )
                        for g in new_groups
                    ]
                )

                links.extend(
                    [
                        GraphLink(
                            source=t_id, target=f"consumer:{g['group_id']}", relation="READS_FROM"
                        )
                        for g in consumer_mapping.consumer_groups
                    ]
                )
            elif not real_matches:
                self.logger.debug(f"Guessed topic {topic} has no active consumers.")

        return ImpactGraph(subject=subject, nodes=nodes, links=links)
