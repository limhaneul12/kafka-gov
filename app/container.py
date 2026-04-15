from dependency_injector import containers, providers

from app.registry_connections.container import RegistryConnectionContainer
from app.schema.container import SchemaContainer
from app.shared.container import InfrastructureContainer


class AppContainer(containers.DeclarativeContainer):
    """애플리케이션 DI 컨테이너 (Composition Root에서만 wire)"""

    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.schema.interface",
            "app.schema.interface.routers",
            "app.registry_connections.interface.routers",
        ]
    )

    # Registry connection container (ConnectionManager 제공)
    registry_container = providers.Container(RegistryConnectionContainer)

    infrastructure_container = providers.Container(InfrastructureContainer)

    # Registry connection container에 infrastructure 주입
    registry_container.override(
        providers.Container(
            RegistryConnectionContainer,
            infrastructure=infrastructure_container,
        )
    )

    # SchemaContainer - ConnectionManager 주입
    schema_container = providers.Container(
        SchemaContainer,
        infrastructure=infrastructure_container,
        registry_connections=registry_container,
    )
