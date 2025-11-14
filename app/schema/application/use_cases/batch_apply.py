"""스키마 배치 Apply 유스케이스"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.cluster.domain.services import IConnectionManager
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.shared.constants import AuditAction, AuditStatus, AuditTarget
from app.shared.domain.events import SchemaRegisteredEvent
from app.shared.infrastructure.event_bus import get_event_bus

from ...domain.models import (
    ChangeId,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaBatch,
    DomainSchemaSpec,
)
from ...domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
)
from ...domain.services import SchemaPlannerService


class SchemaBatchApplyUseCase:
    """스키마 배치 Apply 유스케이스 (멀티 레지스트리/스토리지 지원)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.event_bus = get_event_bus()

    async def execute(
        self, registry_id: str, storage_id: str | None, batch: DomainSchemaBatch, actor: str
    ) -> DomainSchemaApplyResult:
        audit_id = str(uuid.uuid4())
        await self.audit_repository.log_operation(
            change_id=batch.change_id,
            action=AuditAction.APPLY,
            target=AuditTarget.BATCH,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Schema apply started for {len(batch.specs)} subjects",
        )

        try:
            # 1. ConnectionManager로 Schema Registry Client 획득
            registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
            registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

            # 2. Planner Service 생성 및 계획 수립
            planner_service = SchemaPlannerService(registry_repository)  # type: ignore[arg-type]
            plan = await planner_service.create_plan(batch)

            if not plan.can_apply:
                raise ValueError("Policy violations or incompatibilities detected; apply aborted")

            registered: list[str] = []
            skipped: list[str] = []
            failed: list[dict[str, str]] = []
            artifacts: list[DomainSchemaArtifact] = []

            for spec in batch.specs:
                if spec.dry_run_only:
                    skipped.append(spec.subject)
                    continue

                try:
                    version, schema_id = await registry_repository.register_schema(spec)  # type: ignore[arg-type]

                    # MinIO 사용 없이 Artifact 메타데이터만 저장
                    artifact = await self._persist_artifact(spec, version, batch.change_id)
                    artifacts.append(artifact)
                    registered.append(spec.subject)

                    # 🆕 Domain Event 발행
                    await self._publish_schema_registered_event(
                        spec=spec,
                        version=version,
                        schema_id=schema_id,
                        batch=batch,
                        actor=actor,
                    )

                except Exception as exc:
                    failed.append({"subject": spec.subject, "error": str(exc)})

            result = DomainSchemaApplyResult(
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
                action=AuditAction.APPLY,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message="Schema apply completed",
                snapshot={"summary": result.summary()},
            )

            return result
        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Schema apply failed: {exc!s}",
            )
            raise

    async def _persist_artifact(
        self,
        spec: DomainSchemaSpec,
        version: int,
        change_id: ChangeId,
    ) -> DomainSchemaArtifact:
        """스키마 Artifact 메타데이터 저장 (외부 Object Storage 미사용).

        storage_url은 항상 None으로 유지하고, checksum과 기본 메타만 기록한다.
        """
        checksum = spec.schema_hash or spec.fingerprint()

        artifact = DomainSchemaArtifact(
            subject=spec.subject,
            version=version,
            storage_url=None,
            checksum=checksum,
        )
        await self.metadata_repository.record_artifact(artifact, change_id)
        return artifact

    async def _publish_schema_registered_event(
        self,
        spec: DomainSchemaSpec,
        version: int,
        schema_id: int,
        batch: DomainSchemaBatch,
        actor: str,
    ) -> None:
        """스키마 등록 이벤트 발행

        Args:
            schema_id: register_schema에서 받은 스키마 ID (중복 조회 없이 직접 전달)
        """
        event = SchemaRegisteredEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            aggregate_id=batch.change_id,
            occurred_at=datetime.now(),
            subject=spec.subject,
            version=version,
            schema_type=spec.schema_type.value,
            schema_id=schema_id,
            compatibility_mode=spec.compatibility.value,
            subject_strategy=batch.subject_strategy.value,
            environment=batch.env.value,
            actor=actor,
        )

        await self.event_bus.publish(event)
