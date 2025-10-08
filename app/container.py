from dependency_injector import containers, providers

from app.analysis.application.event_handlers import SchemaRegisteredHandler, TopicCreatedHandler
from app.analysis.container import AnalysisContainer
from app.cluster.container import ClusterContainer
from app.connect.container import ConnectContainer
from app.schema.container import SchemaContainer
from app.shared.container import InfrastructureContainer
from app.shared.infrastructure.event_bus import get_event_bus
from app.topic.container import TopicContainer


class AppContainer(containers.DeclarativeContainer):
    """애플리케이션 DI 컨테이너 (Composition Root에서만 wire)"""

    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.topic.interface",
            "app.schema.interface",
            "app.analysis.interface",
            "app.shared.interface",
            "app.cluster.interface",
            "app.connect.interface",  # Connect API 추가
        ]
    )

    # ClusterContainer (ConnectionManager 제공) - 최우선 생성
    cluster_container = providers.Container(ClusterContainer)

    infrastructure_container = providers.Container(
        InfrastructureContainer,
        cluster=cluster_container,
    )

    # ClusterContainer에 infrastructure 주입 (순환 참조 해결)
    cluster_container.override(
        providers.Container(
            ClusterContainer,
            infrastructure=infrastructure_container,
        )
    )

    analysis_container = providers.Container(
        AnalysisContainer, infrastructure=infrastructure_container
    )

    # TopicContainer - ConnectionManager 주입
    topic_container = providers.Container(
        TopicContainer,
        infrastructure=infrastructure_container,
        cluster=cluster_container,  # ConnectionManager 전달
    )

    # SchemaContainer - ConnectionManager 주입
    schema_container = providers.Container(
        SchemaContainer,
        infrastructure=infrastructure_container,
        analysis=analysis_container,
        cluster=cluster_container,  # ConnectionManager 전달
    )

    # ConnectContainer - Kafka Connect 관리
    connect_container = providers.Container(
        ConnectContainer,
        connect_repository=cluster_container.kafka_connect_repository,
        database_manager=infrastructure_container.database_manager,
    )


def register_event_handlers(container: AppContainer) -> None:
    """이벤트 핸들러 등록 - Session Factory 패턴"""
    event_bus = get_event_bus()

    linker = container.analysis_container().topic_schema_linker()
    session_factory = container.infrastructure_container().database_manager().get_db_session

    schema_handler = SchemaRegisteredHandler(linker, session_factory)
    topic_handler = TopicCreatedHandler(linker)

    event_bus.subscribe("schema.registered", schema_handler.handle)
    event_bus.subscribe("topic.created", topic_handler.handle)
