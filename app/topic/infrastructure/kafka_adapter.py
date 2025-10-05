"""Kafka AdminClient 어댑터 - 얇은 래퍼 구현"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from functools import partial
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

    async def _wait_for_futures(
        self,
        futures: dict[Any, Any],
        operation: str,
        key_extractor: Callable[[Any], str] | None = None,
    ) -> TopicMetadata:
        """Kafka AdminClient의 future 결과를 대기하고 처리

        Args:
            futures: AdminClient가 반환한 futures 딕셔너리
            operation: 작업 이름 (로깅용)
            key_extractor: future dict의 키에서 토픽 이름을 추출하는 함수 (기본: str 변환)

        Returns:
            TopicMetadata: {topic_name: None (성공) | Exception (실패)}
        """
        results: TopicMetadata = {}

        for key, future in futures.items():
            # 토픽 이름 추출
            topic_name = key_extractor(key) if key_extractor else str(key)

            try:
                await asyncio.get_event_loop().run_in_executor(None, future.result, 30.0)
                results[topic_name] = None  # 성공
                logger.info(f"Successfully {operation} topic: {topic_name}")
            except Exception as e:
                results[topic_name] = e
                logger.error(f"Failed to {operation} topic {topic_name}: {e}")

        return results

    async def _execute_kafka_operation(
        self,
        futures: dict[Any, Any],
        operation: str,
        fallback_keys: list[str] | dict,
        key_extractor: Callable[[Any], str] | None = None,
    ) -> TopicMetadata:
        """Kafka 작업 실행 및 에러 핸들링

        Args:
            futures: AdminClient가 반환한 futures 딕셔너리
            operation: 작업 이름 (로깅용)
            fallback_keys: 에러 발생 시 반환할 키 목록 (list 또는 dict)
            key_extractor: future dict의 키에서 토픽 이름을 추출하는 함수

        Returns:
            TopicMetadata: {topic_name: None (성공) | Exception (실패)}
        """
        try:
            return await self._wait_for_futures(futures, operation, key_extractor)
        except Exception as e:
            logger.error(f"Failed to {operation} topics: {e}")
            # 모든 토픽에 대해 동일한 에러 반환
            if isinstance(fallback_keys, dict):
                return dict.fromkeys(fallback_keys.keys(), e)
            return dict.fromkeys(fallback_keys, e)

    async def list_topics(self) -> list[TopicName]:
        """모든 토픽 목록 조회"""
        try:
            # 클러스터 메타데이터 조회
            # list_topics(topic=None, timeout=-1) - 첫 번째 인자는 topic(str or None), 두 번째가 timeout
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, partial(self.admin_client.list_topics, timeout=30.0)
            )

            # 내부 토픽 제외 (__ 로 시작하는 토픽)
            topics = [topic for topic in metadata.topics if not topic.startswith("__")]

            logger.info(f"Retrieved {len(topics)} topics from Kafka")
            return topics
        except Exception as e:
            logger.error(f"Failed to list topics: {e}")
            raise RuntimeError(f"Failed to retrieve topics: {e}") from e

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
        new_topics: list[NewTopic] = [
            NewTopic(
                topic=spec.name,
                num_partitions=spec.config.partitions,
                replication_factor=spec.config.replication_factor,
                config=spec.config.to_kafka_config(),
            )
            for spec in specs
            if spec.config
        ]

        if not new_topics:
            return {}

        # 비동기 실행
        futures: dict = self.admin_client.create_topics(
            new_topics,
            operation_timeout=30.0,
            request_timeout=60.0,
        )

        # 결과 대기
        return await self._execute_kafka_operation(
            futures=futures,
            operation="created",
            fallback_keys=[spec.name for spec in specs],
        )

    async def delete_topics(self, names: list[TopicName]) -> TopicMetadata:
        """토픽 삭제"""
        if not names:
            return {}

        # 비동기 실행
        futures: dict = self.admin_client.delete_topics(
            names, operation_timeout=30.0, request_timeout=60.0
        )

        # 결과 대기
        return await self._execute_kafka_operation(
            futures=futures,
            operation="deleted",
            fallback_keys=names,
        )

    async def alter_topic_configs(self, configs: TopicConfig) -> TopicMetadata:
        """토픽 설정 변경"""
        if not configs:
            return {}

        # ConfigResource 객체 생성
        resources: list[tuple[ConfigResource, dict[str, str]]] = [
            (ConfigResource(ConfigResource.Type.TOPIC, topic_name), config)
            for topic_name, config in configs.items()
        ]

        # 비동기 실행
        futures: dict = self.admin_client.alter_configs(resources, request_timeout=60.0)

        # ConfigResource에서 토픽 이름 추출 함수
        def extract_topic_name(resource: Any) -> str:
            # Confluent returns keys as ConfigResource; tests may mock with strings
            if topic_name := getattr(resource, "name", None):
                return topic_name
            # Mock string format: "TOPIC:dev.user.events" -> "dev.user.events"
            return str(resource).split(":", 1)[1] if ":" in str(resource) else str(resource)

        # 결과 대기
        return await self._execute_kafka_operation(
            futures=futures,
            operation="altered config for",
            fallback_keys=configs,
            key_extractor=extract_topic_name,
        )

    async def create_partitions(self, partitions: TopicPartitions) -> TopicMetadata:
        """파티션 수 증가"""
        if not partitions:
            return {}

        # NewPartitions 객체 생성
        partition_updates: list[NewPartitions] = [
            NewPartitions(topic=topic_name, new_total_count=partition_count)
            for topic_name, partition_count in partitions.items()
        ]

        # 비동기 실행
        futures: dict = self.admin_client.create_partitions(
            partition_updates,
            operation_timeout=30.0,
            request_timeout=60.0,
        )

        # 결과 대기
        return await self._execute_kafka_operation(
            futures=futures,
            operation="created partitions for",
            fallback_keys=partitions,
        )

    async def describe_topics(self, names: list[TopicName]) -> dict[TopicName, dict[str, Any]]:
        """토픽 상세 정보 조회"""
        if not names:
            return {}

        try:
            # 클러스터 메타데이터 조회
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, partial(self.admin_client.list_topics, timeout=60.0)
            )
            logger.debug(f"Metadata for topics {names}: {metadata}")

            results: dict[TopicName, dict[str, Any]] = {}
            for name in names:
                topic_metadata = metadata.topics.get(name)
                if topic_metadata is None:
                    continue

                # 토픽 설정 조회
                config_resource = ConfigResource(ConfigResource.Type.TOPIC, name)
                config_futures = self.admin_client.describe_configs([config_resource])
                logger.info("config_futures: %s", config_futures)

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
                    # 토픽이 조회 중 삭제되었거나 권한이 없는 경우
                    error_str = str(e)
                    if "UNKNOWN_TOPIC_OR_PART" in error_str:
                        logger.warning(
                            f"Topic {name} was deleted or is inaccessible during config fetch. "
                            "Returning basic metadata only."
                        )
                    else:
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
