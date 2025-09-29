"""Object Storage 구현체 모듈"""

from .minio_adapter import (
    MinIOObjectStorageAdapter,
    create_minio_client,
    create_minio_storage_adapter,
)

__all__ = [
    "MinIOObjectStorageAdapter",
    "create_minio_client",
    "create_minio_storage_adapter",
]
