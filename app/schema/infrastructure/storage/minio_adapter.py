"""MinIO 기반 Object Storage 어댑터"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import timedelta
from io import BytesIO
from typing import Any
from urllib.parse import urljoin

from minio import Minio
from minio.deleteobjects import DeleteObject
from minio.error import S3Error

from ...domain.repositories.interfaces import IObjectStorageRepository

logger = logging.getLogger(__name__)


class MinIOObjectStorageAdapter(IObjectStorageRepository):
    """MinIO 기반 Object Storage 구현체"""

    def __init__(
        self,
        client: Minio,
        bucket_name: str,
        base_url: str | None = None,
    ) -> None:
        self.client = client
        self.bucket_name = bucket_name
        self.base_url = base_url or "http://localhost:9000"

        # 버킷 존재 확인 및 생성
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """버킷 존재 확인 및 생성"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise RuntimeError(f"Bucket operation failed: {e}") from e

    async def put_object(
        self,
        key: str,
        data: bytes,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """객체 저장 후 접근 URL 반환"""
        try:
            # 메타데이터 준비
            object_metadata = metadata or {}
            object_metadata.update(
                {
                    "content-length": str(len(data)),
                    "content-hash": hashlib.sha256(data).hexdigest(),
                }
            )

            # 객체 업로드
            await asyncio.to_thread(
                self.client.put_object,
                bucket_name=self.bucket_name,
                object_name=key,
                data=BytesIO(data),
                length=len(data),
                metadata=dict(object_metadata),  # dict로 변환
            )

            # 접근 URL 생성
            storage_url = urljoin(self.base_url, f"/{self.bucket_name}/{key}")

            logger.info(f"Object stored: {key} ({len(data)} bytes)")
            return storage_url

        except S3Error as e:
            logger.error(f"Failed to put object {key}: {e}")
            raise RuntimeError(f"Object storage failed: {e}") from e

    async def get_object(self, key: str) -> bytes:
        """객체 조회"""
        try:

            def _get() -> bytes:
                response = self.client.get_object(self.bucket_name, key)
                try:
                    data = response.read()
                    return data
                finally:
                    response.close()
                    response.release_conn()

            return await asyncio.to_thread(_get)
        except S3Error as e:
            logger.error(f"Failed to get object {key}: {e}")
            raise RuntimeError(f"Object retrieval failed: {e}") from e

    async def delete_object(self, key: str) -> None:
        """단일 객체 삭제"""
        try:
            await asyncio.to_thread(self.client.remove_object, self.bucket_name, key)
            logger.info(f"Object deleted: {key}")
        except S3Error as e:
            logger.error(f"Failed to delete object {key}: {e}")
            raise RuntimeError(f"Object deletion failed: {e}") from e

    async def delete_prefix(self, prefix: str) -> None:
        """접두사로 객체들 일괄 삭제"""
        try:
            # 접두사에 해당하는 객체 목록 조회 및 이름 수집
            def _list_names() -> list[str]:
                objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
                return [obj.object_name for obj in objects if obj.object_name is not None]

            object_names = await asyncio.to_thread(_list_names)

            if object_names:
                # 일괄 삭제
                def _remove_many() -> list[Any]:
                    delete_list = [DeleteObject(name) for name in object_names]
                    errors_iter = self.client.remove_objects(self.bucket_name, delete_list)
                    return list(errors_iter)

                error_list = await asyncio.to_thread(_remove_many)
                if error_list:
                    logger.error(f"Failed to delete some objects: {error_list}")
                    raise RuntimeError(f"Partial deletion failed: {error_list}")

                logger.info(f"Deleted {len(object_names)} objects with prefix: {prefix}")
            else:
                logger.info(f"No objects found with prefix: {prefix}")

        except S3Error as e:
            logger.error(f"Failed to delete objects with prefix {prefix}: {e}")
            raise RuntimeError(f"Prefix deletion failed: {e}") from e

    async def list_objects(self, prefix: str | None = None) -> list[dict[str, Any]]:
        """객체 목록 조회"""
        try:

            def _list() -> list[dict[str, Any]]:
                objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
                return [
                    {
                        "key": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                        "etag": obj.etag,
                    }
                    for obj in objects
                ]

            return await asyncio.to_thread(_list)

        except S3Error as e:
            logger.error(f"Failed to list objects: {e}")
            raise RuntimeError(f"Object listing failed: {e}") from e

    def get_presigned_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        """사전 서명된 URL 생성 (다운로드용)"""
        try:
            url = self.client.presigned_get_object(
                self.bucket_name, key, expires=timedelta(seconds=expires_in_seconds)
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            raise RuntimeError(f"Presigned URL generation failed: {e}") from e


def create_minio_client(
    endpoint: str, access_key: str, secret_key: str, secure: bool = False
) -> Minio:
    """MinIO 클라이언트 생성"""
    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def create_minio_storage_adapter(
    client: Minio, bucket_name: str, base_url: str | None = None
) -> MinIOObjectStorageAdapter:
    """MinIO Storage 어댑터 생성"""
    return MinIOObjectStorageAdapter(
        client=client,
        bucket_name=bucket_name,
        base_url=base_url,
    )
