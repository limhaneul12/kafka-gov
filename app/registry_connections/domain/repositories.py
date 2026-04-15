"""Schema Registry connection repository interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import SchemaRegistry


class ISchemaRegistryRepository(ABC):
    """Schema Registry repository interface."""

    @abstractmethod
    async def create(self, registry: SchemaRegistry) -> SchemaRegistry: ...

    @abstractmethod
    async def get_by_id(self, registry_id: str) -> SchemaRegistry | None: ...

    @abstractmethod
    async def list_all(self, active_only: bool = True) -> list[SchemaRegistry]: ...

    @abstractmethod
    async def update(self, registry: SchemaRegistry) -> SchemaRegistry: ...

    @abstractmethod
    async def delete(self, registry_id: str) -> bool: ...
