"""Schema Registry Use Cases"""

from __future__ import annotations

import logging
from datetime import datetime

from app.cluster.domain.models import ConnectionTestResult, SchemaRegistry
from app.cluster.domain.repositories import ISchemaRegistryRepository
from app.cluster.domain.services import IConnectionManager
from app.shared.security import get_encryption_service

logger = logging.getLogger(__name__)


class CreateSchemaRegistryUseCase:
    """Schema Registry 생성 Use Case"""

    def __init__(
        self,
        registry_repo: ISchemaRegistryRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.registry_repo = registry_repo
        self.connection_manager = connection_manager

    async def execute(
        self,
        registry_id: str,
        name: str,
        url: str,
        description: str | None = None,
        auth_username: str | None = None,
        auth_password: str | None = None,
        ssl_ca_location: str | None = None,
        ssl_cert_location: str | None = None,
        ssl_key_location: str | None = None,
        timeout: int = 30,
    ) -> SchemaRegistry:
        """레지스트리 생성"""
        encryption_service = get_encryption_service()
        encrypted_password = encryption_service.encrypt(auth_password) if auth_password else None

        registry = SchemaRegistry(
            registry_id=registry_id,
            name=name,
            url=url,
            description=description,
            auth_username=auth_username,
            auth_password=encrypted_password,
            ssl_ca_location=ssl_ca_location,
            ssl_cert_location=ssl_cert_location,
            ssl_key_location=ssl_key_location,
            timeout=timeout,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        created_registry = await self.registry_repo.create(registry)
        logger.info(f"Schema Registry created: {registry_id}")
        return created_registry


class ListSchemaRegistriesUseCase:
    """Schema Registry 목록 조회 Use Case"""

    def __init__(self, registry_repo: ISchemaRegistryRepository) -> None:
        self.registry_repo = registry_repo

    async def execute(self, active_only: bool = True) -> list[SchemaRegistry]:
        """레지스트리 목록 조회"""
        return await self.registry_repo.list_all(active_only=active_only)


class GetSchemaRegistryUseCase:
    """Schema Registry 단일 조회 Use Case"""

    def __init__(self, registry_repo: ISchemaRegistryRepository) -> None:
        self.registry_repo = registry_repo

    async def execute(self, registry_id: str) -> SchemaRegistry | None:
        """레지스트리 단일 조회"""
        return await self.registry_repo.get_by_id(registry_id)


class UpdateSchemaRegistryUseCase:
    """Schema Registry 수정 Use Case"""

    def __init__(
        self,
        registry_repo: ISchemaRegistryRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.registry_repo = registry_repo
        self.connection_manager = connection_manager

    async def execute(
        self,
        registry_id: str,
        name: str,
        url: str,
        description: str | None = None,
        auth_username: str | None = None,
        auth_password: str | None = None,
        ssl_ca_location: str | None = None,
        ssl_cert_location: str | None = None,
        ssl_key_location: str | None = None,
        timeout: int = 30,
        is_active: bool = True,
    ) -> SchemaRegistry:
        """레지스트리 수정"""
        existing = await self.registry_repo.get_by_id(registry_id)
        if not existing:
            raise ValueError(f"Schema Registry not found: {registry_id}")

        encryption_service = get_encryption_service()
        encrypted_password = encryption_service.encrypt(auth_password) if auth_password else None

        updated_registry = SchemaRegistry(
            registry_id=registry_id,
            name=name,
            url=url,
            description=description,
            auth_username=auth_username,
            auth_password=encrypted_password,
            ssl_ca_location=ssl_ca_location,
            ssl_cert_location=ssl_cert_location,
            ssl_key_location=ssl_key_location,
            timeout=timeout,
            is_active=is_active,
            created_at=existing.created_at,
            updated_at=datetime.now(),
        )

        result = await self.registry_repo.update(updated_registry)
        self.connection_manager.invalidate_cache("schema_registry", registry_id)
        logger.info(f"Schema Registry updated: {registry_id}")
        return result


class DeleteSchemaRegistryUseCase:
    """Schema Registry 삭제 Use Case"""

    def __init__(
        self,
        registry_repo: ISchemaRegistryRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.registry_repo = registry_repo
        self.connection_manager = connection_manager

    async def execute(self, registry_id: str) -> bool:
        """레지스트리 삭제 (소프트 삭제)"""
        success = await self.registry_repo.delete(registry_id)
        if success:
            self.connection_manager.invalidate_cache("schema_registry", registry_id)
            logger.info(f"Schema Registry deleted: {registry_id}")
        return success


class TestSchemaRegistryConnectionUseCase:
    """Schema Registry 연결 테스트 Use Case"""

    def __init__(self, connection_manager: IConnectionManager) -> None:
        self.connection_manager = connection_manager

    async def execute(self, registry_id: str) -> ConnectionTestResult:
        """Schema Registry 연결 테스트"""
        return await self.connection_manager.test_schema_registry_connection(registry_id)
