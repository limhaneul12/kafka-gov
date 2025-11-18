"""Cluster 모듈 DI 컨테이너"""

from __future__ import annotations

from dependency_injector import containers, providers

from app.cluster.application.use_cases import (
    CreateKafkaClusterUseCase,
    CreateSchemaRegistryUseCase,
    DeleteKafkaClusterUseCase,
    DeleteSchemaRegistryUseCase,
    GetKafkaClusterUseCase,
    GetSchemaRegistryUseCase,
    ListKafkaClustersUseCase,
    ListSchemaRegistriesUseCase,
    TestKafkaConnectionUseCase,
    TestSchemaRegistryConnectionUseCase,
    UpdateKafkaClusterUseCase,
    UpdateSchemaRegistryUseCase,
)
from app.cluster.domain.services import ConnectionManager
from app.cluster.infrastructure.repositories import (
    MySQLKafkaClusterRepository,
    MySQLSchemaRegistryRepository,
)


class ClusterContainer(containers.DeclarativeContainer):
    """Cluster 모듈 DI 컨테이너

    Note:
        ConnectionManager는 Singleton으로 관리되며,
        다른 모듈(Topic/Schema)에서 주입받아 사용됨
    """

    # 인프라스트럭처 컨테이너 참조
    infrastructure = providers.DependenciesContainer()

    # Repositories (Session Factory 패턴)
    kafka_cluster_repository = providers.Factory(
        MySQLKafkaClusterRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    schema_registry_repository = providers.Factory(
        MySQLSchemaRegistryRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    # ConnectionManager (Singleton) - 핵심 Domain Service
    # 다른 모듈에서 이것을 주입받아 동적 클라이언트 생성
    connection_manager = providers.Singleton(
        ConnectionManager,
        kafka_cluster_repo=kafka_cluster_repository,
        schema_registry_repo=schema_registry_repository,
    )

    # ========================================================================
    # Kafka Cluster Use Cases
    # ========================================================================

    create_kafka_cluster_use_case = providers.Factory(
        CreateKafkaClusterUseCase,
        cluster_repo=kafka_cluster_repository,
        connection_manager=connection_manager,
    )

    list_kafka_clusters_use_case = providers.Factory(
        ListKafkaClustersUseCase,
        cluster_repo=kafka_cluster_repository,
    )

    get_kafka_cluster_use_case = providers.Factory(
        GetKafkaClusterUseCase,
        cluster_repo=kafka_cluster_repository,
    )

    update_kafka_cluster_use_case = providers.Factory(
        UpdateKafkaClusterUseCase,
        cluster_repo=kafka_cluster_repository,
        connection_manager=connection_manager,
    )

    delete_kafka_cluster_use_case = providers.Factory(
        DeleteKafkaClusterUseCase,
        cluster_repo=kafka_cluster_repository,
        connection_manager=connection_manager,
    )

    test_kafka_connection_use_case = providers.Factory(
        TestKafkaConnectionUseCase,
        connection_manager=connection_manager,
    )

    # ========================================================================
    # Schema Registry Use Cases
    # ========================================================================

    create_schema_registry_use_case = providers.Factory(
        CreateSchemaRegistryUseCase,
        registry_repo=schema_registry_repository,
        connection_manager=connection_manager,
    )

    list_schema_registries_use_case = providers.Factory(
        ListSchemaRegistriesUseCase,
        registry_repo=schema_registry_repository,
    )

    get_schema_registry_use_case = providers.Factory(
        GetSchemaRegistryUseCase,
        registry_repo=schema_registry_repository,
    )

    update_schema_registry_use_case = providers.Factory(
        UpdateSchemaRegistryUseCase,
        registry_repo=schema_registry_repository,
        connection_manager=connection_manager,
    )

    delete_schema_registry_use_case = providers.Factory(
        DeleteSchemaRegistryUseCase,
        registry_repo=schema_registry_repository,
        connection_manager=connection_manager,
    )

    test_schema_registry_connection_use_case = providers.Factory(
        TestSchemaRegistryConnectionUseCase,
        connection_manager=connection_manager,
    )
