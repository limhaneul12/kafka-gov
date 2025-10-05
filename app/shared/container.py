"""공통 DI 컨테이너 - 인프라스트럭처 의존성 관리"""

from __future__ import annotations

from dependency_injector import containers, providers

from app.schema.infrastructure.storage.minio_adapter import create_minio_client
from app.shared.application.use_cases import GetClusterStatusUseCase, GetRecentActivitiesUseCase
from app.shared.infrastructure.cluster_repository import KafkaClusterRepository
from app.shared.infrastructure.repository import MySQLAuditActivityRepository

from .database import DatabaseManager
from .settings import (
    create_kafka_admin_client,
    create_schema_registry_client,
    settings,
)


class InfrastructureContainer(containers.DeclarativeContainer):
    infra_container = providers.Object(settings)

    # Database Manager - Singleton
    database_manager = providers.Singleton(
        DatabaseManager,
        database_url=infra_container.provided.database.url,
        echo=infra_container.provided.database.echo,
    )

    # Kafka AdminClient - Singleton
    kafka_admin_client = providers.Singleton(
        create_kafka_admin_client,
        bootstrap_servers=infra_container.provided.kafka.bootstrap_servers,
    )

    # Schema Registry Client - Singleton
    schema_registry_client = providers.Singleton(
        create_schema_registry_client,
        config=infra_container.provided.schema_registry.client_config,
    )

    # MinIO Client - Singleton
    minio_client = providers.Singleton(
        create_minio_client,
        endpoint=infra_container.provided.storage.endpoint_url,
        access_key=infra_container.provided.storage.access_key,
        secret_key=infra_container.provided.storage.secret_key,
        secure=infra_container.provided.storage.use_ssl,
    )

    # MinIO 설정값 노출 (SchemaContainer에서 사용)
    bucket_name = infra_container.provided.storage.bucket_name
    endpoint_url = infra_container.provided.storage.endpoint_url

    # Repositories
    audit_activity_repository = providers.Factory(
        MySQLAuditActivityRepository,
        session_factory=database_manager.provided.get_db_session,
    )

    cluster_repository = providers.Factory(
        KafkaClusterRepository,
        admin_client=kafka_admin_client,
    )

    # Use Cases
    get_recent_activities_use_case = providers.Factory(
        GetRecentActivitiesUseCase,
        audit_repository=audit_activity_repository,
    )

    get_cluster_status_use_case = providers.Factory(
        GetClusterStatusUseCase,
        cluster_repository=cluster_repository,
    )
