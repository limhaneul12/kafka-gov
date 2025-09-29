"""Schema Domain 서비스"""

from __future__ import annotations

from typing import Any

from .models import (
    DomainPlanAction,
    DomainSchemaBatch,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaSpec,
)
from .policies import SchemaPolicyEngine
from .repositories.interfaces import ISchemaRegistryRepository


class SchemaPlannerService:
    """스키마 배치 계획 생성 서비스"""

    def __init__(
        self,
        registry_repository: ISchemaRegistryRepository,
        policy_engine: SchemaPolicyEngine,
    ) -> None:
        self.registry_repository = registry_repository
        self.policy_engine = policy_engine

    async def create_plan(self, batch: DomainSchemaBatch) -> DomainSchemaPlan:
        """배치 계획 및 정책 검증 실행"""
        violations = self.policy_engine.validate_batch(batch.specs)

        current_subjects = await self.registry_repository.describe_subjects(
            spec.subject for spec in batch.specs
        )

        compatibility_reports = []
        plan_items: list[DomainSchemaPlanItem] = []

        for spec in batch.specs:
            current_info = current_subjects.get(spec.subject)
            plan_items.append(self._create_plan_item(spec, current_info))

            report = await self.registry_repository.check_compatibility(spec)
            compatibility_reports.append(report)

        return DomainSchemaPlan(
            change_id=batch.change_id,
            env=batch.env,
            items=tuple(plan_items),
            violations=tuple(violations),
            compatibility_reports=tuple(compatibility_reports),
            impacts=(),
        )

    def _create_plan_item(
        self, spec: DomainSchemaSpec, current_info: dict[str, Any] | None
    ) -> DomainSchemaPlanItem:
        if spec.dry_run_only:
            return DomainSchemaPlanItem(
                subject=spec.subject,
                action=DomainPlanAction.NONE,
                current_version=current_info.get("version") if current_info else None,
                target_version=None,
                diff={},
            )

        if current_info is None:
            return DomainSchemaPlanItem(
                subject=spec.subject,
                action=DomainPlanAction.REGISTER,
                current_version=None,
                target_version=None,
                diff={"status": "new→registered"},
            )

        current_version = current_info.get("version")
        current_hash = current_info.get("hash")
        target_hash = spec.schema_hash or spec.fingerprint()

        if current_hash == target_hash:
            return DomainSchemaPlanItem(
                subject=spec.subject,
                action=DomainPlanAction.NONE,
                current_version=current_version,
                target_version=current_version,
                diff={},
            )

        diff: dict[str, object] = {
            "hash": f"{current_hash}→{target_hash}",
        }
        return DomainSchemaPlanItem(
            subject=spec.subject,
            action=DomainPlanAction.UPDATE,
            current_version=current_version,
            target_version=None,
            diff=diff,
        )
