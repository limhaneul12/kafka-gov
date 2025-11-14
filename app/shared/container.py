"""공통 DI 컨테이너 - 인프라스트럭처 의존성 관리"""

from __future__ import annotations

from dependency_injector import containers, providers

from app.shared.application.use_cases import (
    GetActivityHistoryUseCase,
    GetClusterStatusUseCase,
    GetRecentActivitiesUseCase,
)
from app.shared.infrastructure.repository import MySQLAuditActivityRepository

from .cache import init_redis
from .database import DatabaseManager
from .settings import settings


class InfrastructureContainer(containers.DeclarativeContainer):
    """인프라스트럭처 컨테이너 (DB만 관리)

    Note:
        Kafka/Schema Registry/MinIO는 DB 기반 동적 관리로 전환됨
        ConnectionManager가 cluster_id 기반으로 클라이언트를 생성/관리
    """

    infra_container = providers.Object(settings)

    # Cluster Container (외부 주입)
    cluster = providers.DependenciesContainer()

    # Database Manager - Singleton
    database_manager = providers.Singleton(
        DatabaseManager,
        database_url=infra_container.provided.database.url,
        echo=infra_container.provided.database.echo,
    )

    # Redis Client - Resource (자동 생명주기 관리)
    redis_client = providers.Resource(init_redis)

    # Repositories
    audit_activity_repository = providers.Factory(
        MySQLAuditActivityRepository,
        session_factory=database_manager.provided.get_db_session,
    )

    # Use Cases
    get_recent_activities_use_case = providers.Factory(
        GetRecentActivitiesUseCase,
        audit_repository=audit_activity_repository,
    )

    get_activity_history_use_case = providers.Factory(
        GetActivityHistoryUseCase,
        audit_repository=audit_activity_repository,
    )

    get_cluster_status_use_case = providers.Factory(
        GetClusterStatusUseCase,
        connection_manager=cluster.connection_manager,
    )
