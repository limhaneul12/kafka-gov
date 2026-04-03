"""Schema Registry → DB 동기화 유스케이스"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.kafka.connection_manager import IConnectionManager
from app.infra.kafka.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.application.services.catalog_sync import CatalogSyncService
from app.shared.actor import merge_actor_metadata
from app.shared.constants import AuditAction, AuditStatus, AuditTarget

from ....domain.models import DomainSchemaArtifact
from ....domain.repositories.interfaces import (
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
        session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] | None = None,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.session_factory = session_factory

    async def execute(
        self,
        registry_id: str,
        actor: str,
        actor_context: dict[str, str] | None = None,
    ) -> dict[str, dict[str, int] | int]:
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
            snapshot=merge_actor_metadata(None, actor_context),
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

            # 3. 각 subject의 최신 버전 정보 조회 (없으면 빈 dict)
            subjects_info = (
                await registry_repository.describe_subjects(all_subjects) if all_subjects else {}
            )

            # 4. DB에 artifact로 저장
            added_count = 0
            skipped_count = 0
            catalog_metrics: dict[str, int] | None = None

            for subject, info in subjects_info.items():
                from datetime import datetime

                artifact = DomainSchemaArtifact(
                    subject=subject,
                    version=info.version,
                    storage_url=f"registry://{subject}/versions/{info.version}",
                    checksum=info.hash,
                    created_at=datetime.now(),
                )

                try:
                    await self.metadata_repository.record_artifact(artifact, change_id)

                    # 메타데이터 자동 생성 (목록에 나타나도록)
                    await self.metadata_repository.save_schema_metadata(
                        subject,
                        {
                            "owner": "team",
                            "compatibility_mode": "BACKWARD",
                            "created_by": actor,
                            "updated_by": actor,
                        },
                    )
                    added_count += 1
                except Exception as e:
                    logger.warning(f"Failed to record artifact/meta for {subject}: {e}")
                    skipped_count += 1

            if self.session_factory is not None:
                async with self.session_factory() as session:
                    catalog_service = CatalogSyncService(sr_client=registry_client, session=session)
                    metrics = await catalog_service.sync_all()
                    catalog_metrics = {
                        "subjects_total": metrics.subjects_total,
                        "subjects_new": metrics.subjects_new,
                        "versions_total": metrics.versions_total,
                        "versions_new": metrics.versions_new,
                    }

            result = {
                "total": len(subjects_info),
                "added": added_count,
                "updated": skipped_count,
                "catalog": catalog_metrics
                or {
                    "subjects_total": 0,
                    "subjects_new": 0,
                    "versions_total": 0,
                    "versions_new": 0,
                },
            }

            await self.audit_repository.log_operation(
                change_id=change_id,
                action=AuditAction.SYNC,
                target=AuditTarget.SCHEMA_REGISTRY,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message=f"Schema synchronization completed: {result['total']} total, {result['added']} added",
                snapshot=merge_actor_metadata(result, actor_context),
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
                snapshot=merge_actor_metadata(None, actor_context),
            )
            raise
