"""Schema Registry → DB 동기화 유스케이스"""

from __future__ import annotations

import logging
import uuid

from app.cluster.domain.services import IConnectionManager
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.shared.constants import AuditAction, AuditStatus, AuditTarget

from ...domain.models import DomainSchemaArtifact
from ...domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
)

logger = logging.getLogger(__name__)


class SchemaSyncUseCase:
    """Schema Registry → DB 동기화 유스케이스 (멀티 레지스트리 지원)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository

    async def execute(self, registry_id: str, actor: str) -> dict[str, int]:
        """Schema Registry의 모든 스키마를 DB로 동기화

        Returns:
            동기화 결과 (총 subject 수, 새로 추가된 수, 업데이트된 수)
        """
        logger.info(f"[Schema Sync] Starting synchronization for registry_id: {registry_id}")
        change_id = f"sync_{uuid.uuid4().hex[:8]}"

        await self.audit_repository.log_operation(
            change_id=change_id,
            action=AuditAction.SYNC,
            target=AuditTarget.SCHEMA_REGISTRY,
            actor=actor,
            status=AuditStatus.STARTED,
            message="Schema synchronization started",
        )

        try:
            # 1. ConnectionManager로 Schema Registry Client 획득
            logger.warning("[Schema Sync] Getting Schema Registry client for: %s", registry_id)
            registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
            logger.warning("[Schema Sync] Schema Registry client obtained successfully")
            registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

            # 2. Schema Registry에서 모든 subject 조회
            logger.warning("[Schema Sync] Listing all subjects from Schema Registry")
            all_subjects = await registry_repository.list_all_subjects()
            logger.warning(f"[Schema Sync] Found {len(all_subjects)} subjects")

            if not all_subjects:
                await self.audit_repository.log_operation(
                    change_id=change_id,
                    action=AuditAction.SYNC,
                    target=AuditTarget.SCHEMA_REGISTRY,
                    actor=actor,
                    status=AuditStatus.COMPLETED,
                    message="No schemas found in Schema Registry",
                )
                return {"total": 0, "added": 0, "updated": 0}

            # 3. 각 subject의 최신 버전 정보 조회
            subjects_info = await registry_repository.describe_subjects(all_subjects)

            # 4. DB에 artifact로 저장
            added_count = 0
            skipped_count = 0

            for subject, info in subjects_info.items():
                artifact = DomainSchemaArtifact(
                    subject=subject,
                    version=info.version,
                    storage_url=f"registry://{subject}/versions/{info.version}",
                    checksum=info.hash,
                )

                try:
                    await self.metadata_repository.record_artifact(artifact, change_id)
                    added_count += 1
                except Exception:
                    # 이미 존재하는 경우는 무시 (중복 키 에러)
                    skipped_count += 1

            result = {
                "total": len(subjects_info),
                "added": added_count,
                "updated": skipped_count,
            }

            await self.audit_repository.log_operation(
                change_id=change_id,
                action=AuditAction.SYNC,
                target=AuditTarget.SCHEMA_REGISTRY,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message=f"Schema synchronization completed: {result['total']} total, {result['added']} added",
                snapshot=result,
            )

            return result

        except Exception as exc:
            logger.warning(f"[Schema Sync] ERROR: {type(exc).__name__}: {exc!s}", exc_info=True)
            await self.audit_repository.log_operation(
                change_id=change_id,
                action=AuditAction.SYNC,
                target=AuditTarget.SCHEMA_REGISTRY,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Schema synchronization failed: {exc!s}",
            )
            raise
