"""공통 DI 컨테이너 - 인프라스트럭처 전용"""

from __future__ import annotations

from dependency_injector import containers, providers

from .database import DatabaseManager
from .settings import get_settings


class SharedContainer(containers.DeclarativeContainer):
    """공통 컨테이너 - 전역 설정"""

    # Pydantic Settings 통합
    settings = providers.Singleton(get_settings)

    # 데이터베이스 설정 (settings에서 가져옴)
    database_url = providers.Callable(lambda s: s.database.url, settings)
    database_echo = providers.Callable(lambda s: s.database.echo, settings)

    # Kafka 설정 (settings에서 가져옴)
    kafka_config = providers.Callable(lambda s: s.kafka.admin_config, settings)

    # Schema Registry 설정 (settings에서 가져옴)
    schema_registry_config = providers.Callable(lambda s: s.schema_registry.client_config, settings)


class InfrastructureContainer(containers.DeclarativeContainer):
    """인프라스트럭처 컨테이너 - 외부 시스템 연결"""

    # Configuration from shared container
    config = providers.DependenciesContainer()

    # Database Manager
    database_manager = providers.Singleton(
        DatabaseManager,
        database_url=config.database_url,
        echo=config.database_echo,
    )

    # Kafka AdminClient (외부에서 주입)
    kafka_admin_client = providers.Dependency()
    
    # Schema Registry Client (외부에서 주입)
    schema_registry_client = providers.Dependency()


# 전역 컨테이너 인스턴스들
shared_container = SharedContainer()
infrastructure_container = InfrastructureContainer()

# 컨테이너 간 의존성 연결
infrastructure_container.config.override(shared_container)
