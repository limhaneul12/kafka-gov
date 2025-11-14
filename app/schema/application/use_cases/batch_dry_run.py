"""스키마 배치 Dry-Run 유스케이스"""

from __future__ import annotations

from app.cluster.domain.services import IConnectionManager
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.shared.constants import AuditAction, AuditStatus, AuditTarget

from ...domain.models import DomainSchemaBatch, DomainSchemaPlan
from ...domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
)
from ...domain.services import SchemaPlannerService


class SchemaBatchDryRunUseCase:
    """스키마 배치 Dry-Run 유스케이스 (멀티 레지스트리 지원)"""

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
        self, registry_id: str, batch: DomainSchemaBatch, actor: str
    ) -> DomainSchemaPlan:
        await self.audit_repository.log_operation(
            change_id=batch.change_id,
            action=AuditAction.DRY_RUN,
            target=AuditTarget.BATCH,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Schema dry-run started for {len(batch.specs)} subjects",
        )

        try:
            # 1. ConnectionManager로 Schema Registry Client 획득
            registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
            registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

            # 2. Planner Service 생성 및 계획 수립
            planner_service = SchemaPlannerService(registry_repository)  # type: ignore[arg-type]
            plan = await planner_service.create_plan(batch)

            await self.metadata_repository.save_plan(plan, actor)
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.DRY_RUN,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message="Schema dry-run completed",
                snapshot={"summary": plan.summary()},
            )
            return plan
        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.DRY_RUN,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Schema dry-run failed: {exc!s}",
            )
            raise
