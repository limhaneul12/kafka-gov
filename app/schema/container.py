"""Schema module DI container."""

from __future__ import annotations

from dependency_injector import containers, providers

from .application.services.schema_lint import SchemaLintService
from .application.use_cases.batch.apply import SchemaBatchApplyUseCase
from .application.use_cases.batch.dry_run import SchemaBatchDryRunUseCase
from .application.use_cases.batch.get_plan import SchemaPlanUseCase
from .application.use_cases.governance.detail import GetSubjectDetailUseCase
from .application.use_cases.governance.drift import GetSchemaDriftUseCase
from .application.use_cases.governance.history import GetSchemaHistoryUseCase
from .application.use_cases.governance.rollback import (
    ExecuteRollbackSchemaUseCase,
    RollbackSchemaUseCase,
)
from .application.use_cases.governance.stats import GetGovernanceStatsUseCase
from .application.use_cases.governance.versions import (
    CompareSchemaVersionsUseCase,
    ExportSchemaVersionUseCase,
    GetSchemaVersionsUseCase,
    GetSchemaVersionUseCase,
)
from .application.use_cases.management.delete import SchemaDeleteUseCase
from .application.use_cases.management.plan_change import PlanSchemaChangeUseCase
from .application.use_cases.management.search import SchemaSearchUseCase
from .application.use_cases.management.settings import UpdateSchemaSettingsUseCase
from .application.use_cases.management.sync import SchemaSyncUseCase
from .application.use_cases.management.upload import SchemaUploadUseCase
from .application.use_cases.policy.management import SchemaPolicyUseCase
from .domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaPolicyRepository,
)
from .governance_support.infrastructure.repository import (
    MySQLAuditActivityRepository,
    SQLApprovalRequestRepository,
)
from .governance_support.use_cases import (
    ApproveApprovalRequestUseCase,
    CreateApprovalRequestUseCase,
    GetActivityHistoryUseCase,
    GetApprovalRequestUseCase,
    GetRecentActivitiesUseCase,
    ListApprovalRequestsUseCase,
    RejectApprovalRequestUseCase,
)
from .infrastructure.repository.audit_repository import MySQLSchemaAuditRepository
from .infrastructure.repository.mysql_repository import MySQLSchemaMetadataRepository
from .infrastructure.repository.policy_repository import MySQLSchemaPolicyRepository


class SchemaContainer(containers.DeclarativeContainer):
    """Schema module DI container."""

    infrastructure = providers.DependenciesContainer()
    registry_connections = providers.DependenciesContainer()

    metadata_repository: providers.Provider[ISchemaMetadataRepository] = providers.Factory(
        MySQLSchemaMetadataRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )
    audit_repository: providers.Provider[ISchemaAuditRepository] = providers.Factory(
        MySQLSchemaAuditRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )
    policy_repository: providers.Provider[ISchemaPolicyRepository] = providers.Factory(
        MySQLSchemaPolicyRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )
    approval_request_repository = providers.Factory(
        SQLApprovalRequestRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )
    audit_activity_repository = providers.Factory(
        MySQLAuditActivityRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )
    create_approval_request_use_case = providers.Factory(
        CreateApprovalRequestUseCase,
        approval_repository=approval_request_repository,
    )
    list_approval_requests_use_case = providers.Factory(
        ListApprovalRequestsUseCase,
        approval_repository=approval_request_repository,
    )
    get_approval_request_use_case = providers.Factory(
        GetApprovalRequestUseCase,
        approval_repository=approval_request_repository,
    )
    approve_approval_request_use_case = providers.Factory(
        ApproveApprovalRequestUseCase,
        approval_repository=approval_request_repository,
    )
    reject_approval_request_use_case = providers.Factory(
        RejectApprovalRequestUseCase,
        approval_repository=approval_request_repository,
    )
    recent_activities_use_case = providers.Factory(
        GetRecentActivitiesUseCase,
        audit_repository=audit_activity_repository,
    )
    activity_history_use_case = providers.Factory(
        GetActivityHistoryUseCase,
        audit_repository=audit_activity_repository,
    )

    dry_run_use_case: providers.Provider[SchemaBatchDryRunUseCase] = providers.Factory(
        SchemaBatchDryRunUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_repository=policy_repository,
    )
    apply_use_case: providers.Provider[SchemaBatchApplyUseCase] = providers.Factory(
        SchemaBatchApplyUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_repository=policy_repository,
        approval_request_use_case=create_approval_request_use_case,
    )
    plan_use_case: providers.Provider[SchemaPlanUseCase] = providers.Factory(
        SchemaPlanUseCase,
        metadata_repository=metadata_repository,
    )
    upload_use_case: providers.Provider[SchemaUploadUseCase] = providers.Factory(
        SchemaUploadUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
    )
    sync_use_case: providers.Provider[SchemaSyncUseCase] = providers.Factory(
        SchemaSyncUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )
    delete_use_case: providers.Provider[SchemaDeleteUseCase] = providers.Factory(
        SchemaDeleteUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
    )
    lint_service: providers.Provider[SchemaLintService] = providers.Factory(SchemaLintService)

    governance_stats_use_case: providers.Provider[GetGovernanceStatsUseCase] = providers.Factory(
        GetGovernanceStatsUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
        policy_repository=policy_repository,
    )
    schema_history_use_case: providers.Provider[GetSchemaHistoryUseCase] = providers.Factory(
        GetSchemaHistoryUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
    )
    schema_drift_use_case: providers.Provider[GetSchemaDriftUseCase] = providers.Factory(
        GetSchemaDriftUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
    )
    schema_versions_use_case: providers.Provider[GetSchemaVersionsUseCase] = providers.Factory(
        GetSchemaVersionsUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
    )
    schema_version_use_case: providers.Provider[GetSchemaVersionUseCase] = providers.Factory(
        GetSchemaVersionUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
    )
    compare_schema_versions_use_case: providers.Provider[CompareSchemaVersionsUseCase] = (
        providers.Factory(
            CompareSchemaVersionsUseCase,
            connection_manager=registry_connections.connection_manager,
            metadata_repository=metadata_repository,
        )
    )
    export_schema_version_use_case: providers.Provider[ExportSchemaVersionUseCase] = (
        providers.Factory(
            ExportSchemaVersionUseCase,
            version_use_case=schema_version_use_case,
        )
    )
    subject_detail_use_case: providers.Provider[GetSubjectDetailUseCase] = providers.Factory(
        GetSubjectDetailUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
        policy_repository=policy_repository,
    )
    plan_change_use_case: providers.Provider[PlanSchemaChangeUseCase] = providers.Factory(
        PlanSchemaChangeUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
    )
    rollback_use_case: providers.Provider[RollbackSchemaUseCase] = providers.Factory(
        RollbackSchemaUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
        plan_change_use_case=plan_change_use_case,
    )
    execute_rollback_use_case: providers.Provider[ExecuteRollbackSchemaUseCase] = providers.Factory(
        ExecuteRollbackSchemaUseCase,
        connection_manager=registry_connections.connection_manager,
        metadata_repository=metadata_repository,
        apply_use_case=apply_use_case,
    )
    search_use_case: providers.Provider[SchemaSearchUseCase] = providers.Factory(
        SchemaSearchUseCase,
        metadata_repository=metadata_repository,
    )
    update_schema_settings_use_case: providers.Provider[UpdateSchemaSettingsUseCase] = (
        providers.Factory(
            UpdateSchemaSettingsUseCase,
            connection_manager=registry_connections.connection_manager,
            metadata_repository=metadata_repository,
            audit_repository=audit_repository,
        )
    )
    policy_use_case: providers.Provider[SchemaPolicyUseCase] = providers.Factory(
        SchemaPolicyUseCase,
        policy_repository=policy_repository,
    )
