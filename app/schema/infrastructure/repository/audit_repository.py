"""Schema Audit Repository 구현체 (Session Factory 패턴)"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schema.domain.models import ChangeId, SubjectName
from app.schema.domain.repositories.interfaces import ISchemaAuditRepository
from app.schema.infrastructure.models import SchemaAuditLogModel

logger = logging.getLogger(__name__)


class MySQLSchemaAuditRepository(ISchemaAuditRepository):
    """MySQL 기반 스키마 감사 로그 리포지토리 (Session Factory 패턴)

    각 메서드가 session_factory를 통해 독립적으로 session을 생성하고 관리합니다.
    Transaction 경계가 명확하며, context manager가 자동으로 commit/rollback을 처리합니다.
    """

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

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
        async with self.session_factory() as session:
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

                session.add(audit_log)
                await session.flush()

                log_id = str(audit_log.id)
                logger.info(
                    f"Schema audit log recorded: {log_id} - {action} {target} by {actor} ({status})"
                )

                return log_id

            except Exception as e:
                logger.error(f"Failed to record schema audit log: {e}")
                raise
