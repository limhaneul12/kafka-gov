"""(Deprecated) MinIO Storage Adapter 모듈.

이 모듈은 과거 MinIO 기반 Object Storage 연동을 위해 사용되었으나,
현재 버전에서는 더 이상 사용되지 않습니다.

남아 있는 import 경로 호환성을 위해 파일은 유지하지만,
실제 구현은 제공하지 않습니다.
"""

from __future__ import annotations

from typing import Any, NoReturn


class MinIOObjectStorageAdapter:  # pragma: no cover - deprecated shim
    """Deprecated shim for backward compatibility.

    사용 시점에 즉시 런타임 오류를 발생시켜, 남아 있는 참조를 조기에 발견할 수 있게 합니다.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._raise_deprecated()

    def _raise_deprecated(self) -> NoReturn:
        raise RuntimeError("MinIO-based object storage is no longer supported.")


def create_minio_client(*args: Any, **kwargs: Any) -> NoReturn:  # pragma: no cover
    raise RuntimeError("MinIO-based object storage is no longer supported.")


def create_minio_storage_adapter(*args: Any, **kwargs: Any) -> NoReturn:  # pragma: no cover
    raise RuntimeError("MinIO-based object storage is no longer supported.")
