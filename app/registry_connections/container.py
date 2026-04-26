"""Schema Registry connection DI container."""

from __future__ import annotations

from dependency_injector import containers, providers

from app.infra.kafka.connection_manager import ConnectionManager
from app.registry_connections.application.use_cases import (
    CreateSchemaRegistryUseCase,
    DeleteSchemaRegistryUseCase,
    GetSchemaRegistryUseCase,
    ListSchemaRegistriesUseCase,
    TestSchemaRegistryConnectionUseCase,
    UpdateSchemaRegistryUseCase,
)
from app.registry_connections.infrastructure.repositories import MySQLSchemaRegistryRepository


class RegistryConnectionContainer(containers.DeclarativeContainer):
    """Schema Registry connection DI container."""

    infrastructure = providers.DependenciesContainer()

    schema_registry_repository = providers.Factory(
        MySQLSchemaRegistryRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    connection_manager = providers.Singleton(
        ConnectionManager,
        schema_registry_repo=schema_registry_repository,
    )

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
