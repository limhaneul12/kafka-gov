"""스키마 이력 조회 유스케이스"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.cluster.domain.services import IConnectionManager
from app.schema.domain.models import (
    SchemaHistoryItem,
    SubjectHistory,
    SubjectName,
)
from app.schema.domain.repositories.interfaces import (
    ISchemaMetadataRepository,
)
from app.schema.infrastructure.models import SchemaArtifactModel, SchemaAuditLogModel
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter


class GetSchemaHistoryUseCase:
    """스키마 이력 조회 (타임머신)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.logger = logging.getLogger(__name__)

    async def execute(self, registry_id: str, subject: SubjectName) -> SubjectHistory:
        """스키마 이력 조회 (타임머신)"""
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

        versions = await registry_repository.get_schema_versions(subject)

        # DB에서 아티팩트 및 감사 로그 조회 (작성자, 시간 등)
        async with self.metadata_repository.session_factory() as session:
            # 아티팩트 조회
            stmt_art = select(SchemaArtifactModel).where(SchemaArtifactModel.subject == subject)
            res_art = await session.execute(stmt_art)
            artifact_models = {a.version: a for a in res_art.scalars().all()}

            # 감사 로그 조회 (작성자 추론용)
            stmt_audit = select(SchemaAuditLogModel).where(SchemaAuditLogModel.target == subject)
            res_audit = await session.execute(stmt_audit)
            audit_logs = {log.change_id: log.actor for log in res_audit.scalars().all()}

        # 각 버전별 상세 조회 (병렬)
        tasks = [registry_repository.get_schema_by_version(subject, v) for v in versions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        history_items = []
        for result in results:
            if isinstance(result, Exception):
                continue

            # DB 정보 매핑
            db_info = artifact_models.get(result.version)
            author = "system"
            if db_info and db_info.change_id in audit_logs:
                author = audit_logs[db_info.change_id]

            history_items.append(
                SchemaHistoryItem(
                    version=result.version,
                    schema_id=result.schema_id,
                    created_at=db_info.created_at.isoformat()
                    if db_info and db_info.created_at
                    else None,
                    diff_type="UPDATE" if result.version > 1 else "CREATE",
                    author=author,
                    commit_message=f"Schema update v{result.version}",
                )
            )

        return SubjectHistory(
            subject=subject, history=sorted(history_items, key=lambda x: x.version, reverse=True)
        )
