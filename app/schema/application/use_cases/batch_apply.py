"""스키마 배치 Apply 유스케이스"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.cluster.domain.services import IConnectionManager
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.infrastructure.storage.minio_adapter import MinIOObjectStorageAdapter
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
from ...domain.policies import SchemaPolicyEngine
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
        policy_engine: SchemaPolicyEngine,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.policy_engine = policy_engine
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

            # 2. Storage Repository 준비 (선택적)
            storage_repository = None
            if storage_id:
                minio_client, bucket_name = await self.connection_manager.get_minio_client(
                    storage_id
                )
                # ObjectStorage 정보에서 base_url 가져오기
                storage_info = await self.connection_manager.get_storage_info(storage_id)
                base_url = (
                    storage_info.get_base_url()
                    if hasattr(storage_info, "get_base_url")
                    else f"http://{storage_info.endpoint_url}"
                )

                storage_repository = MinIOObjectStorageAdapter(
                    client=minio_client,
                    bucket_name=bucket_name,
                    base_url=base_url,
                )

            # 3. Planner Service 생성 및 계획 수립
            planner_service = SchemaPlannerService(registry_repository, self.policy_engine)  # type: ignore[arg-type]
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
                    artifact = await self._persist_artifact(
                        storage_repository, spec, version, batch.change_id
                    )
                    if artifact:
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
        storage_repository: MinIOObjectStorageAdapter | None,
        spec: DomainSchemaSpec,
        version: int,
        change_id: ChangeId,
    ) -> DomainSchemaArtifact | None:
        if storage_repository is None:
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
        storage_url = await storage_repository.put_object(
            key=key,
            data=payload.encode(),
            metadata=metadata,
        )

        artifact = DomainSchemaArtifact(
            subject=spec.subject,
            version=version,
            storage_url=storage_url,
            checksum=spec.schema_hash or spec.fingerprint(),
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
