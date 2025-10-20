"""Topic 모듈 DI 컨테이너 - ConnectionManager 기반"""

from __future__ import annotations

from dependency_injector import containers, providers

from app.topic.application.use_cases import (
    TopicBatchApplyUseCase,
    TopicBatchDryRunUseCase,
    TopicBulkDeleteUseCase,
    TopicListUseCase,
)
from app.topic.application.use_cases.policy_crud import (
    ActivatePolicyUseCase,
    ArchivePolicyUseCase,
    CreatePolicyUseCase,
    DeletePolicyUseCase,
    GetActivePolicyUseCase,
    GetPolicyUseCase,
    ListPoliciesUseCase,
    ListPolicyVersionsUseCase,
    RollbackPolicyUseCase,
    UpdatePolicyUseCase,
)
from app.topic.domain.repositories.interfaces import (
    IAuditRepository,
    IPolicyRepository,
    ITopicMetadataRepository,
)
from app.topic.infrastructure.repository.audit_repository import MySQLAuditRepository
from app.topic.infrastructure.repository.mysql_repository import MySQLTopicMetadataRepository
from app.topic.infrastructure.repository.policy_repository import PolicyRepository


class TopicContainer(containers.DeclarativeContainer):
    """Topic 모듈 DI 컨테이너 (멀티 클러스터 지원)

    Note:
        ConnectionManager는 cluster container에서 주입받아 사용
        모든 Use Case는 cluster_id를 파라미터로 받아 동적 클라이언트 생성
    """

    # 인프라스트럭처 컨테이너 참조
    infrastructure = providers.DependenciesContainer()

    # Cluster 컨테이너 참조 (ConnectionManager 사용)
    cluster = providers.DependenciesContainer()

    # MySQL 기반 구현체들 (Session Factory 패턴)
    metadata_repository: providers.Provider[ITopicMetadataRepository] = providers.Factory(
        MySQLTopicMetadataRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    audit_repository: providers.Provider[IAuditRepository] = providers.Factory(
        MySQLAuditRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    policy_repository: providers.Provider[IPolicyRepository] = providers.Factory(
        PolicyRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    # Use Cases (ConnectionManager 주입)
    dry_run_use_case: providers.Provider[TopicBatchDryRunUseCase] = providers.Factory(
        TopicBatchDryRunUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_repository=policy_repository,  # 정책 검증용
    )

    apply_use_case: providers.Provider[TopicBatchApplyUseCase] = providers.Factory(
        TopicBatchApplyUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_repository=policy_repository,  # 정책 검증용
    )

    list_use_case: providers.Provider[TopicListUseCase] = providers.Factory(
        TopicListUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
    )

    bulk_delete_use_case: providers.Provider[TopicBulkDeleteUseCase] = providers.Factory(
        TopicBulkDeleteUseCase,
        apply_use_case=apply_use_case,
        audit_repository=audit_repository,
        metadata_repository=metadata_repository,
    )

    # Policy Use Cases
    create_policy_use_case: providers.Provider[CreatePolicyUseCase] = providers.Factory(
        CreatePolicyUseCase,
        policy_repository=policy_repository,
    )

    get_policy_use_case: providers.Provider[GetPolicyUseCase] = providers.Factory(
        GetPolicyUseCase,
        policy_repository=policy_repository,
    )

    get_active_policy_use_case: providers.Provider[GetActivePolicyUseCase] = providers.Factory(
        GetActivePolicyUseCase,
        policy_repository=policy_repository,
    )

    list_policies_use_case: providers.Provider[ListPoliciesUseCase] = providers.Factory(
        ListPoliciesUseCase,
        policy_repository=policy_repository,
    )

    list_policy_versions_use_case: providers.Provider[ListPolicyVersionsUseCase] = (
        providers.Factory(
            ListPolicyVersionsUseCase,
            policy_repository=policy_repository,
        )
    )

    update_policy_use_case: providers.Provider[UpdatePolicyUseCase] = providers.Factory(
        UpdatePolicyUseCase,
        policy_repository=policy_repository,
    )

    activate_policy_use_case: providers.Provider[ActivatePolicyUseCase] = providers.Factory(
        ActivatePolicyUseCase,
        policy_repository=policy_repository,
    )

    archive_policy_use_case: providers.Provider[ArchivePolicyUseCase] = providers.Factory(
        ArchivePolicyUseCase,
        policy_repository=policy_repository,
    )

    delete_policy_use_case: providers.Provider[DeletePolicyUseCase] = providers.Factory(
        DeletePolicyUseCase,
        policy_repository=policy_repository,
    )

    rollback_policy_use_case: providers.Provider[RollbackPolicyUseCase] = providers.Factory(
        RollbackPolicyUseCase,
        policy_repository=policy_repository,
    )


# 전역 컨테이너 인스턴스
container = TopicContainer()
