"""Shared Infrastructure Repository (Session Factory 패턴)"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Any, TypeVar

from sqlalchemy import desc, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Select

from app.schema.infrastructure.models import SchemaAuditLogModel
from app.shared.constants import ACTION_MESSAGES, ActivityType, AuditAction, AuditStatus
from app.shared.domain.models import ApprovalRequest, AuditActivity
from app.shared.domain.repositories import IApprovalRequestRepository, IAuditActivityRepository
from app.shared.infrastructure.models import ApprovalRequestModel
from app.topic.infrastructure.models import AuditLogModel

logger = logging.getLogger(__name__)

# TypeVar for audit log models
AuditLogT = TypeVar("AuditLogT", AuditLogModel, SchemaAuditLogModel)
ModelsToQuery = list[
    tuple[type[AuditLogModel] | type[SchemaAuditLogModel] | type[ApprovalRequestModel], str]
]


VISIBLE_AUDIT_STATUSES = (AuditStatus.COMPLETED, AuditStatus.PARTIALLY_COMPLETED)


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
    # team 컬럼 존재 여부 확인 후 분기
    try:
        team_col = getattr(model, "team", literal(None).label("team"))
    except AttributeError:
        team_col = literal(None).label("team")

    return select(
        model.action,
        model.target,
        model.actor,
        team_col,
        model.timestamp,
        model.message,
        model.snapshot,
        literal(activity_type).label("activity_type"),
        literal(None).label("request_id"),
        literal(None).label("resource_type"),
        literal(None).label("change_type"),
        literal(None).label("change_ref"),
        literal(None).label("approver"),
        literal(None).label("decision_reason"),
    ).where(model.status.in_(VISIBLE_AUDIT_STATUSES))


def _approval_request_query() -> Select[Any]:
    return select(
        ApprovalRequestModel.status.label("action"),
        ApprovalRequestModel.resource_name.label("target"),
        ApprovalRequestModel.requested_by.label("actor"),
        literal(None).label("team"),
        ApprovalRequestModel.requested_at.label("timestamp"),
        ApprovalRequestModel.summary.label("message"),
        ApprovalRequestModel.metadata_json.label("snapshot"),
        literal(ActivityType.APPROVAL).label("activity_type"),
        ApprovalRequestModel.request_id.label("request_id"),
        ApprovalRequestModel.resource_type.label("resource_type"),
        ApprovalRequestModel.change_type.label("change_type"),
        ApprovalRequestModel.change_ref.label("change_ref"),
        ApprovalRequestModel.approver.label("approver"),
        ApprovalRequestModel.decision_reason.label("decision_reason"),
    )


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
    if not activity_type or activity_type == ActivityType.APPROVAL:
        models.append((ApprovalRequestModel, ActivityType.APPROVAL))
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
            topic_query = _subquery_log_model(AuditLogModel, ActivityType.TOPIC)
            schema_query = _subquery_log_model(SchemaAuditLogModel, ActivityType.SCHEMA)
            approval_query = _approval_request_query()
            combined_query = (
                union_all(topic_query, schema_query, approval_query)
                .order_by(desc("timestamp"))
                .limit(limit)
            )

            result = await session.execute(combined_query)
            rows = result.fetchall()

            # 도메인 모델로 변환
            return [self._row_to_activity(row) for row in rows]

    @staticmethod
    def _row_to_activity(row) -> AuditActivity:
        """DB Row → AuditActivity 변환"""
        activity_type = row.activity_type
        action = MySQLAuditActivityRepository._normalize_action(activity_type, row.action)
        message = (
            row.message or ACTION_MESSAGES.get(activity_type, {}).get(action, action) or action
        )

        metadata = row.snapshot or {}
        if activity_type == ActivityType.APPROVAL:
            metadata = {
                **(metadata if isinstance(metadata, dict) else {}),
                "approval_request": {
                    "request_id": row.request_id,
                    "resource_type": row.resource_type,
                    "change_type": row.change_type,
                    "change_ref": row.change_ref,
                    "status": row.action,
                    "requested_by": row.actor,
                    "approver": row.approver,
                    "decision_reason": row.decision_reason,
                },
            }

        return AuditActivity(
            activity_type=activity_type,
            action=action,
            target=row.target,
            message=str(message),  # 명시적 문자열 변환
            actor=row.actor,
            team=row.team if hasattr(row, "team") else None,
            timestamp=row.timestamp,
            metadata=metadata,
        )

    @staticmethod
    def _normalize_action(activity_type: str, action: str) -> str:
        if activity_type != ActivityType.APPROVAL:
            return action

        approval_status_map = {
            "pending": AuditAction.REQUESTED,
            "approved": AuditAction.APPROVED,
            "rejected": AuditAction.REJECTED,
        }
        return approval_status_map.get(action.lower(), action.upper())

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
                final_query = union_all(*queries).order_by(desc("timestamp")).limit(limit)

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
        if model is ApprovalRequestModel:
            query = _approval_request_query()
            if from_date:
                query = query.where(ApprovalRequestModel.requested_at >= from_date)
            if to_date:
                query = query.where(ApprovalRequestModel.requested_at <= to_date)
            if action:
                query = query.where(ApprovalRequestModel.status.ilike(action))
            if actor:
                query = query.where(ApprovalRequestModel.requested_by.like(f"%{actor}%"))
            return query

        query = select(
            model.action,
            model.target,
            model.actor,
            model.team if hasattr(model, "team") else literal(None).label("team"),
            model.timestamp,
            model.message,
            model.snapshot,
            literal(activity_type).label("activity_type"),
            literal(None).label("request_id"),
            literal(None).label("resource_type"),
            literal(None).label("change_type"),
            literal(None).label("change_ref"),
            literal(None).label("approver"),
            literal(None).label("decision_reason"),
        ).where(model.status.in_(VISIBLE_AUDIT_STATUSES))

        if from_date:
            query = query.where(model.timestamp >= from_date)
        if to_date:
            query = query.where(model.timestamp <= to_date)
        if action:
            query = query.where(model.action == action)
        if actor:
            query = query.where(model.actor.like(f"%{actor}%"))

        return query


class SQLApprovalRequestRepository(IApprovalRequestRepository):
    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        async with self.session_factory() as session:
            model = ApprovalRequestModel(
                request_id=request.request_id,
                resource_type=request.resource_type,
                resource_name=request.resource_name,
                change_type=request.change_type,
                change_ref=request.change_ref,
                summary=request.summary,
                justification=request.justification,
                requested_by=request.requested_by,
                status=request.status,
                approver=request.approver,
                decision_reason=request.decision_reason,
                metadata_json=request.metadata,
                requested_at=request.requested_at,
                decided_at=request.decided_at,
            )
            session.add(model)
            await session.flush()
            await session.refresh(model)
            return self._to_domain(model)

    async def get(self, request_id: str) -> ApprovalRequest | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ApprovalRequestModel).where(ApprovalRequestModel.request_id == request_id)
            )
            model = result.scalar_one_or_none()
            return self._to_domain(model) if model is not None else None

    async def list(
        self,
        *,
        status: str | None = None,
        resource_type: str | None = None,
        requested_by: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        async with self.session_factory() as session:
            query = select(ApprovalRequestModel).order_by(desc(ApprovalRequestModel.requested_at))
            if status:
                query = query.where(ApprovalRequestModel.status == status)
            if resource_type:
                query = query.where(ApprovalRequestModel.resource_type == resource_type)
            if requested_by:
                query = query.where(ApprovalRequestModel.requested_by.like(f"%{requested_by}%"))
            result = await session.execute(query.limit(limit))
            return [self._to_domain(model) for model in result.scalars().all()]

    async def update_status(
        self,
        *,
        request_id: str,
        status: str,
        approver: str,
        decision_reason: str | None,
    ) -> ApprovalRequest:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ApprovalRequestModel).where(ApprovalRequestModel.request_id == request_id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                raise ValueError(f"approval request not found: {request_id}")
            model.status = status
            model.approver = approver
            model.decision_reason = decision_reason
            model.decided_at = datetime.now(UTC)
            await session.flush()
            await session.refresh(model)
            return self._to_domain(model)

    @staticmethod
    def _to_domain(model: ApprovalRequestModel) -> ApprovalRequest:
        return ApprovalRequest(
            request_id=model.request_id,
            resource_type=model.resource_type,
            resource_name=model.resource_name,
            change_type=model.change_type,
            change_ref=model.change_ref,
            summary=model.summary,
            justification=model.justification,
            requested_by=model.requested_by,
            status=model.status,
            approver=model.approver,
            decision_reason=model.decision_reason,
            metadata=model.metadata_json,
            requested_at=model.requested_at,
            decided_at=model.decided_at,
        )
