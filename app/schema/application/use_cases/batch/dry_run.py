"""스키마 배치 Dry-Run 유스케이스"""

from __future__ import annotations

from app.cluster.domain.services import IConnectionManager
from app.schema.domain.policies.policy_pack import DefaultSchemaPolicyPackV1
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.shared.actor import merge_actor_metadata
from app.shared.constants import AuditAction, AuditStatus, AuditTarget

from ....domain.models import DomainSchemaBatch, DomainSchemaPlan
from ....domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaPolicyRepository,
)
from ....domain.services import SchemaPlannerService


class SchemaBatchDryRunUseCase:
    """스키마 배치 Dry-Run 유스케이스 (멀티 레지스트리 지원)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
        policy_repository: ISchemaPolicyRepository | None = None,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.policy_repository = policy_repository

    async def execute(
        self,
        registry_id: str,
        batch: DomainSchemaBatch,
        actor: str,
        actor_context: dict[str, str] | None = None,
    ) -> DomainSchemaPlan:
        await self.audit_repository.log_operation(
            change_id=batch.change_id,
            action=AuditAction.DRY_RUN,
            target=AuditTarget.BATCH,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Schema dry-run started for {len(batch.specs)} subjects",
            snapshot=merge_actor_metadata(None, actor_context),
        )

        try:
            # 1. ConnectionManager로 Schema Registry Client 획득
            registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
            registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

            # 2. Planner Service 생성 및 계획 수립
            planner_service = SchemaPlannerService(
                registry_repository, policy_repository=self.policy_repository
            )  # type: ignore[arg-type]
            plan = await planner_service.create_plan(batch)
            policy_pack_result = DefaultSchemaPolicyPackV1().evaluate(batch, plan)
            plan = DomainSchemaPlan(
                change_id=plan.change_id,
                env=plan.env,
                items=plan.items,
                compatibility_reports=plan.compatibility_reports,
                impacts=plan.impacts,
                violations=policy_pack_result.violations,
                risk=policy_pack_result.evaluation.risk_metadata(),
                approval=policy_pack_result.evaluation.approval_metadata(
                    mode="dry-run",
                    approval_override_present=False,
                ),
                policy_evaluation=policy_pack_result.evaluation,
                requested_total=plan.requested_total,
                actor_context=actor_context,
            )

            await self.metadata_repository.save_plan(plan, actor)
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.DRY_RUN,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message="Schema dry-run completed",
                snapshot=merge_actor_metadata(
                    {
                        "summary": plan.summary(),
                        "requested_items": [
                            {
                                "subject": spec.subject,
                                "reason": spec.reason,
                            }
                            for spec in batch.specs
                        ],
                        "policy_pack": plan.policy_evaluation.to_audit_dict()
                        if plan.policy_evaluation is not None
                        else None,
                    },
                    actor_context,
                ),
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
                snapshot=merge_actor_metadata(None, actor_context),
            )
            raise
