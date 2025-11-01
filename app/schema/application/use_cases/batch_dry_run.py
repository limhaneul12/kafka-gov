"""스키마 배치 Dry-Run 유스케이스"""

from __future__ import annotations

from app.cluster.domain.services import IConnectionManager
from app.schema.domain.policy_engine import SchemaPolicyEngine
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.shared.constants import AuditAction, AuditStatus, AuditTarget
from app.shared.domain.policy_types import DomainPolicySeverity

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
        policy_engine: SchemaPolicyEngine,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.policy_engine = policy_engine

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
            planner_service = SchemaPlannerService(registry_repository, self.policy_engine)  # type: ignore[arg-type]
            plan = await planner_service.create_plan(batch)

            # 정책 위반 분석
            if plan.violations:
                self._analyze_policy_violations(list(plan.violations), actor)

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

    def _analyze_policy_violations(self, violations: list, actor: str) -> None:
        """정책 위반 분석 (통합 형식 활용)"""

        # DomainPolicySeverity Enum 기반 분석 가능
        blocking_count = sum(
            1
            for v in violations
            if v.severity in (DomainPolicySeverity.ERROR, DomainPolicySeverity.CRITICAL)
        )

        # 로깅이나 추가 처리
        print(f"Policy violations analysis - Total: {len(violations)}, Blocking: {blocking_count}")
