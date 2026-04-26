"""스키마 롤백 유스케이스"""

from __future__ import annotations

import logging
from datetime import datetime

from app.infra.kafka.connection_manager import IConnectionManager
from app.infra.kafka.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.application.use_cases.management.plan_change import PlanSchemaChangeUseCase
from app.schema.domain.models import (
    DomainEnvironment,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaPlan,
)
from app.schema.domain.repositories.interfaces import (
    ISchemaMetadataRepository,
)
from app.schema.governance_support.approval import ApprovalOverride


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
        if not artifact or not artifact.compatibility_mode:
            raise ValueError(
                f"Compatibility mode must be explicitly configured before rollback planning: {subject}"
            )
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


class ExecuteRollbackSchemaUseCase:
    """특정 버전으로 롤백 실행"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        apply_use_case: object,  # retained for container wiring compatibility
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.apply_use_case = apply_use_case
        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        registry_id: str,
        subject: str,
        version: int,
        actor: str,
        approval_override: ApprovalOverride | None = None,
        reason: str | None = None,
        actor_context: dict[str, str] | None = None,
    ) -> DomainSchemaApplyResult:
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

        old_version_info = await registry_repository.get_schema_by_version(subject, version)
        if not old_version_info or not old_version_info.schema:
            raise ValueError(f"Version {version} for subject {subject} not found")

        versions = await registry_repository.get_schema_versions(subject)
        if version not in versions:
            raise ValueError(f"Version {version} for subject {subject} not found")

        artifact = await self.metadata_repository.get_latest_artifact(subject)

        env_str = subject.split(".")[0] if "." in subject else DomainEnvironment.DEV.value
        try:
            env = DomainEnvironment(env_str)
        except ValueError:
            env = DomainEnvironment.DEV

        change_id = f"rollback_{subject}_{version}_{int(datetime.now().timestamp())}"
        newer_versions = sorted((item for item in versions if item > version), reverse=True)

        if not newer_versions:
            result = DomainSchemaApplyResult(
                change_id=change_id,
                env=env,
                registered=(),
                skipped=(subject,),
                failed=(),
                audit_id=change_id,
                artifacts=(),
                requested_total=1,
                planned_total=0,
                warning_total=1,
                details=(
                    {
                        "subject": subject,
                        "action": "NONE",
                        "status": "skipped",
                        "reason": reason,
                        "error_message": None,
                    },
                ),
                actor_context=actor_context,
            )
            await self.metadata_repository.save_apply_result(result, actor)
            return result

        for newer_version in newer_versions:
            await registry_repository.delete_version(subject, newer_version)

        await self.metadata_repository.delete_artifacts_newer_than(subject, version)

        result = DomainSchemaApplyResult(
            change_id=change_id,
            env=env,
            registered=(subject,),
            skipped=(),
            failed=(),
            audit_id=change_id,
            artifacts=(
                DomainSchemaArtifact(
                    subject=subject,
                    version=old_version_info.version,
                    storage_url=artifact.storage_url if artifact else None,
                    checksum=old_version_info.hash,
                    compatibility_mode=artifact.compatibility_mode
                    if artifact is not None
                    else None,
                    owner=artifact.owner if artifact is not None else None,
                ),
            ),
            requested_total=1,
            planned_total=1,
            warning_total=0,
            details=(
                {
                    "subject": subject,
                    "action": "ROLLBACK",
                    "status": "registered",
                    "reason": reason,
                    "error_message": None,
                },
            ),
            actor_context=actor_context,
        )
        await self.metadata_repository.save_apply_result(result, actor)
        return result
