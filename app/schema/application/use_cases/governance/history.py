"""스키마 이력 조회 유스케이스"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.kafka.connection_manager import IConnectionManager
from app.infra.kafka.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.domain.models import (
    SchemaHistoryItem,
    SchemaVersionInfo,
    SubjectHistory,
    SubjectName,
)
from app.schema.domain.repositories.interfaces import (
    ISchemaMetadataRepository,
)
from app.schema.infrastructure.models import (
    SchemaArtifactModel,
    SchemaAuditLogModel,
    SchemaPlanModel,
)


class _MetadataRepositoryWithSessionFactory(Protocol):
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]]


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
        metadata_repository = cast(
            _MetadataRepositoryWithSessionFactory,
            cast(object, self.metadata_repository),
        )
        session_factory = metadata_repository.session_factory
        async with session_factory() as session:
            # 아티팩트 조회
            stmt_art = select(SchemaArtifactModel).where(SchemaArtifactModel.subject == subject)
            res_art = await session.execute(stmt_art)
            artifacts = res_art.scalars().all()
            artifact_models = {a.version: a for a in artifacts}
            change_ids = {artifact.change_id for artifact in artifacts if artifact.change_id}

            audit_logs: dict[str, str] = {}
            plan_reasons: dict[tuple[str, str], str] = {}

            if change_ids:
                stmt_audit = select(SchemaAuditLogModel).where(
                    SchemaAuditLogModel.change_id.in_(change_ids)
                )
                res_audit = await session.execute(stmt_audit)
                audit_logs = {log.change_id: log.actor for log in res_audit.scalars().all()}

                stmt_plan = select(SchemaPlanModel).where(SchemaPlanModel.change_id.in_(change_ids))
                res_plan = await session.execute(stmt_plan)
                for plan_model in res_plan.scalars().all():
                    items = plan_model.plan_data.get("items", []) if plan_model.plan_data else []
                    for item in items:
                        item_subject = item.get("subject")
                        reason = item.get("reason")
                        if isinstance(item_subject, str) and isinstance(reason, str) and reason:
                            plan_reasons[(plan_model.change_id, item_subject)] = reason

        # 각 버전별 상세 조회 (병렬)
        tasks = [registry_repository.get_schema_by_version(subject, v) for v in versions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        history_items = []
        for result in results:
            if not isinstance(result, SchemaVersionInfo):
                continue

            if result.version is None or result.schema_id is None:
                continue

            # DB 정보 매핑
            db_info = artifact_models.get(result.version)
            author = "system"
            if db_info and db_info.change_id in audit_logs:
                author = audit_logs[db_info.change_id]
            commit_message = None
            if db_info is not None:
                commit_message = plan_reasons.get((db_info.change_id, subject))

            history_items.append(
                SchemaHistoryItem(
                    version=result.version,
                    schema_id=result.schema_id,
                    created_at=db_info.created_at.isoformat()
                    if db_info and db_info.created_at
                    else None,
                    diff_type="UPDATE" if result.version > 1 else "CREATE",
                    author=author,
                    commit_message=commit_message,
                )
            )

        return SubjectHistory(
            subject=subject, history=sorted(history_items, key=lambda x: x.version, reverse=True)
        )
