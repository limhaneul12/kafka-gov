"""Object Storage Use Cases"""

from __future__ import annotations

import logging
from datetime import datetime

from app.cluster.domain.models import ConnectionTestResult, ObjectStorage
from app.cluster.domain.repositories import IObjectStorageRepository
from app.cluster.domain.services import IConnectionManager
from app.shared.security import get_encryption_service

logger = logging.getLogger(__name__)


class CreateObjectStorageUseCase:
    """Object Storage 생성 Use Case"""

    def __init__(
        self,
        storage_repo: IObjectStorageRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.storage_repo = storage_repo
        self.connection_manager = connection_manager

    async def execute(
        self,
        storage_id: str,
        name: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        description: str | None = None,
        region: str = "us-east-1",
        use_ssl: bool = False,
    ) -> ObjectStorage:
        """스토리지 생성"""
        encryption_service = get_encryption_service()
        encrypted_secret = encryption_service.encrypt(secret_key)

        storage = ObjectStorage(
            storage_id=storage_id,
            name=name,
            endpoint_url=endpoint_url,
            description=description,
            access_key=access_key,
            secret_key=encrypted_secret,
            bucket_name=bucket_name,
            region=region,
            use_ssl=use_ssl,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        created_storage = await self.storage_repo.create(storage)
        logger.info(f"Object Storage created: {storage_id}")
        return created_storage


class ListObjectStoragesUseCase:
    """Object Storage 목록 조회 Use Case"""

    def __init__(self, storage_repo: IObjectStorageRepository) -> None:
        self.storage_repo = storage_repo

    async def execute(self, active_only: bool = True) -> list[ObjectStorage]:
        """스토리지 목록 조회"""
        return await self.storage_repo.list_all(active_only=active_only)


class UpdateObjectStorageUseCase:
    """Object Storage 수정 Use Case"""

    def __init__(
        self,
        storage_repo: IObjectStorageRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.storage_repo = storage_repo
        self.connection_manager = connection_manager

    async def execute(
        self,
        storage_id: str,
        name: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        description: str | None = None,
        region: str = "us-east-1",
        use_ssl: bool = False,
        is_active: bool = True,
    ) -> ObjectStorage:
        """스토리지 수정"""
        existing = await self.storage_repo.get_by_id(storage_id)
        if not existing:
            raise ValueError(f"Object Storage not found: {storage_id}")

        encryption_service = get_encryption_service()
        encrypted_secret = encryption_service.encrypt(secret_key)

        updated_storage = ObjectStorage(
            storage_id=storage_id,
            name=name,
            endpoint_url=endpoint_url,
            description=description,
            access_key=access_key,
            secret_key=encrypted_secret,
            bucket_name=bucket_name,
            region=region,
            use_ssl=use_ssl,
            is_active=is_active,
            created_at=existing.created_at,
            updated_at=datetime.now(),
        )

        result = await self.storage_repo.update(updated_storage)
        self.connection_manager.invalidate_cache("storage", storage_id)
        logger.info(f"Object Storage updated: {storage_id}")
        return result


class DeleteObjectStorageUseCase:
    """Object Storage 삭제 Use Case"""

    def __init__(
        self,
        storage_repo: IObjectStorageRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.storage_repo = storage_repo
        self.connection_manager = connection_manager

    async def execute(self, storage_id: str) -> bool:
        """스토리지 삭제 (소프트 삭제)"""
        success = await self.storage_repo.delete(storage_id)
        if success:
            self.connection_manager.invalidate_cache("storage", storage_id)
            logger.info(f"Object Storage deleted: {storage_id}")
        return success


class TestObjectStorageConnectionUseCase:
    """Object Storage 연결 테스트 Use Case"""

    def __init__(self, connection_manager: IConnectionManager) -> None:
        self.connection_manager = connection_manager

    async def execute(self, storage_id: str) -> ConnectionTestResult:
        """Object Storage 연결 테스트"""
        return await self.connection_manager.test_storage_connection(storage_id)
