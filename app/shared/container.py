"""공통 인프라 DI 컨테이너."""

from __future__ import annotations

from dependency_injector import containers, providers

from .database import DatabaseManager
from .settings import settings


class InfrastructureContainer(containers.DeclarativeContainer):
    """현재는 데이터베이스 매니저만 제공하는 공통 인프라 컨테이너."""

    infra_container = providers.Object(settings)

    database_manager = providers.Singleton(
        DatabaseManager,
        database_url=infra_container.provided.database.url,
        echo=infra_container.provided.database.echo,
    )
