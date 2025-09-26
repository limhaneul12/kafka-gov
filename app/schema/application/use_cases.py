"""Schema Application 유스케이스"""

from __future__ import annotations

import uuid
from typing import Any

from ..domain.models import (
    ChangeId,
    SchemaApplyResult,
    SchemaArtifact,
    SchemaBatch,
    SchemaPlan,
    SchemaSpec,
)
from ..domain.policies import SchemaPolicyEngine
from ..domain.repositories.interfaces import (
    IObjectStorageRepository,
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaRegistryRepository,
)
from ..domain.services import SchemaPlannerService


class SchemaBatchDryRunUseCase:
    """스키마 배치 Dry-Run 유스케이스"""

    def __init__(
        self,
        registry_repository: ISchemaRegistryRepository,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
        policy_engine: SchemaPolicyEngine,
    ) -> None:
        self.registry_repository = registry_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.policy_engine = policy_engine
        self.planner_service = SchemaPlannerService(registry_repository, policy_engine)

    async def execute(self, batch: SchemaBatch, actor: str) -> SchemaPlan:
        await self.audit_repository.log_operation(
            change_id=batch.change_id,
            action="DRY_RUN",
            target="BATCH",
            actor=actor,
            status="STARTED",
            message=f"Schema dry-run started for {len(batch.specs)} subjects",
        )

        try:
            plan = await self.planner_service.create_plan(batch)
            await self.metadata_repository.save_plan(plan, actor)
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action="DRY_RUN",
                target="BATCH",
                actor=actor,
                status="COMPLETED",
                message="Schema dry-run completed",
                snapshot={"summary": plan.summary()},
            )
            return plan
        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action="DRY_RUN",
                target="BATCH",
                actor=actor,
                status="FAILED",
                message=f"Schema dry-run failed: {exc!s}",
            )
            raise


class SchemaBatchApplyUseCase:
    """스키마 배치 Apply 유스케이스"""

    def __init__(
        self,
        registry_repository: ISchemaRegistryRepository,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
        storage_repository: IObjectStorageRepository | None,
        policy_engine: SchemaPolicyEngine,
    ) -> None:
        self.registry_repository = registry_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.storage_repository = storage_repository
        self.policy_engine = policy_engine
        self.planner_service = SchemaPlannerService(registry_repository, policy_engine)

    async def execute(self, batch: SchemaBatch, actor: str) -> SchemaApplyResult:
        audit_id = str(uuid.uuid4())
        await self.audit_repository.log_operation(
            change_id=batch.change_id,
            action="APPLY",
            target="BATCH",
            actor=actor,
            status="STARTED",
            message=f"Schema apply started for {len(batch.specs)} subjects",
        )

        try:
            plan = await self.planner_service.create_plan(batch)
            if not plan.can_apply:
                raise ValueError("Policy violations or incompatibilities detected; apply aborted")

            registered: list[str] = []
            skipped: list[str] = []
            failed: list[dict[str, str]] = []
            artifacts: list[SchemaArtifact] = []

            for spec in batch.specs:
                if spec.dry_run_only:
                    skipped.append(spec.subject)
                    continue

                try:
                    version = await self.registry_repository.register_schema(spec)
                    artifact = await self._persist_artifact(spec, version, batch.change_id)
                    if artifact:
                        artifacts.append(artifact)
                    registered.append(spec.subject)
                except Exception as exc:  # pragma: no cover - 실제 구현에서 세부 처리
                    failed.append({"subject": spec.subject, "error": str(exc)})

            result = SchemaApplyResult(
                change_id=batch.change_id,
                env=batch.env,
                registered=tuple(registered),
                skipped=tuple(skipped),
                failed=tuple(failed),
                audit_id=audit_id,
                artifacts=tuple(artifacts),
            )

            await self.metadata_repository.save_apply_result(result, actor)
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action="APPLY",
                target="BATCH",
                actor=actor,
                status="COMPLETED",
                message="Schema apply completed",
                snapshot={"summary": result.summary()},
            )

            return result
        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action="APPLY",
                target="BATCH",
                actor=actor,
                status="FAILED",
                message=f"Schema apply failed: {exc!s}",
            )
            raise

    async def _persist_artifact(
        self,
        spec: SchemaSpec,
        version: int,
        change_id: ChangeId,
    ) -> SchemaArtifact | None:
        if self.storage_repository is None:
            return None

        payload: str | None = None
        if spec.schema:
            payload = spec.schema
        elif spec.source and spec.source.inline:
            payload = spec.source.inline
        elif spec.source and spec.source.yaml:
            payload = spec.source.yaml

        if payload is None:
            return None

        key = f"{spec.environment.value}/{spec.subject}/{version}/schema.txt"
        metadata = {"change_id": change_id, "schema_type": spec.schema_type.value}
        storage_url = await self.storage_repository.put_object(
            key=key,
            data=payload.encode(),
            metadata=metadata,
        )

        artifact = SchemaArtifact(
            subject=spec.subject,
            version=version,
            storage_url=storage_url,
            checksum=spec.schema_hash or spec.fingerprint(),
        )
        await self.metadata_repository.record_artifact(artifact, change_id)
        return artifact


class SchemaPlanUseCase:
    """스키마 배치 계획 조회 유스케이스"""

    def __init__(
        self,
        metadata_repository: ISchemaMetadataRepository,
    ) -> None:
        self.metadata_repository = metadata_repository

    async def execute(self, change_id: ChangeId) -> SchemaPlan | None:
        return await self.metadata_repository.get_plan(change_id)


class SchemaUploadUseCase:
    """스키마 업로드 유스케이스"""

    def __init__(
        self,
        storage_repository: IObjectStorageRepository,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
    ) -> None:
        self.storage_repository = storage_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository

    async def execute(
        self,
        *,
        env: Any,
        change_id: ChangeId,
        files: list[Any],
        actor: str,
    ) -> dict[str, Any]:
        raise NotImplementedError("Schema upload use case not implemented yet")
