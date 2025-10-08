"""Topic 모듈 DI 컨테이너 - ConnectionManager 기반"""

from __future__ import annotations

from dependency_injector import containers, providers

from app.topic.application.use_cases import (
    TopicBatchApplyUseCase,
    TopicBatchDryRunUseCase,
    TopicBulkDeleteUseCase,
    TopicListUseCase,
)
from app.topic.domain.repositories.interfaces import (
    IAuditRepository,
    ITopicMetadataRepository,
)
from app.topic.infrastructure.repository.audit_repository import MySQLAuditRepository
from app.topic.infrastructure.repository.mysql_repository import MySQLTopicMetadataRepository


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

    # Use Cases (ConnectionManager 주입)
    dry_run_use_case: providers.Provider[TopicBatchDryRunUseCase] = providers.Factory(
        TopicBatchDryRunUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
    )

    apply_use_case: providers.Provider[TopicBatchApplyUseCase] = providers.Factory(
        TopicBatchApplyUseCase,
        connection_manager=cluster.connection_manager,  # ConnectionManager 주입
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
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


# 전역 컨테이너 인스턴스
container = TopicContainer()
