"""공통 DI 컨테이너 - 고성능 최적화"""

from __future__ import annotations

from dependency_injector import containers, providers

from .database import DatabaseManager
from .settings import get_settings


class SharedContainer(containers.DeclarativeContainer):
    """공통 컨테이너 - 설정 관리 (최적화)"""

    # Settings는 이미 lru_cache로 싱글톤이므로 직접 사용
    settings = providers.Singleton(get_settings)


class InfrastructureContainer(containers.DeclarativeContainer):
    """인프라스트럭처 컨테이너 - 외부 시스템 연결 (최적화)"""

    # Configuration from shared container
    config = providers.DependenciesContainer()

    # Database Manager - Lazy 초기화
    database_manager = providers.Singleton(
        DatabaseManager,
        database_url=providers.Callable(lambda: get_settings().database.url),
        echo=providers.Callable(lambda: get_settings().database.echo),
    )

    # Kafka AdminClient (외부에서 주입)
    kafka_admin_client = providers.Dependency()

    # Schema Registry Client (외부에서 주입)
    schema_registry_client = providers.Dependency()

    # MinIO Client - Lazy 초기화
    minio_client = providers.Factory(
        providers.Callable(
            lambda: __import__(
                "app.schema.infrastructure.storage.minio_adapter", fromlist=["create_minio_client"]
            ).create_minio_client
        ),
        endpoint=providers.Callable(
            lambda: get_settings()
            .storage.endpoint_url.replace("http://", "")
            .replace("https://", "")
        ),
        access_key=providers.Callable(lambda: get_settings().storage.access_key),
        secret_key=providers.Callable(lambda: get_settings().storage.secret_key),
        secure=providers.Callable(lambda: get_settings().storage.use_ssl),
    )


# 전역 컨테이너 인스턴스들
shared_container = SharedContainer()
infrastructure_container = InfrastructureContainer()

# 컨테이너 간 의존성 연결
infrastructure_container.config.override(shared_container)
