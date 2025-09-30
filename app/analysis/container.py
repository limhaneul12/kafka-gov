"""Analysis Container - Dependency Injection"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..shared.infrastructure.event_bus import get_event_bus
from .application.event_handlers import SchemaRegisteredHandler, TopicCreatedHandler
from .application.queries import CorrelationQueryService, ImpactAnalysisQueryService
from .domain.services import TopicSchemaLinker
from .infrastructure.mysql_repository import (
    MySQLCorrelationRepository,
    MySQLImpactAnalysisRepository,
)


def get_correlation_query_service(session: AsyncSession) -> CorrelationQueryService:
    """상관관계 조회 서비스 팩토리"""
    correlation_repo = MySQLCorrelationRepository(session)
    return CorrelationQueryService(correlation_repo)


def get_impact_analysis_service(session: AsyncSession) -> ImpactAnalysisQueryService:
    """영향도 분석 서비스 팩토리"""
    correlation_repo = MySQLCorrelationRepository(session)
    impact_repo = MySQLImpactAnalysisRepository(session)
    return ImpactAnalysisQueryService(correlation_repo, impact_repo)


def register_event_handlers(session: AsyncSession) -> None:
    """이벤트 핸들러 등록"""
    event_bus = get_event_bus()

    # Repository 생성
    correlation_repo = MySQLCorrelationRepository(session)

    # Service 생성
    linker = TopicSchemaLinker(correlation_repo)

    # Handler 생성 및 등록
    schema_handler = SchemaRegisteredHandler(linker)
    topic_handler = TopicCreatedHandler(linker)

    event_bus.subscribe("schema.registered", schema_handler.handle)
    event_bus.subscribe("topic.created", topic_handler.handle)
