"""Kafka Connect Container - Dependency Injection"""

from __future__ import annotations

from dependency_injector import containers, providers

from app.connect.application.metadata_use_cases import (
    DeleteConnectorMetadataUseCase,
    GetConnectorMetadataUseCase,
    ListConnectorsByTeamUseCase,
    UpdateConnectorMetadataUseCase,
)
from app.connect.application.use_cases import (
    ConnectorOperations,
    ConnectorStateControl,
    ListConnectorsUseCase,
    PluginOperations,
    TaskOperations,
    TopicOperations,
)
from app.connect.infrastructure.repositories import MySQLConnectorMetadataRepository


class ConnectContainer(containers.DeclarativeContainer):
    """Kafka Connect 모듈 컨테이너"""

    connect_repository = providers.Dependency()
    database_manager = providers.Dependency()

    connector_metadata_repository = providers.Factory(
        MySQLConnectorMetadataRepository,
        session_factory=database_manager.provided.get_db_session,
    )

    list_connectors_use_case = providers.Factory(
        ListConnectorsUseCase,
        connect_repo=connect_repository,
        metadata_repo=connector_metadata_repository,
    )

    connector_operations = providers.Factory(
        ConnectorOperations,
        connect_repo=connect_repository,
    )

    connector_state_control = providers.Factory(
        ConnectorStateControl,
        connect_repo=connect_repository,
    )

    task_operations = providers.Factory(
        TaskOperations,
        connect_repo=connect_repository,
    )

    plugin_operations = providers.Factory(
        PluginOperations,
        connect_repo=connect_repository,
    )

    topic_operations = providers.Factory(
        TopicOperations,
        connect_repo=connect_repository,
    )

    get_connector_metadata_use_case = providers.Factory(
        GetConnectorMetadataUseCase,
        metadata_repo=connector_metadata_repository,
    )

    update_connector_metadata_use_case = providers.Factory(
        UpdateConnectorMetadataUseCase,
        metadata_repo=connector_metadata_repository,
    )

    delete_connector_metadata_use_case = providers.Factory(
        DeleteConnectorMetadataUseCase,
        metadata_repo=connector_metadata_repository,
    )

    list_connectors_by_team_use_case = providers.Factory(
        ListConnectorsByTeamUseCase,
        metadata_repo=connector_metadata_repository,
    )
