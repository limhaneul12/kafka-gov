"""Audit Repository MySQL 구현체"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db_session
from app.topic.domain.models import ChangeId, TopicName
from app.topic.domain.repositories.interfaces import IAuditRepository
from app.topic.infrastructure.models import AuditLogModel

logger = logging.getLogger(__name__)


class MySQLAuditRepository(IAuditRepository):
    """MySQL 기반 감사 로그 리포지토리"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_topic_operation(
        self,
        change_id: ChangeId,
        action: str,
        target: TopicName,
        actor: str,
        status: str,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> str:
        """토픽 작업 감사 로그 기록"""
        try:
            audit_log = AuditLogModel(
                change_id=change_id,
                action=action,
                target=target,
                actor=actor,
                status=status,
                message=message,
                snapshot=snapshot or {},
            )

            self.session.add(audit_log)
            await self.session.flush()

            log_id = str(audit_log.id)
            logger.info(f"Audit log created: {log_id} - {action} on {target} by {actor}")

            return log_id

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            raise


# 의존성 주입용 팩토리 함수
async def get_mysql_audit_repository() -> MySQLAuditRepository:
    """MySQL 감사 리포지토리 팩토리"""
    async with get_db_session() as session:
        return MySQLAuditRepository(session)
