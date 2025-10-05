"""Shared Infrastructure Repository (Session Factory 패턴)"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime
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


async def select_recent_audit_logs[AuditLogT: (AuditLogModel, SchemaAuditLogModel)](
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

    async def get_activity_history(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        activity_type: str | None = None,
        action: str | None = None,
        actor: str | None = None,
        limit: int = 100,
    ) -> list[AuditActivity]:
        """활동 히스토리 조회 (필터링 지원)"""
        async with self.session_factory() as session:
            # 토픽 활동 조회
            topic_activities = []
            if not activity_type or activity_type == "topic":
                topic_query = select(AuditLogModel).where(AuditLogModel.status == "COMPLETED")

                # 날짜 필터
                if from_date:
                    topic_query = topic_query.where(AuditLogModel.timestamp >= from_date)
                if to_date:
                    topic_query = topic_query.where(AuditLogModel.timestamp <= to_date)

                # 액션 필터
                if action:
                    topic_query = topic_query.where(AuditLogModel.action == action)

                # 수행자 필터
                if actor:
                    topic_query = topic_query.where(AuditLogModel.actor.like(f"%{actor}%"))

                topic_query = topic_query.order_by(desc(AuditLogModel.timestamp)).limit(limit)

                result = await session.execute(topic_query)
                topic_logs = result.scalars().all()

                topic_activities = [
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

            # 스키마 활동 조회
            schema_activities = []
            if not activity_type or activity_type == "schema":
                schema_query = select(SchemaAuditLogModel).where(
                    SchemaAuditLogModel.status == "COMPLETED"
                )

                # 날짜 필터
                if from_date:
                    schema_query = schema_query.where(SchemaAuditLogModel.timestamp >= from_date)
                if to_date:
                    schema_query = schema_query.where(SchemaAuditLogModel.timestamp <= to_date)

                # 액션 필터
                if action:
                    schema_query = schema_query.where(SchemaAuditLogModel.action == action)

                # 수행자 필터
                if actor:
                    schema_query = schema_query.where(SchemaAuditLogModel.actor.like(f"%{actor}%"))

                schema_query = schema_query.order_by(desc(SchemaAuditLogModel.timestamp)).limit(
                    limit
                )

                result = await session.execute(schema_query)
                schema_logs = result.scalars().all()

                schema_activities = [
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
                ]

            # 병합 및 정렬
            all_activities = topic_activities + schema_activities
            all_activities.sort(key=lambda x: x.timestamp, reverse=True)

            return all_activities[:limit]
