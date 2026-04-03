from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from functools import partial
from typing import Any

from confluent_kafka.admin import AdminClient, ConfigResource, NewPartitions, NewTopic

from app.shared.logging_config import get_logger
from app.topic.domain.models import DomainTopicSpec, TopicName
from app.topic.domain.repositories.interfaces import ITopicRepository

logger = get_logger(__name__)
TopicMetadata = dict[TopicName, Exception | None]
TopicConfig = dict[TopicName, dict[str, str]]
TopicPartitions = dict[TopicName, int]


class KafkaTopicAdapter(ITopicRepository):
    def __init__(self, admin_client: AdminClient) -> None:
        self.admin_client: AdminClient = admin_client

    async def _wait_for_futures(
        self,
        futures: dict[Any, Any],
        operation: str,
        key_extractor: Callable[[Any], str] | None = None,
    ) -> TopicMetadata:
        results: TopicMetadata = {}

        for key, future in futures.items():
            topic_name = key_extractor(key) if key_extractor else str(key)

            try:
                await asyncio.get_event_loop().run_in_executor(None, future.result, 30.0)
                results[topic_name] = None
                logger.info(
                    "kafka_operation_success",
                    operation=operation,
                    topic_name=topic_name,
                )
            except Exception as e:
                results[topic_name] = e
                logger.error(
                    "kafka_operation_failed",
                    operation=operation,
                    topic_name=topic_name,
                    error_type=e.__class__.__name__,
                    error_message=str(e),
                )

        return results

    async def _execute_kafka_operation(
        self,
        futures: dict[Any, Any],
        operation: str,
        fallback_keys: list[str] | Mapping[TopicName, object],
        key_extractor: Callable[[Any], str] | None = None,
    ) -> TopicMetadata:
        try:
            return await self._wait_for_futures(futures, operation, key_extractor)
        except Exception as e:
            logger.error(f"Failed to {operation} topics: {e}")
            if isinstance(fallback_keys, dict):
                return dict.fromkeys(fallback_keys.keys(), e)
            return dict.fromkeys(fallback_keys, e)

    async def list_topics(self) -> list[TopicName]:
        try:
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, partial(self.admin_client.list_topics, timeout=30.0)
            )
            topics = [topic for topic in metadata.topics if not topic.startswith("__")]
            logger.info(f"Retrieved {len(topics)} topics from Kafka")
            return topics
        except Exception as e:
            logger.error(f"Failed to list topics: {e}")
            raise RuntimeError(f"Failed to retrieve topics: {e}") from e

    async def get_topic_metadata(self, name: TopicName) -> dict[str, Any] | None:
        try:
            topics = await self.describe_topics([name])
            return topics.get(name)
        except Exception as e:
            logger.error(f"Failed to get topic metadata for {name}: {e}")
            return None

    async def create_topics(self, specs: list[DomainTopicSpec]) -> TopicMetadata:
        if not specs:
            return {}

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

        futures: dict[Any, Any] = self.admin_client.create_topics(
            new_topics,
            operation_timeout=30.0,
            request_timeout=60.0,
        )

        return await self._execute_kafka_operation(
            futures=futures,
            operation="created",
            fallback_keys=[spec.name for spec in specs],
        )

    async def delete_topics(self, names: list[TopicName]) -> TopicMetadata:
        if not names:
            return {}

        futures: dict[Any, Any] = self.admin_client.delete_topics(
            names, operation_timeout=30.0, request_timeout=60.0
        )

        return await self._execute_kafka_operation(
            futures=futures,
            operation="deleted",
            fallback_keys=names,
        )

    async def alter_topic_configs(self, configs: TopicConfig) -> TopicMetadata:
        if not configs:
            return {}

        resources: list[tuple[ConfigResource, dict[str, str]]] = [
            (ConfigResource(ConfigResource.Type.TOPIC, topic_name), config)
            for topic_name, config in configs.items()
        ]
        futures: dict[Any, Any] = self.admin_client.alter_configs(resources, request_timeout=60.0)

        def extract_topic_name(resource: Any) -> str:
            if topic_name := getattr(resource, "name", None):
                return topic_name
            return str(resource).split(":", 1)[1] if ":" in str(resource) else str(resource)

        return await self._execute_kafka_operation(
            futures=futures,
            operation="altered config for",
            fallback_keys=configs,
            key_extractor=extract_topic_name,
        )

    async def create_partitions(self, partitions: TopicPartitions) -> TopicMetadata:
        if not partitions:
            return {}

        partition_updates: list[NewPartitions] = [
            NewPartitions(topic=topic_name, new_total_count=partition_count)
            for topic_name, partition_count in partitions.items()
        ]
        futures: dict[Any, Any] = self.admin_client.create_partitions(
            partition_updates,
            operation_timeout=30.0,
            request_timeout=60.0,
        )

        return await self._execute_kafka_operation(
            futures=futures,
            operation="created partitions for",
            fallback_keys=partitions,
        )

    async def describe_topics(self, names: list[TopicName]) -> dict[TopicName, dict[str, Any]]:
        if not names:
            return {}

        try:
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, partial(self.admin_client.list_topics, timeout=60.0)
            )
            logger.debug(f"Metadata for topics {names}: {metadata}")

            results: dict[TopicName, dict[str, Any]] = {}
            for name in names:
                topic_metadata = metadata.topics.get(name)
                if topic_metadata is None:
                    continue

                config_resource = ConfigResource(ConfigResource.Type.TOPIC, name)
                config_futures = self.admin_client.describe_configs([config_resource])
                logger.info("config_futures: %s", config_futures)

                try:
                    config_result = await asyncio.get_event_loop().run_in_executor(
                        None, config_futures[config_resource].result, 30.0
                    )

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
                    error_str = str(e)
                    if "UNKNOWN_TOPIC_OR_PART" in error_str:
                        logger.warning(
                            f"Topic {name} was deleted or is inaccessible during config fetch. "
                            "Returning basic metadata only."
                        )
                    else:
                        logger.error(f"Failed to get config for topic {name}: {e}")

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
