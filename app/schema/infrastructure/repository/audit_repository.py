"""Schema Audit Repository 구현체"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schema.domain.models import ChangeId, SubjectName
from app.schema.domain.repositories.interfaces import ISchemaAuditRepository
from app.schema.infrastructure.models import SchemaAuditLogModel

logger = logging.getLogger(__name__)


class MySQLSchemaAuditRepository(ISchemaAuditRepository):
    """MySQL 기반 스키마 감사 로그 리포지토리"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_operation(
        self,
        change_id: ChangeId,
        action: str,
        target: SubjectName,
        actor: str,
        status: str,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> str:
        """감사 로그 기록"""
        try:
            audit_log = SchemaAuditLogModel(
                change_id=change_id,
                action=action,
                target=target,
                actor=actor,
                status=status,
                message=message,
                snapshot=snapshot,
            )

            self.session.add(audit_log)
            await self.session.flush()

            log_id = str(audit_log.id)
            logger.info(
                f"Schema audit log recorded: {log_id} - {action} {target} by {actor} ({status})"
            )

            return log_id

        except Exception as e:
            logger.error(f"Failed to record schema audit log: {e}")
            raise
