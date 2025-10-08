"""Shared Infrastructure Repository (Session Factory 패턴)"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import desc, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Select

from app.schema.infrastructure.models import SchemaAuditLogModel
from app.shared.constants import ACTION_MESSAGES, ActivityType, AuditStatus
from app.shared.domain.models import AuditActivity
from app.shared.domain.repositories import IAuditActivityRepository
from app.topic.infrastructure.models import AuditLogModel

logger = logging.getLogger(__name__)

# TypeVar for audit log models
AuditLogT = TypeVar("AuditLogT", AuditLogModel, SchemaAuditLogModel)
ModelsToQuery = list[tuple[type[AuditLogModel] | type[SchemaAuditLogModel], str]]


def _subquery_log_model[AuditLogT: (AuditLogModel, SchemaAuditLogModel)](
    model: type[AuditLogT], activity_type: str
) -> Select[Any]:
    """활동 로그 서브쿼리 생성 (모델별)

    Args:
        model: Audit 로그 모델 클래스
        activity_type: 활동 타입 ("topic" or "schema")

    Returns:
        SQLAlchemy Select 쿼리 객체
    """
    return select(
        model.action,
        model.target,
        model.actor,
        model.team if hasattr(model, "team") else literal(None).label("team"),
        model.timestamp,
        model.message,
        model.snapshot,
        literal(activity_type).label("activity_type"),
    ).where(model.status == AuditStatus.COMPLETED)


def _get_models_to_query(activity_type: str | None) -> ModelsToQuery:
    """조회할 모델과 활동 타입 결정

    Args:
        activity_type: 필터링할 활동 타입 (None이면 전체)

    Returns:
        (모델 클래스, 활동 타입) 튜플 리스트
    """
    models: ModelsToQuery = []
    if not activity_type or activity_type == ActivityType.TOPIC:
        models.append((AuditLogModel, ActivityType.TOPIC))
    if not activity_type or activity_type == ActivityType.SCHEMA:
        models.append((SchemaAuditLogModel, ActivityType.SCHEMA))
    return models


class MySQLAuditActivityRepository(IAuditActivityRepository):
    """MySQL 기반 통합 감사 활동 리포지토리 (Session Factory 패턴)"""

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    async def get_recent_activities(self, limit: int) -> list[AuditActivity]:
        """최근 활동 조회 (Topic + Schema 통합) - UNION 쿼리 최적화"""
        async with self.session_factory() as session:
            # Topic 로그 서브쿼리
            topic_query = _subquery_log_model(AuditLogModel, ActivityType.TOPIC).limit(limit)

            # Schema 로그 서브쿼리
            schema_query = _subquery_log_model(SchemaAuditLogModel, ActivityType.SCHEMA).limit(
                limit
            )

            # UNION ALL로 통합하고 timestamp 기준 정렬
            combined_query = (
                topic_query.union_all(schema_query).order_by(desc("timestamp")).limit(limit)
            )

            result = await session.execute(combined_query)
            rows = result.fetchall()

            # 도메인 모델로 변환
            return [self._row_to_activity(row) for row in rows]

    @staticmethod
    def _row_to_activity(row) -> AuditActivity:
        """DB Row → AuditActivity 변환"""
        activity_type = row.activity_type
        action = row.action
        message = (
            row.message or ACTION_MESSAGES.get(activity_type, {}).get(action, action) or action
        )

        return AuditActivity(
            activity_type=activity_type,
            action=action,
            target=row.target,
            message=str(message),  # 명시적 문자열 변환
            actor=row.actor,
            team=row.team if hasattr(row, "team") else None,
            timestamp=row.timestamp,
            metadata=row.snapshot or {},
        )

    async def get_activity_history(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        activity_type: str | None = None,
        action: str | None = None,
        actor: str | None = None,
        limit: int = 100,
    ) -> list[AuditActivity]:
        """활동 히스토리 조회 (필터링 지원) - 개선된 쿼리"""
        async with self.session_factory() as session:
            # 조회할 모델과 타입 결정
            models_to_query: ModelsToQuery = _get_models_to_query(activity_type)

            # 각 모델별로 필터링된 쿼리 생성
            queries = [
                self._build_filtered_query(
                    model=model,
                    activity_type=act_type,
                    from_date=from_date,
                    to_date=to_date,
                    action=action,
                    actor=actor,
                    limit=limit,
                )
                for model, act_type in models_to_query
            ]

            # 쿼리가 없으면 빈 리스트 반환
            if not queries:
                return []

            # 단일 쿼리면 그대로, 복수면 UNION
            if len(queries) == 1:
                final_query = queries[0].order_by(desc("timestamp")).limit(limit)
            else:
                final_query = (
                    queries[0].union_all(queries[1]).order_by(desc("timestamp")).limit(limit)
                )

            result = await session.execute(final_query)
            rows = result.fetchall()

            return [self._row_to_activity(row) for row in rows]

    @staticmethod
    def _build_filtered_query(
        model,
        activity_type: str,
        from_date: datetime | None,
        to_date: datetime | None,
        action: str | None,
        actor: str | None,
        limit: int,
    ):
        """필터가 적용된 쿼리 빌드"""
        query = select(
            model.action,
            model.target,
            model.actor,
            model.team if hasattr(model, "team") else literal(None).label("team"),
            model.timestamp,
            model.message,
            model.snapshot,
            literal(activity_type).label("activity_type"),
        ).where(model.status == AuditStatus.COMPLETED)

        if from_date:
            query = query.where(model.timestamp >= from_date)
        if to_date:
            query = query.where(model.timestamp <= to_date)
        if action:
            query = query.where(model.action == action)
        if actor:
            query = query.where(model.actor.like(f"%{actor}%"))

        return query.limit(limit)
