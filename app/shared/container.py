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

    # Object Storage 설정 (settings에서 가져옴)
    storage_endpoint = providers.Callable(
        lambda s: s.storage.endpoint_url.replace("http://", "").replace("https://", ""), settings
    )
    storage_access_key = providers.Callable(lambda s: s.storage.access_key, settings)
    storage_secret_key = providers.Callable(lambda s: s.storage.secret_key, settings)
    storage_bucket_name = providers.Callable(lambda s: s.storage.bucket_name, settings)
    storage_use_ssl = providers.Callable(lambda s: s.storage.use_ssl, settings)
    storage_base_url = providers.Callable(lambda s: s.storage.endpoint_url, settings)


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

    # MinIO Client (팩토리 함수 사용)
    minio_client = providers.Factory(
        providers.Callable(
            lambda: __import__(
                "app.schema.infrastructure.storage.minio_adapter", fromlist=["create_minio_client"]
            ).create_minio_client
        ),
        endpoint=config.storage_endpoint,
        access_key=config.storage_access_key,
        secret_key=config.storage_secret_key,
        secure=config.storage_use_ssl,
    )


# 전역 컨테이너 인스턴스들
shared_container = SharedContainer()
infrastructure_container = InfrastructureContainer()

# 컨테이너 간 의존성 연결
infrastructure_container.config.override(shared_container)
