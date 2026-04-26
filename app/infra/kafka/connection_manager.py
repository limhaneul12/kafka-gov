from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from confluent_kafka.schema_registry import AsyncSchemaRegistryClient

from app.registry_connections.domain.models import ConnectionTestResult
from app.registry_connections.domain.repositories import ISchemaRegistryRepository

logger = logging.getLogger(__name__)


class IConnectionManager(ABC):
    @property
    @abstractmethod
    def schema_registry_repo(self) -> ISchemaRegistryRepository: ...

    @abstractmethod
    async def get_schema_registry_client(self, registry_id: str) -> AsyncSchemaRegistryClient: ...

    @abstractmethod
    async def test_schema_registry_connection(self, registry_id: str) -> ConnectionTestResult: ...

    @abstractmethod
    def invalidate_cache(self, resource_type: str, resource_id: str) -> None: ...


class ConnectionManager(IConnectionManager):
    def __init__(
        self,
        schema_registry_repo: ISchemaRegistryRepository,
    ) -> None:
        self._schema_registry_repo = schema_registry_repo
        self._schema_registry_clients: dict[str, AsyncSchemaRegistryClient] = {}
        self._locks: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Lock]] = {}

    @property
    def schema_registry_repo(self) -> ISchemaRegistryRepository:
        return self._schema_registry_repo

    async def get_schema_registry_client(self, registry_id: str) -> AsyncSchemaRegistryClient:
        if registry_id in self._schema_registry_clients:
            logger.debug("Schema Registry Client cache hit: %s", registry_id)
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

            logger.info("Creating new Schema Registry Client: %s", registry_id)
            client = AsyncSchemaRegistryClient(registry.to_client_config())
            self._schema_registry_clients[registry_id] = client
            return client

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
            logger.error("Schema Registry connection test failed for %s: %s", registry_id, e)
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {e!s}",
            )

    def invalidate_cache(self, resource_type: str, resource_id: str) -> None:
        if resource_type == "schema_registry" and resource_id in self._schema_registry_clients:
            del self._schema_registry_clients[resource_id]
            logger.info("Schema Registry Client cache invalidated: %s", resource_id)

        lock_key = f"{resource_type}_{resource_id}"
        if lock_key in self._locks:
            del self._locks[lock_key]

    def clear_all_caches(self) -> None:
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
