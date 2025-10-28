from __future__ import annotations

from dependency_injector import containers, providers

from app.consumer.application.use_cases.metrics import (
    GetConsumerGroupMetricsUseCase,
    GetGroupAdviceUseCase,
)
from app.consumer.application.use_cases.query import (
    GetConsumerGroupSummaryUseCase,
    GetGroupMembersUseCase,
    GetGroupPartitionsUseCase,
    GetGroupRebalanceUseCase,
    GetTopicConsumersUseCase,
    ListConsumerGroupsUseCase,
)
from app.consumer.application.use_cases.topic_stats import GetGroupTopicStatsUseCase


class ConsumerContainer(containers.DeclarativeContainer):
    """Consumer 모듈 DI 컨테이너 - 실시간 Kafka 조회 방식"""

    infrastructure = providers.DependenciesContainer()
    cluster = providers.DependenciesContainer()

    # Use Cases - admin_client_getter 주입 (실시간 Kafka 조회)
    list_groups_use_case: providers.Provider[ListConsumerGroupsUseCase] = providers.Factory(
        ListConsumerGroupsUseCase,
        admin_client_getter=cluster.connection_manager.provided.get_kafka_admin_client,
    )

    get_metrics_use_case: providers.Provider[GetConsumerGroupMetricsUseCase] = providers.Factory(
        GetConsumerGroupMetricsUseCase,
        admin_client_getter=cluster.connection_manager.provided.get_kafka_admin_client,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    get_summary_use_case: providers.Provider[GetConsumerGroupSummaryUseCase] = providers.Factory(
        GetConsumerGroupSummaryUseCase,
        admin_client_getter=cluster.connection_manager.provided.get_kafka_admin_client,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    get_members_use_case: providers.Provider[GetGroupMembersUseCase] = providers.Factory(
        GetGroupMembersUseCase,
        admin_client_getter=cluster.connection_manager.provided.get_kafka_admin_client,
    )

    get_partitions_use_case: providers.Provider[GetGroupPartitionsUseCase] = providers.Factory(
        GetGroupPartitionsUseCase,
        admin_client_getter=cluster.connection_manager.provided.get_kafka_admin_client,
    )

    get_rebalance_use_case: providers.Provider[GetGroupRebalanceUseCase] = providers.Factory(
        GetGroupRebalanceUseCase,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    get_advice_use_case: providers.Provider[GetGroupAdviceUseCase] = providers.Factory(
        GetGroupAdviceUseCase,
        admin_client_getter=cluster.connection_manager.provided.get_kafka_admin_client,
        session_factory=infrastructure.database_manager.provided.get_db_session,
    )

    get_topic_consumers_use_case: providers.Provider[GetTopicConsumersUseCase] = providers.Factory(
        GetTopicConsumersUseCase,
        admin_client_getter=cluster.connection_manager.provided.get_kafka_admin_client,
    )

    get_group_topic_stats_use_case: providers.Provider[GetGroupTopicStatsUseCase] = (
        providers.Factory(
            GetGroupTopicStatsUseCase,
            admin_client_getter=cluster.connection_manager.provided.get_kafka_admin_client,
        )
    )
