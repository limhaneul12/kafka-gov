from dependency_injector import containers, providers

from app.analysis.application.event_handlers import SchemaRegisteredHandler, TopicCreatedHandler
from app.analysis.container import AnalysisContainer
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
        ]
    )

    infrastructure_container = providers.Container(InfrastructureContainer)
    analysis_container = providers.Container(
        AnalysisContainer, infrastructure=infrastructure_container
    )
    topic_container = providers.Container(TopicContainer, infrastructure=infrastructure_container)
    schema_container = providers.Container(
        SchemaContainer,
        infrastructure=infrastructure_container,
        analysis=analysis_container,
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
