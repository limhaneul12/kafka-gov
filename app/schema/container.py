"""Schema 모듈 DI 컨테이너 - ConnectionManager 기반"""

from __future__ import annotations

from dependency_injector import containers, providers

from .application.services.schema_lint import SchemaLintService
from .application.use_cases.batch.apply import SchemaBatchApplyUseCase
from .application.use_cases.batch.dry_run import SchemaBatchDryRunUseCase
from .application.use_cases.batch.get_plan import SchemaPlanUseCase
from .application.use_cases.governance.detail import GetSubjectDetailUseCase
from .application.use_cases.governance.history import GetSchemaHistoryUseCase
from .application.use_cases.governance.impact import GetImpactGraphUseCase
from .application.use_cases.governance.rollback import RollbackSchemaUseCase
from .application.use_cases.governance.stats import GetGovernanceStatsUseCase
from .application.use_cases.management.delete import SchemaDeleteUseCase
from .application.use_cases.management.plan_change import PlanSchemaChangeUseCase
from .application.use_cases.management.search import SchemaSearchUseCase
from .application.use_cases.management.sync import SchemaSyncUseCase
from .application.use_cases.management.upload import SchemaUploadUseCase
from .application.use_cases.policy.management import SchemaPolicyUseCase
from .domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaPolicyRepository,
)
from .infrastructure.repository.audit_repository import MySQLSchemaAuditRepository
from .infrastructure.repository.mysql_repository import MySQLSchemaMetadataRepository
from .infrastructure.repository.policy_repository import MySQLSchemaPolicyRepository


class SchemaContainer(containers.DeclarativeContainer):
    """Schema 모듈 DI 컨테이너 (멀티 레지스트리/스토리지 지원)

    Note:
        ConnectionManager는 cluster container에서 주입받아 사용
        모든 Use Case는 registry_id/storage_id를 파라미터로 받아 동적 클라이언트 생성
    """

    # 인프라스트럭처 컨테이너 참조
    infrastructure = providers.DependenciesContainer()

    # Cluster 컨테이너 참조 (ConnectionManager 사용)
    cluster = providers.DependenciesContainer()

    # Consumer 컨테이너 참조 (GetTopicConsumersUseCase 사용)
    consumer = providers.DependenciesContainer()

    # MySQL 기반 구현체들 (Session Factory 패턴)
    metadata_repository: providers.Provider[ISchemaMetadataRepository] = providers.Factory(
        MySQLSchemaMetadataRepository,  # type: ignore[arg-type]
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    audit_repository: providers.Provider[ISchemaAuditRepository] = providers.Factory(
        MySQLSchemaAuditRepository,  # type: ignore[arg-type]
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    policy_repository: providers.Provider[ISchemaPolicyRepository] = providers.Factory(
        MySQLSchemaPolicyRepository,  # type: ignore[arg-type]
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    # Use Cases (ConnectionManager 주입)
    dry_run_use_case: providers.Provider[SchemaBatchDryRunUseCase] = providers.Factory(
        SchemaBatchDryRunUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_repository=policy_repository,
    )

    apply_use_case: providers.Provider[SchemaBatchApplyUseCase] = providers.Factory(
        SchemaBatchApplyUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_repository=policy_repository,
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
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    delete_use_case: providers.Provider[SchemaDeleteUseCase] = providers.Factory(
        SchemaDeleteUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
    )

    lint_service: providers.Provider[SchemaLintService] = providers.Factory(SchemaLintService)

    # Governance Use Cases
    governance_stats_use_case: providers.Provider[GetGovernanceStatsUseCase] = providers.Factory(
        GetGovernanceStatsUseCase,
        connection_manager=cluster.connection_manager,
        metadata_repository=metadata_repository,
        policy_repository=policy_repository,
    )

    schema_history_use_case: providers.Provider[GetSchemaHistoryUseCase] = providers.Factory(
        GetSchemaHistoryUseCase,
        connection_manager=cluster.connection_manager,
        metadata_repository=metadata_repository,
    )

    impact_graph_use_case: providers.Provider[GetImpactGraphUseCase] = providers.Factory(
        GetImpactGraphUseCase,
        connection_manager=cluster.connection_manager,
        get_topic_consumers_use_case=consumer.get_topic_consumers_use_case,
    )

    subject_detail_use_case: providers.Provider[GetSubjectDetailUseCase] = providers.Factory(
        GetSubjectDetailUseCase,
        connection_manager=cluster.connection_manager,
        metadata_repository=metadata_repository,
        policy_repository=policy_repository,
    )

    plan_change_use_case: providers.Provider[PlanSchemaChangeUseCase] = providers.Factory(
        PlanSchemaChangeUseCase,
        connection_manager=cluster.connection_manager,
        metadata_repository=metadata_repository,
    )

    rollback_use_case: providers.Provider[RollbackSchemaUseCase] = providers.Factory(
        RollbackSchemaUseCase,
        connection_manager=cluster.connection_manager,
        metadata_repository=metadata_repository,
        plan_change_use_case=plan_change_use_case,
    )

    search_use_case: providers.Provider[SchemaSearchUseCase] = providers.Factory(
        SchemaSearchUseCase,
        metadata_repository=metadata_repository,
    )

    policy_use_case: providers.Provider[SchemaPolicyUseCase] = providers.Factory(
        SchemaPolicyUseCase,
        policy_repository=policy_repository,
    )
