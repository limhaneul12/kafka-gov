from dependency_injector import containers, providers

from app.cluster.container import ClusterContainer
from app.schema.container import SchemaContainer
from app.shared.container import InfrastructureContainer


class AppContainer(containers.DeclarativeContainer):
    """애플리케이션 DI 컨테이너 (Composition Root에서만 wire)"""

    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.schema.interface",
            "app.schema.interface.routers",
            "app.shared.interface",
            "app.cluster.interface.routers",
        ]
    )

    # ClusterContainer (ConnectionManager 제공) - 최우선 생성
    cluster_container = providers.Container(ClusterContainer)

    infrastructure_container = providers.Container(InfrastructureContainer)

    # ClusterContainer에 infrastructure 주입 (순환 참조 해결)
    cluster_container.override(
        providers.Container(
            ClusterContainer,
            infrastructure=infrastructure_container,
        )
    )

    # SchemaContainer - ConnectionManager 주입
    schema_container = providers.Container(
        SchemaContainer,
        infrastructure=infrastructure_container,
        cluster=cluster_container,  # ConnectionManager 전달
    )
