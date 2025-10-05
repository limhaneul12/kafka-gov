"""Schema 모듈 DI 컨테이너"""

from __future__ import annotations

from dependency_injector import containers, providers

from .application.use_cases import (
    SchemaBatchApplyUseCase,
    SchemaBatchDryRunUseCase,
    SchemaDeleteUseCase,
    SchemaPlanUseCase,
    SchemaSyncUseCase,
    SchemaUploadUseCase,
)
from .domain.policies import SchemaPolicyEngine
from .domain.repositories.interfaces import (
    IObjectStorageRepository,
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaRegistryRepository,
)
from .infrastructure.repository.audit_repository import MySQLSchemaAuditRepository
from .infrastructure.repository.mysql_repository import MySQLSchemaMetadataRepository
from .infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from .infrastructure.storage.minio_adapter import create_minio_storage_adapter


class SchemaContainer(containers.DeclarativeContainer):
    """Schema 모듈 DI 컨테이너"""

    # 인프라스트럭처 컨테이너 참조
    infrastructure = providers.DependenciesContainer()

    # Analysis 컨테이너 참조 (correlation_repository 사용)
    analysis = providers.DependenciesContainer()

    # Repositories
    schema_registry_repository: providers.Provider[ISchemaRegistryRepository] = providers.Singleton(
        ConfluentSchemaRegistryAdapter,
        client=infrastructure.schema_registry_client,
    )

    # MySQL 기반 구현체들 (Session Factory 패턴)
    metadata_repository: providers.Provider[ISchemaMetadataRepository] = providers.Factory(
        MySQLSchemaMetadataRepository,  # type: ignore[arg-type]
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    audit_repository: providers.Provider[ISchemaAuditRepository] = providers.Factory(
        MySQLSchemaAuditRepository,  # type: ignore[arg-type]
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    # Object Storage (MinIO)
    object_storage_repository: providers.Provider[IObjectStorageRepository] = providers.Singleton(
        create_minio_storage_adapter,
        client=infrastructure.minio_client,
        bucket_name=infrastructure.bucket_name,
        base_url=infrastructure.endpoint_url,
    )

    # Domain Services
    policy_engine: providers.Provider[SchemaPolicyEngine] = providers.Singleton(SchemaPolicyEngine)

    # Use Cases
    dry_run_use_case: providers.Provider[SchemaBatchDryRunUseCase] = providers.Factory(
        SchemaBatchDryRunUseCase,
        registry_repository=schema_registry_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_engine=policy_engine,
    )

    apply_use_case: providers.Provider[SchemaBatchApplyUseCase] = providers.Factory(
        SchemaBatchApplyUseCase,
        registry_repository=schema_registry_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        storage_repository=object_storage_repository,
        policy_engine=policy_engine,
    )

    plan_use_case: providers.Provider[SchemaPlanUseCase] = providers.Factory(
        SchemaPlanUseCase,
        metadata_repository=metadata_repository,
    )

    upload_use_case: providers.Provider[SchemaUploadUseCase] = providers.Factory(
        SchemaUploadUseCase,
        storage_repository=object_storage_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        registry_repository=schema_registry_repository,
    )

    delete_analysis_use_case: providers.Provider[SchemaDeleteUseCase] = providers.Factory(
        SchemaDeleteUseCase,
        registry_repository=schema_registry_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        correlation_repository=analysis.correlation_repository,
    )

    sync_use_case: providers.Provider[SchemaSyncUseCase] = providers.Factory(
        SchemaSyncUseCase,
        registry_repository=schema_registry_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
    )

    delete_use_case: providers.Provider[SchemaDeleteUseCase] = providers.Factory(
        SchemaDeleteUseCase,
        registry_repository=schema_registry_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        correlation_repository=analysis.correlation_repository,
    )
