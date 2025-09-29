"""Kafka AdminClient 어댑터 - 얇은 래퍼 구현"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from confluent_kafka.admin import AdminClient, ConfigResource, NewPartitions, NewTopic

from ..domain.models import DomainTopicSpec, TopicName
from ..domain.repositories.interfaces import ITopicRepository

logger = logging.getLogger(__name__)
TopicMetadata = dict[TopicName, Exception | None]
TopicConfig = dict[TopicName, dict[str, str]]
TopicPartitions = dict[TopicName, int]


class KafkaTopicAdapter(ITopicRepository):
    """Kafka AdminClient 어댑터"""

    def __init__(self, admin_client: AdminClient) -> None:
        self.admin_client = admin_client

    async def get_topic_metadata(self, name: TopicName) -> dict[str, Any] | None:
        """토픽 메타데이터 조회"""
        try:
            topics = await self.describe_topics([name])
            return topics.get(name)
        except Exception as e:
            logger.error(f"Failed to get topic metadata for {name}: {e}")
            return None

    async def create_topics(self, specs: list[DomainTopicSpec]) -> TopicMetadata:
        """토픽 생성"""
        if not specs:
            return {}

        # NewTopic 객체 생성
        new_topics = []
        for spec in specs:
            if not spec.config:
                continue

            new_topic = NewTopic(
                topic=spec.name,
                num_partitions=spec.config.partitions,
                replication_factor=spec.config.replication_factor,
                config=spec.config.to_kafka_config(),
            )
            new_topics.append(new_topic)

        if not new_topics:
            return {}

        try:
            # 비동기 실행
            futures = self.admin_client.create_topics(
                new_topics,
                operation_timeout=30.0,
                request_timeout=60.0,
            )

            # 결과 대기
            results = {}
            for topic_name, future in futures.items():
                try:
                    await asyncio.get_event_loop().run_in_executor(None, future.result, 30.0)
                    results[topic_name] = None  # 성공
                    logger.info(f"Successfully created topic: {topic_name}")
                except Exception as e:
                    results[topic_name] = e
                    logger.error(f"Failed to create topic {topic_name}: {e}")

            return results

        except Exception as e:
            logger.error(f"Failed to create topics: {e}")
            # 모든 토픽에 대해 동일한 에러 반환
            return {spec.name: e for spec in specs}

    async def delete_topics(self, names: list[TopicName]) -> TopicMetadata:
        """토픽 삭제"""
        if not names:
            return {}

        try:
            # 비동기 실행
            futures = self.admin_client.delete_topics(
                names,
                operation_timeout=30.0,
                request_timeout=60.0,
            )

            # 결과 대기
            results = {}
            for topic_name, future in futures.items():
                try:
                    await asyncio.get_event_loop().run_in_executor(None, future.result, 30.0)
                    results[topic_name] = None  # 성공
                    logger.info(f"Successfully deleted topic: {topic_name}")
                except Exception as e:
                    results[topic_name] = e
                    logger.error(f"Failed to delete topic {topic_name}: {e}")

            return results

        except Exception as e:
            logger.error(f"Failed to delete topics: {e}")
            # 모든 토픽에 대해 동일한 에러 반환
            return dict.fromkeys(names, e)

    async def alter_topic_configs(self, configs: TopicConfig) -> TopicMetadata:
        """토픽 설정 변경"""
        if not configs:
            return {}

        try:
            # ConfigResource 객체 생성
            resources = []
            for topic_name, config in configs.items():
                resource = ConfigResource(ConfigResource.Type.TOPIC, topic_name)
                resources.append((resource, config))

            # 비동기 실행
            futures = self.admin_client.alter_configs(resources, request_timeout=60.0)

            # 결과 대기
            results = {}
            for resource, future in futures.items():
                # Confluent returns keys as ConfigResource; tests may mock with strings
                topic_name = getattr(resource, "name", None)
                if topic_name is None:
                    topic_name = str(resource)
                    if ":" in topic_name:
                        # e.g., "TOPIC:dev.user.events" -> "dev.user.events"
                        topic_name = topic_name.split(":", 1)[1]
                try:
                    await asyncio.get_event_loop().run_in_executor(None, future.result, 30.0)
                    results[topic_name] = None  # 성공
                    logger.info(f"Successfully altered config for topic: {topic_name}")
                except Exception as e:
                    results[topic_name] = e
                    logger.error(f"Failed to alter config for topic {topic_name}: {e}")

            return results

        except Exception as e:
            logger.error(f"Failed to alter topic configs: {e}")
            # 모든 토픽에 대해 동일한 에러 반환
            return dict.fromkeys(configs.keys(), e)

    async def create_partitions(self, partitions: TopicPartitions) -> TopicMetadata:
        """파티션 수 증가"""
        if not partitions:
            return {}

        try:
            # NewPartitions 객체 생성
            partition_updates = [
                NewPartitions(topic=topic_name, new_total_count=partition_count)
                for topic_name, partition_count in partitions.items()
            ]

            # 비동기 실행
            futures = self.admin_client.create_partitions(
                partition_updates, operation_timeout=30.0, request_timeout=60.0
            )

            # 결과 대기
            results: TopicMetadata = {}
            for topic_name, future in futures.items():
                try:
                    await asyncio.get_event_loop().run_in_executor(None, future.result, 30.0)
                    results[topic_name] = None  # 성공
                    logger.info(f"Successfully created partitions for topic: {topic_name}")
                except Exception as e:
                    results[topic_name] = e
                    logger.error(f"Failed to create partitions for topic {topic_name}: {e}")

            return results

        except Exception as e:
            logger.error(f"Failed to create partitions: {e}")
            # 모든 토픽에 대해 동일한 에러 반환
            return dict.fromkeys(partitions.keys(), e)

    async def describe_topics(self, names: list[TopicName]) -> dict[TopicName, dict[str, Any]]:
        """토픽 상세 정보 조회"""
        if not names:
            return {}

        try:
            # 클러스터 메타데이터 조회
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, self.admin_client.list_topics, 60.0
            )

            results: dict[TopicName, dict[str, Any]] = {}
            for name in names:
                topic_metadata = metadata.topics.get(name)
                if topic_metadata is None:
                    continue

                # 토픽 설정 조회
                config_resource = ConfigResource(ConfigResource.Type.TOPIC, name)
                config_futures = self.admin_client.describe_configs([config_resource])

                try:
                    config_result = await asyncio.get_event_loop().run_in_executor(
                        None, config_futures[config_resource].result, 30.0
                    )

                    # 설정을 딕셔너리로 변환
                    config_dict = {entry.name: entry.value for entry in config_result.values()}

                    results[name] = {
                        "partition_count": len(topic_metadata.partitions),
                        "replication_factor": (
                            len(topic_metadata.partitions[0].replicas)
                            if topic_metadata.partitions
                            else 0
                        ),
                        "config": config_dict,
                        "partitions": [
                            {
                                "id": p.id,
                                "leader": p.leader,
                                "replicas": p.replicas,
                                "isrs": p.isrs,
                            }
                            for p in topic_metadata.partitions.values()
                        ],
                    }

                except Exception as e:
                    logger.error(f"Failed to get config for topic {name}: {e}")
                    # 기본 정보만 반환
                    results[name] = {
                        "partition_count": len(topic_metadata.partitions),
                        "replication_factor": (
                            len(topic_metadata.partitions[0].replicas)
                            if topic_metadata.partitions
                            else 0
                        ),
                        "config": {},
                        "partitions": [],
                    }

            return results

        except Exception as e:
            logger.error(f"Failed to describe topics: {e}")
            return {}


def create_kafka_admin_client(bootstrap_servers: str, **config) -> AdminClient:
    """Kafka AdminClient 생성"""
    admin_config = {
        "bootstrap.servers": bootstrap_servers,
        "request.timeout.ms": 60000,
        "socket.timeout.ms": 60000,
        **config,
    }

    return AdminClient(admin_config)
