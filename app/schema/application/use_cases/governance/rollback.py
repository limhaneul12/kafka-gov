"""스키마 롤백 유스케이스"""

from __future__ import annotations

import logging

from app.infra.kafka.connection_manager import IConnectionManager
from app.infra.kafka.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.application.use_cases.management.plan_change import PlanSchemaChangeUseCase
from app.schema.domain.models import (
    DomainSchemaPlan,
)
from app.schema.domain.repositories.interfaces import (
    ISchemaMetadataRepository,
)


class RollbackSchemaUseCase:
    """특정 버전으로 롤백 계획 수립"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        plan_change_use_case: PlanSchemaChangeUseCase,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.plan_change_use_case = plan_change_use_case
        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        registry_id: str,
        subject: str,
        version: int,
        actor: str,
        reason: str | None = None,
        actor_context: dict[str, str] | None = None,
    ) -> DomainSchemaPlan:
        """특정 버전으로 롤백 계획 수립"""
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

        # 1. 과거 버전 스키마 조회
        old_version_info = await registry_repository.get_schema_by_version(subject, version)
        if not old_version_info:
            raise ValueError(f"Version {version} for subject {subject} not found")

        # 2. 현재 메타데이터에서 호환성 모드 조회
        artifact = await self.metadata_repository.get_latest_artifact(subject)
        compatibility = "BACKWARD"
        if artifact and artifact.compatibility_mode:
            compatibility = (
                artifact.compatibility_mode
                if isinstance(artifact.compatibility_mode, str)
                else artifact.compatibility_mode.value
            )

        # 3. plan_change 호출하여 계획 수립 (롤백도 결국 새로운 버전 등록 계획임)
        plan = await self.plan_change_use_case.execute(
            registry_id=registry_id,
            subject=subject,
            new_schema=old_version_info.schema or "",
            compatibility=compatibility,
            actor=actor,
            reason=reason,
            actor_context=actor_context,
        )

        return plan
