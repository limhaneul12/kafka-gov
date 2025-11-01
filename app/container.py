from dependency_injector import containers, providers

from app.cluster.container import ClusterContainer
from app.connect.container import ConnectContainer
from app.consumer.container import ConsumerContainer
from app.schema.container import SchemaContainer
from app.shared.container import InfrastructureContainer
from app.topic.container import TopicContainer


class AppContainer(containers.DeclarativeContainer):
    """애플리케이션 DI 컨테이너 (Composition Root에서만 wire)"""

    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.topic.interface.routers",
            "app.schema.interface",
            "app.shared.interface",
            "app.cluster.interface.routers",
            "app.connect.interface.routers",
            "app.consumer.interface.routers",
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

    # TopicContainer - ConnectionManager 주입
    topic_container = providers.Container(
        TopicContainer,
        infrastructure=infrastructure_container,
        cluster=cluster_container,  # ConnectionManager 전달
    )

    # ConsumerContainer - DB 세션 및 ConnectionManager 주입
    consumer_container = providers.Container(
        ConsumerContainer,
        infrastructure=infrastructure_container,
        cluster=cluster_container,
    )

    # SchemaContainer - ConnectionManager 주입
    schema_container = providers.Container(
        SchemaContainer,
        infrastructure=infrastructure_container,
        cluster=cluster_container,  # ConnectionManager 전달
    )

    # ConnectContainer - Kafka Connect 관리
    connect_container = providers.Container(
        ConnectContainer,
        connect_repository=cluster_container.kafka_connect_repository,
        database_manager=infrastructure_container.database_manager,
    )
