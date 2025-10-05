"""Topic 모듈 DI 컨테이너"""

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
    ITopicRepository,
)
from app.topic.infrastructure.kafka_adapter import KafkaTopicAdapter
from app.topic.infrastructure.repository.audit_repository import MySQLAuditRepository
from app.topic.infrastructure.repository.mysql_repository import MySQLTopicMetadataRepository


class TopicContainer(containers.DeclarativeContainer):
    """Topic 모듈 DI 컨테이너"""

    # 인프라스트럭처 컨테이너 참조
    infrastructure = providers.DependenciesContainer()

    # Repositories
    topic_repository: providers.Provider[ITopicRepository] = providers.Singleton(
        KafkaTopicAdapter,
        admin_client=infrastructure.kafka_admin_client,
    )

    # MySQL 기반 구현체들 (Session Factory 패턴)
    metadata_repository: providers.Provider[ITopicMetadataRepository] = providers.Factory(
        MySQLTopicMetadataRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    audit_repository: providers.Provider[IAuditRepository] = providers.Factory(
        MySQLAuditRepository,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    # Use Cases
    dry_run_use_case: providers.Provider[TopicBatchDryRunUseCase] = providers.Factory(
        TopicBatchDryRunUseCase,
        topic_repository=topic_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
    )

    apply_use_case: providers.Provider[TopicBatchApplyUseCase] = providers.Factory(
        TopicBatchApplyUseCase,
        topic_repository=topic_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
    )

    list_use_case: providers.Provider[TopicListUseCase] = providers.Factory(
        TopicListUseCase,
        topic_repository=topic_repository,
        metadata_repository=metadata_repository,
    )

    bulk_delete_use_case: providers.Provider[TopicBulkDeleteUseCase] = providers.Factory(
        TopicBulkDeleteUseCase,
        apply_use_case=apply_use_case,
        audit_repository=audit_repository,
    )


# 전역 컨테이너 인스턴스
container = TopicContainer()
