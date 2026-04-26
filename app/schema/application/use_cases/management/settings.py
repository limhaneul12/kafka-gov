"""Schema metadata / compatibility settings management use case."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.infra.kafka.connection_manager import IConnectionManager
from app.infra.kafka.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
)
from app.schema.governance_support.actor import merge_actor_metadata
from app.schema.governance_support.constants import AuditAction, AuditStatus


@dataclass(frozen=True, slots=True)
class SchemaSettingsResult:
    subject: str
    owner: str | None = None
    doc: str | None = None
    tags: list[str] | None = None
    description: str | None = None
    compatibility_mode: str | None = None


class UpdateSchemaSettingsUseCase:
    """Update schema metadata and optionally subject compatibility mode."""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository

    async def execute(
        self,
        *,
        registry_id: str,
        subject: str,
        actor: str,
        owner: str | None = None,
        doc: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
        compatibility_mode: str | None = None,
        actor_context: dict[str, str] | None = None,
    ) -> SchemaSettingsResult:
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)
        describe_result = await registry_repository.describe_subjects([subject])
        if subject not in describe_result:
            raise ValueError(f"Subject '{subject}' not found")

        if compatibility_mode:
            await registry_repository.set_compatibility_mode(subject, compatibility_mode)

        payload: dict[str, Any] = {
            "owner": owner,
            "doc": doc,
            "tags": tags,
            "description": description,
            "compatibility_mode": compatibility_mode,
            "created_by": actor,
            "updated_by": actor,
        }
        await self.metadata_repository.save_schema_metadata(subject, payload)
        metadata = await self.metadata_repository.get_schema_metadata(subject)
        if metadata is None:
            raise RuntimeError(
                f"Schema metadata for '{subject}' could not be retrieved after update"
            )

        await self.audit_repository.log_operation(
            change_id=f"settings_{subject}",
            action=AuditAction.UPDATE,
            target=subject,
            actor=actor,
            status=AuditStatus.COMPLETED,
            message="Schema settings updated",
            snapshot=merge_actor_metadata(metadata, actor_context),
        )

        return SchemaSettingsResult(
            subject=subject,
            owner=metadata.get("owner"),
            doc=metadata.get("doc"),
            tags=metadata.get("tags"),
            description=metadata.get("description"),
            compatibility_mode=metadata.get("compatibility_mode"),
        )
