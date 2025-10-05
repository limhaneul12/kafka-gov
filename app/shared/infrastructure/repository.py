"""Shared Infrastructure Repository (Session Factory 패턴)"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import TypeVar

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schema.infrastructure.models import SchemaAuditLogModel
from app.shared.domain.models import AuditActivity
from app.shared.domain.repositories import IAuditActivityRepository
from app.topic.infrastructure.models import AuditLogModel

logger = logging.getLogger(__name__)

# TypeVar for audit log models
AuditLogT = TypeVar("AuditLogT", AuditLogModel, SchemaAuditLogModel)


async def select_recent_audit_logs(
    session: AsyncSession, limit: int, model: type[AuditLogT]
) -> list[AuditLogT]:
    query = (
        select(model)
        .where(model.status == "COMPLETED")
        .order_by(desc(model.timestamp))
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


class MySQLAuditActivityRepository(IAuditActivityRepository):
    """MySQL 기반 통합 감사 활동 리포지토리 (Session Factory 패턴)"""

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    async def get_recent_activities(self, limit: int) -> list[AuditActivity]:
        """최근 활동 조회 (Topic + Schema 통합)"""
        async with self.session_factory() as session:
            topic_logs = await select_recent_audit_logs(session, limit, AuditLogModel)

            # Schema Audit 조회
            schema_logs = await select_recent_audit_logs(session, limit, SchemaAuditLogModel)

            # AuditActivity 도메인 모델로 변환
            activities: list[AuditActivity] = [
                AuditActivity(
                    activity_type="topic",
                    action=log.action,
                    target=log.target,
                    message=log.message or self._format_topic_message(log.action),
                    actor=log.actor,
                    timestamp=log.timestamp,
                    metadata=log.snapshot or {},
                )
                for log in topic_logs
            ]

            activities.extend(
                AuditActivity(
                    activity_type="schema",
                    action=log.action,
                    target=log.target,
                    message=log.message or self._format_schema_message(log.action),
                    actor=log.actor,
                    timestamp=log.timestamp,
                    metadata=log.snapshot or {},
                )
                for log in schema_logs
            )

            # 시간 역순 정렬
            activities.sort(key=lambda x: x.timestamp, reverse=True)

            return activities[:limit]

    @staticmethod
    def _format_topic_message(action: str) -> str:
        """토픽 활동 메시지 포맷"""
        action_map = {
            "CREATE": "생성됨",
            "UPDATE": "수정됨",
            "DELETE": "삭제됨",
            "DRY_RUN": "검증됨",
            "APPLY": "적용됨",
        }
        return action_map.get(action, action)

    @staticmethod
    def _format_schema_message(action: str) -> str:
        """스키마 활동 메시지 포맷"""
        action_map = {
            "REGISTER": "등록됨",
            "UPLOAD": "업로드됨",
            "UPDATE": "업데이트됨",
            "DELETE": "삭제됨",
            "DRY_RUN": "검증됨",
            "APPLY": "적용됨",
        }
        return action_map.get(action, action)
