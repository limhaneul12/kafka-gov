from __future__ import annotations

from typing import Protocol

from app.schema.interface.schemas.request import SchemaBatchRequest
from app.shared.approval import ApprovalOverride
from app.topic.interface.schemas.request import TopicBatchRequest


class TopicBatchTransport(Protocol):
    async def dry_run(
        self,
        cluster_id: str,
        request: TopicBatchRequest,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object: ...

    async def apply(
        self,
        cluster_id: str,
        request: TopicBatchRequest,
        actor: str,
        approval_override: ApprovalOverride | None = None,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object: ...


class SchemaBatchTransport(Protocol):
    async def dry_run(
        self,
        registry_id: str,
        request: SchemaBatchRequest,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object: ...

    async def apply(
        self,
        registry_id: str,
        request: SchemaBatchRequest,
        actor: str,
        storage_id: str | None,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object: ...


class PreflightTransport:
    def __init__(
        self,
        topic_transport: TopicBatchTransport,
        schema_transport: SchemaBatchTransport,
    ) -> None:
        self._topic_transport: TopicBatchTransport = topic_transport
        self._schema_transport: SchemaBatchTransport = schema_transport

    async def topic_dry_run(
        self,
        cluster_id: str,
        request: TopicBatchRequest,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        return await self._topic_transport.dry_run(
            cluster_id, request, actor, actor_context=actor_context
        )

    async def topic_apply(
        self,
        cluster_id: str,
        request: TopicBatchRequest,
        actor: str,
        approval_override: ApprovalOverride | None = None,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        return await self._topic_transport.apply(
            cluster_id,
            request,
            actor,
            approval_override,
            actor_context=actor_context,
        )

    async def schema_dry_run(
        self,
        registry_id: str,
        request: SchemaBatchRequest,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        return await self._schema_transport.dry_run(
            registry_id, request, actor, actor_context=actor_context
        )

    async def schema_apply(
        self,
        registry_id: str,
        request: SchemaBatchRequest,
        actor: str,
        storage_id: str | None,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        return await self._schema_transport.apply(
            registry_id,
            request,
            actor,
            storage_id,
            actor_context=actor_context,
        )
