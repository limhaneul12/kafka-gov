"""Schema 모듈 DI 컨테이너 - ConnectionManager 기반"""

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
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
)
from .infrastructure.repository.audit_repository import MySQLSchemaAuditRepository
from .infrastructure.repository.mysql_repository import MySQLSchemaMetadataRepository


class SchemaContainer(containers.DeclarativeContainer):
    """Schema 모듈 DI 컨테이너 (멀티 레지스트리/스토리지 지원)

    Note:
        ConnectionManager는 cluster container에서 주입받아 사용
        모든 Use Case는 registry_id/storage_id를 파라미터로 받아 동적 클라이언트 생성
    """

    # 인프라스트럭처 컨테이너 참조
    infrastructure = providers.DependenciesContainer()

    # Analysis 컨테이너 참조 (correlation_repository 사용)
    analysis = providers.DependenciesContainer()

    # Cluster 컨테이너 참조 (ConnectionManager 사용)
    cluster = providers.DependenciesContainer()

    # MySQL 기반 구현체들 (Session Factory 패턴)
    metadata_repository: providers.Provider[ISchemaMetadataRepository] = providers.Factory(
        MySQLSchemaMetadataRepository,  # type: ignore[arg-type]
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    audit_repository: providers.Provider[ISchemaAuditRepository] = providers.Factory(
        MySQLSchemaAuditRepository,  # type: ignore[arg-type]
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    # Domain Services
    policy_engine: providers.Provider[SchemaPolicyEngine] = providers.Singleton(SchemaPolicyEngine)

    # Use Cases (ConnectionManager 주입)
    dry_run_use_case: providers.Provider[SchemaBatchDryRunUseCase] = providers.Factory(
        SchemaBatchDryRunUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_engine=policy_engine,
    )

    apply_use_case: providers.Provider[SchemaBatchApplyUseCase] = providers.Factory(
        SchemaBatchApplyUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_engine=policy_engine,
    )

    plan_use_case: providers.Provider[SchemaPlanUseCase] = providers.Factory(
        SchemaPlanUseCase,
        metadata_repository=metadata_repository,
    )

    upload_use_case: providers.Provider[SchemaUploadUseCase] = providers.Factory(
        SchemaUploadUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
    )

    sync_use_case: providers.Provider[SchemaSyncUseCase] = providers.Factory(
        SchemaSyncUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
    )

    delete_use_case: providers.Provider[SchemaDeleteUseCase] = providers.Factory(
        SchemaDeleteUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        correlation_repository=analysis.correlation_repository,  # Optional
    )

    # delete_analysis_use_case는 delete_use_case.analyze()로 통합됨
