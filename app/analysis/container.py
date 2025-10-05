"""Analysis Container - Dependency Injection (Session Factory 패턴)"""

from __future__ import annotations

from dependency_injector import containers, providers

from .application.queries import CorrelationQueryService, ImpactAnalysisQueryService
from .domain.services import TopicSchemaLinker
from .infrastructure.mysql_repository import (
    MySQLCorrelationRepository,
    MySQLImpactAnalysisRepository,
)


class AnalysisContainer(containers.DeclarativeContainer):
    """Analysis 모듈 DI 컨테이너"""

    # 인프라스트럭처 컨테이너 참조
    infrastructure = providers.DependenciesContainer()

    # Repositories (Session Factory 패턴)
    correlation_repository = providers.Factory(
        MySQLCorrelationRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    impact_analysis_repository = providers.Factory(
        MySQLImpactAnalysisRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    # Services
    topic_schema_linker = providers.Factory(
        TopicSchemaLinker, correlation_repo=correlation_repository
    )

    # Query Services
    correlation_query_service = providers.Factory(
        CorrelationQueryService,
        correlation_repo=correlation_repository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    impact_analysis_query_service = providers.Factory(
        ImpactAnalysisQueryService,
        correlation_repo=correlation_repository,
        impact_repo=impact_analysis_repository,
    )
