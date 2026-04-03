from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from confluent_kafka.admin import AdminClient
from confluent_kafka.schema_registry import AsyncSchemaRegistryClient
from kafka import KafkaAdminClient

from app.cluster.domain.models import ConnectionTestResult
from app.cluster.domain.repositories import IKafkaClusterRepository, ISchemaRegistryRepository

logger = logging.getLogger(__name__)


class IConnectionManager(ABC):
    @property
    @abstractmethod
    def kafka_cluster_repo(self) -> IKafkaClusterRepository: ...

    @property
    @abstractmethod
    def schema_registry_repo(self) -> ISchemaRegistryRepository: ...

    @abstractmethod
    async def get_kafka_admin_client(self, cluster_id: str) -> AdminClient: ...

    @abstractmethod
    async def get_kafka_py_admin_client(self, cluster_id: str) -> KafkaAdminClient: ...

    @abstractmethod
    async def get_schema_registry_client(self, registry_id: str) -> AsyncSchemaRegistryClient: ...

    @abstractmethod
    async def test_kafka_connection(self, cluster_id: str) -> ConnectionTestResult: ...

    @abstractmethod
    async def test_schema_registry_connection(self, registry_id: str) -> ConnectionTestResult: ...

    @abstractmethod
    def invalidate_cache(self, resource_type: str, resource_id: str) -> None: ...


class ConnectionManager(IConnectionManager):
    def __init__(
        self,
        kafka_cluster_repo: IKafkaClusterRepository,
        schema_registry_repo: ISchemaRegistryRepository,
    ) -> None:
        self._kafka_cluster_repo = kafka_cluster_repo
        self._schema_registry_repo = schema_registry_repo

        self._kafka_clients: dict[str, AdminClient] = {}
        self._kafka_py_clients: dict[str, KafkaAdminClient] = {}
        self._schema_registry_clients: dict[str, AsyncSchemaRegistryClient] = {}
        self._locks: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Lock]] = {}

    @property
    def kafka_cluster_repo(self) -> IKafkaClusterRepository:
        return self._kafka_cluster_repo

    @property
    def schema_registry_repo(self) -> ISchemaRegistryRepository:
        return self._schema_registry_repo

    async def get_kafka_admin_client(self, cluster_id: str) -> AdminClient:
        if cluster_id in self._kafka_clients:
            logger.debug(f"Kafka AdminClient cache hit: {cluster_id}")
            return self._kafka_clients[cluster_id]

        lock_key = f"kafka_{cluster_id}"
        lock = self._get_loop_scoped_lock(lock_key)

        async with lock:
            if cluster_id in self._kafka_clients:
                return self._kafka_clients[cluster_id]

            cluster = await self.kafka_cluster_repo.get_by_id(cluster_id)
            if not cluster:
                raise ValueError(f"Kafka cluster not found: {cluster_id}")
            if not cluster.is_active:
                raise ValueError(f"Kafka cluster is inactive: {cluster_id}")

            logger.info(f"Creating new Kafka AdminClient: {cluster_id}")
            admin_client = AdminClient(cluster.to_admin_config())
            self._kafka_clients[cluster_id] = admin_client
            return admin_client

    async def get_kafka_py_admin_client(self, cluster_id: str) -> KafkaAdminClient:
        if cluster_id in self._kafka_py_clients:
            logger.debug(f"Kafka (py) AdminClient cache hit: {cluster_id}")
            return self._kafka_py_clients[cluster_id]

        lock_key = f"kafka_py_{cluster_id}"
        lock = self._get_loop_scoped_lock(lock_key)

        async with lock:
            if cluster_id in self._kafka_py_clients:
                return self._kafka_py_clients[cluster_id]

            cluster = await self.kafka_cluster_repo.get_by_id(cluster_id)
            if not cluster:
                raise ValueError(f"Kafka cluster not found: {cluster_id}")
            if not cluster.is_active:
                raise ValueError(f"Kafka cluster is inactive: {cluster_id}")

            config: dict[str, str | int | bool] = {
                "bootstrap_servers": cluster.bootstrap_servers,
                "security_protocol": cluster.security_protocol.value,
                "request_timeout_ms": cluster.request_timeout_ms,
            }

            if cluster.sasl_mechanism:
                config["sasl_mechanism"] = cluster.sasl_mechanism.value
            if cluster.sasl_username:
                config["sasl_plain_username"] = cluster.sasl_username
            if cluster.sasl_password:
                config["sasl_plain_password"] = cluster.sasl_password
            if cluster.ssl_ca_location:
                config["ssl_cafile"] = cluster.ssl_ca_location
            if cluster.ssl_cert_location:
                config["ssl_certfile"] = cluster.ssl_cert_location
            if cluster.ssl_key_location:
                config["ssl_keyfile"] = cluster.ssl_key_location

            logger.info(f"Creating new Kafka (py) AdminClient: {cluster_id}")
            client = KafkaAdminClient(**config)
            self._kafka_py_clients[cluster_id] = client
            return client

    async def get_schema_registry_client(self, registry_id: str) -> AsyncSchemaRegistryClient:
        if registry_id in self._schema_registry_clients:
            logger.debug(f"Schema Registry Client cache hit: {registry_id}")
            return self._schema_registry_clients[registry_id]

        lock_key = f"schema_{registry_id}"
        lock = self._get_loop_scoped_lock(lock_key)

        async with lock:
            if registry_id in self._schema_registry_clients:
                return self._schema_registry_clients[registry_id]

            registry = await self.schema_registry_repo.get_by_id(registry_id)
            if not registry:
                raise ValueError(f"Schema Registry not found: {registry_id}")
            if not registry.is_active:
                raise ValueError(f"Schema Registry is inactive: {registry_id}")

            logger.info(f"Creating new Schema Registry Client: {registry_id}")
            client = AsyncSchemaRegistryClient(registry.to_client_config())
            self._schema_registry_clients[registry_id] = client
            return client

    async def test_kafka_connection(self, cluster_id: str) -> ConnectionTestResult:
        import time

        try:
            start_time = time.time()
            admin_client = await self.get_kafka_admin_client(cluster_id)
            metadata = admin_client.list_topics(timeout=10)
            latency_ms = (time.time() - start_time) * 1000

            return ConnectionTestResult(
                success=True,
                message=f"Connected to Kafka cluster: {len(metadata.brokers)} brokers",
                latency_ms=latency_ms,
                metadata={
                    "broker_count": len(metadata.brokers),
                    "topic_count": len(metadata.topics),
                    "cluster_id": metadata.cluster_id or "unknown",
                },
            )
        except Exception as e:
            logger.error(f"Kafka connection test failed for {cluster_id}: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {e!s}",
            )

    async def test_schema_registry_connection(self, registry_id: str) -> ConnectionTestResult:
        import time

        try:
            start_time = time.time()
            client = await self.get_schema_registry_client(registry_id)
            subjects = await client.get_subjects()
            latency_ms = (time.time() - start_time) * 1000

            return ConnectionTestResult(
                success=True,
                message=f"Connected to Schema Registry: {len(subjects)} subjects",
                latency_ms=latency_ms,
                metadata={"subject_count": len(subjects)},
            )
        except Exception as e:
            logger.error(f"Schema Registry connection test failed for {registry_id}: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {e!s}",
            )

    def invalidate_cache(self, resource_type: str, resource_id: str) -> None:
        if resource_type == "kafka":
            if resource_id in self._kafka_clients:
                del self._kafka_clients[resource_id]
                logger.info(f"Kafka AdminClient cache invalidated: {resource_id}")
            if resource_id in self._kafka_py_clients:
                del self._kafka_py_clients[resource_id]
                logger.info(f"Kafka (py) AdminClient cache invalidated: {resource_id}")
        elif resource_type == "schema_registry" and resource_id in self._schema_registry_clients:
            del self._schema_registry_clients[resource_id]
            logger.info(f"Schema Registry Client cache invalidated: {resource_id}")

        lock_key = f"{resource_type}_{resource_id}"
        if lock_key in self._locks:
            del self._locks[lock_key]

    def clear_all_caches(self) -> None:
        self._kafka_clients.clear()
        self._kafka_py_clients.clear()
        self._schema_registry_clients.clear()
        self._locks.clear()
        logger.info("All connection locks cleared")

    def _get_loop_scoped_lock(self, key: str) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        entry = self._locks.get(key)
        if entry is not None:
            stored_loop, lock = entry
            if stored_loop is loop:
                return lock

        lock = asyncio.Lock()
        self._locks[key] = (loop, lock)
        return lock
