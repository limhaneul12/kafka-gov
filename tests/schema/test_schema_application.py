"""Schema 애플리케이션 레이어 테스트 (재구성)
- MinIO 어댑터를 활용한 업로드 유스케이스 테스트
"""

from __future__ import annotations

from typing import Any

import pytest

from app.schema.application.use_cases import SchemaUploadUseCase
from app.schema.domain.models import DomainEnvironment, DomainSchemaUploadResult
from app.schema.domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
)
from app.schema.infrastructure.storage.minio_adapter import MinIOObjectStorageAdapter


class DummyMinio:
    """테스트용 MinIO 클라이언트 더블"""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    # 초기화에서 사용
    def bucket_exists(self, bucket: str) -> bool:  # pragma: no cover - 단순 패스
        return True

    def make_bucket(self, bucket: str) -> None:  # pragma: no cover - 단순 패스
        return None

    # 업로드에서 사용 (to_thread로 호출됨)
    def put_object(
        self,
        *,
        bucket_name: str,
        object_name: str,
        data: bytes,
        length: int,
        metadata: dict[str, str] | None = None,
    ) -> None:
        assert len(data) == length
        self.objects[object_name] = data


class DummyFile:
    """FastAPI UploadFile 대체에 충분한 더블"""

    def __init__(
        self, filename: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        self.filename = filename
        self._data = data
        self.content_type = content_type

    async def read(self) -> bytes:
        return self._data


class DummyAuditRepo(ISchemaAuditRepository):
    async def log_operation(
        self,
        change_id: str,
        action: str,
        target: str,
        actor: str,
        status: str,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> str:  # pragma: no cover - 부수효과만 검증
        return "log-1"


class DummyMetadataRepo(ISchemaMetadataRepository):
    async def save_plan(self, plan, created_by: str) -> None:  # pragma: no cover
        return None

    async def get_plan(self, change_id: str):  # pragma: no cover
        return None

    async def save_apply_result(self, result, applied_by: str) -> None:  # pragma: no cover
        return None

    async def record_artifact(self, artifact, change_id: str) -> None:  # pragma: no cover
        return None

    async def save_upload_result(
        self, upload: DomainSchemaUploadResult, uploaded_by: str
    ) -> None:  # pragma: no cover
        return None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_use_case_success_with_minio_adapter() -> None:
    # Arrange
    dummy_minio = DummyMinio()
    storage = MinIOObjectStorageAdapter(
        client=dummy_minio, bucket_name="schemas", base_url="http://minio.local"
    )
    metadata = DummyMetadataRepo()
    audit = DummyAuditRepo()

    use_case = SchemaUploadUseCase(
        storage_repository=storage, metadata_repository=metadata, audit_repository=audit
    )

    files = [DummyFile("dev.user.avsc", b"{}", "application/json")]

    # Act
    result = await use_case.execute(
        env=DomainEnvironment.DEV, change_id="chg-1", files=files, actor="tester"
    )

    # Assert
    assert isinstance(result, DomainSchemaUploadResult)
    assert result.upload_id.startswith("upload_chg-1_")
    assert len(result.artifacts) == 1
    assert result.artifacts[0].subject == "dev.dev.user"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_use_case_rejects_empty_and_too_large() -> None:
    # Arrange
    dummy_minio = DummyMinio()
    storage = MinIOObjectStorageAdapter(client=dummy_minio, bucket_name="schemas")
    metadata = DummyMetadataRepo()
    audit = DummyAuditRepo()
    use_case = SchemaUploadUseCase(
        storage_repository=storage, metadata_repository=metadata, audit_repository=audit
    )

    # 빈 파일
    files_empty = [DummyFile("dev.empty.json", b"", "application/json")]
    with pytest.raises(ValueError, match=r"File dev\.empty\.json is empty"):
        await use_case.execute(
            env=DomainEnvironment.DEV, change_id="chg-2", files=files_empty, actor="tester"
        )

    # 너무 큰 파일
    big_data = b"0" * (10 * 1024 * 1024 + 1)
    files_big = [DummyFile("dev.big.json", big_data, "application/json")]
    with pytest.raises(ValueError, match=r"File dev\.big\.json is too large"):
        await use_case.execute(
            env=DomainEnvironment.DEV, change_id="chg-3", files=files_big, actor="tester"
        )
