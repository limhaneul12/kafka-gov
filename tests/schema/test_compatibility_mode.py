"""스키마 호환성 모드 기능 테스트"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schema.application.use_cases import SchemaUploadUseCase
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSchemaArtifact,
    DomainSchemaType,
)


class MockUploadFile:
    """FastAPI UploadFile Mock"""

    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content_type = "application/octet-stream"
        self._content = content

    async def read(self) -> bytes:
        return self._content


@pytest.fixture
def mock_connection_manager():
    """Mock Connection Manager"""
    mock = AsyncMock()

    # get_schema_registry_client returns a mock registry client (AsyncMock으로 변경)
    mock_registry_client = AsyncMock()
    mock_registry_client.get_subjects = AsyncMock(return_value=[])
    mock_registry_client.get_latest_version = AsyncMock(return_value=None)
    mock_registry_client.test_compatibility = AsyncMock(return_value=True)
    mock_registry_client.register_schema = AsyncMock(return_value=1)
    mock_registry_client.delete_subject = AsyncMock(return_value=[])
    mock_registry_client.get_versions = AsyncMock(return_value=[])
    mock_registry_client.get_version = AsyncMock(return_value=None)
    mock_registry_client.set_config = AsyncMock(return_value=None)

    mock.get_schema_registry_client = AsyncMock(return_value=mock_registry_client)

    # get_minio_client returns (client, bucket_name)
    mock_minio_client = MagicMock()
    mock_minio_client.put_object = MagicMock(return_value=None)
    mock.get_minio_client = AsyncMock(return_value=(mock_minio_client, "test-bucket"))

    # get_storage_info returns storage info with base_url
    mock_storage_info = MagicMock()
    mock_storage_info.get_base_url = MagicMock(return_value="http://localhost:9000")
    mock_storage_info.endpoint_url = "localhost:9000"
    mock.get_storage_info = AsyncMock(return_value=mock_storage_info)

    return mock


@pytest.fixture
def mock_metadata_repository():
    """Mock Metadata Repository"""
    mock = AsyncMock()
    mock.save_upload_result.return_value = None
    mock.record_artifact.return_value = None
    mock.save_schema_metadata.return_value = None
    return mock


@pytest.fixture
def mock_audit_repository():
    """Mock Audit Repository"""
    mock = AsyncMock()
    mock.log_operation.return_value = "audit-log-id"
    return mock


class TestSchemaCompatibilityModeUpload:
    """스키마 업로드 시 호환성 모드 설정 테스트"""

    @pytest.mark.asyncio
    async def test_upload_with_default_compatibility_mode(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """기본 호환성 모드(BACKWARD)로 스키마 업로드"""
        # Given
        use_case = SchemaUploadUseCase(
            connection_manager=mock_connection_manager,
            metadata_repository=mock_metadata_repository,
            audit_repository=mock_audit_repository,
        )

        avro_schema = b'{"type": "record", "name": "TestSchema", "fields": []}'
        files = [MockUploadFile("test-schema.avsc", avro_schema)]

        # When
        result = await use_case.execute(
            registry_id="test-registry",
            storage_id="test-storage",
            env=DomainEnvironment.DEV,
            change_id="test-change-001",
            owner="team-test",
            files=files,
            actor="test-user",
            compatibility_mode=None,  # 기본값 사용
        )

        # Then
        assert result is not None
        assert len(result.artifacts) == 1
        assert result.artifacts[0].subject == "dev.test-schema"

    @pytest.mark.asyncio
    async def test_upload_with_custom_compatibility_mode(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """커스텀 호환성 모드(FULL)로 스키마 업로드"""
        # Given
        use_case = SchemaUploadUseCase(
            connection_manager=mock_connection_manager,
            metadata_repository=mock_metadata_repository,
            audit_repository=mock_audit_repository,
        )

        avro_schema = b'{"type": "record", "name": "TestSchema", "fields": []}'
        files = [MockUploadFile("test-schema.avsc", avro_schema)]

        # When
        result = await use_case.execute(
            registry_id="test-registry",
            storage_id="test-storage",
            env=DomainEnvironment.PROD,
            change_id="test-change-002",
            owner="team-test",
            files=files,
            actor="test-user",
            compatibility_mode=DomainCompatibilityMode.FULL,
        )

        # Then
        assert result is not None
        assert len(result.artifacts) == 1

    @pytest.mark.asyncio
    async def test_upload_with_all_compatibility_modes(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """모든 호환성 모드 옵션 테스트"""
        # Given
        use_case = SchemaUploadUseCase(
            connection_manager=mock_connection_manager,
            metadata_repository=mock_metadata_repository,
            audit_repository=mock_audit_repository,
        )

        test_modes = [
            DomainCompatibilityMode.NONE,
            DomainCompatibilityMode.BACKWARD,
            DomainCompatibilityMode.BACKWARD_TRANSITIVE,
            DomainCompatibilityMode.FORWARD,
            DomainCompatibilityMode.FORWARD_TRANSITIVE,
            DomainCompatibilityMode.FULL,
            DomainCompatibilityMode.FULL_TRANSITIVE,
        ]

        avro_schema = b'{"type": "record", "name": "TestSchema", "fields": []}'

        for idx, mode in enumerate(test_modes):
            files = [MockUploadFile(f"test-schema-{idx}.avsc", avro_schema)]

            # When
            result = await use_case.execute(
                registry_id="test-registry",
                storage_id="test-storage",
                env=DomainEnvironment.DEV,
                change_id=f"test-change-{idx:03d}",
                owner="team-test",
                files=files,
                actor="test-user",
                compatibility_mode=mode,
            )

            # Then
            assert result is not None

    @pytest.mark.asyncio
    async def test_upload_multiple_files_with_same_compatibility(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """여러 파일 업로드 시 동일한 호환성 모드 적용 테스트"""
        # Given
        use_case = SchemaUploadUseCase(
            connection_manager=mock_connection_manager,
            metadata_repository=mock_metadata_repository,
            audit_repository=mock_audit_repository,
        )

        avro_schema = b'{"type": "record", "name": "TestSchema", "fields": []}'
        files = [
            MockUploadFile("schema1.avsc", avro_schema),
            MockUploadFile("schema2.avsc", avro_schema),
            MockUploadFile("schema3.avsc", avro_schema),
        ]

        # When
        result = await use_case.execute(
            registry_id="test-registry",
            storage_id="test-storage",
            env=DomainEnvironment.STG,
            change_id="test-change-multi",
            owner="team-test",
            files=files,
            actor="test-user",
            compatibility_mode=DomainCompatibilityMode.FULL_TRANSITIVE,
        )

        # Then
        assert result is not None
        assert len(result.artifacts) == 3


class TestCompatibilityModeValidation:
    """호환성 모드 검증 테스트"""

    def test_compatibility_mode_enum_values(self):
        """호환성 모드 Enum 값 검증"""
        # Given & Then
        assert DomainCompatibilityMode.NONE.value == "NONE"
        assert DomainCompatibilityMode.BACKWARD.value == "BACKWARD"
        assert DomainCompatibilityMode.BACKWARD_TRANSITIVE.value == "BACKWARD_TRANSITIVE"
        assert DomainCompatibilityMode.FORWARD.value == "FORWARD"
        assert DomainCompatibilityMode.FORWARD_TRANSITIVE.value == "FORWARD_TRANSITIVE"
        assert DomainCompatibilityMode.FULL.value == "FULL"
        assert DomainCompatibilityMode.FULL_TRANSITIVE.value == "FULL_TRANSITIVE"

    def test_compatibility_mode_string_conversion(self):
        """호환성 모드 문자열 변환 테스트"""
        # Given & When & Then
        assert DomainCompatibilityMode("BACKWARD") == DomainCompatibilityMode.BACKWARD
        assert DomainCompatibilityMode("FULL") == DomainCompatibilityMode.FULL
        assert DomainCompatibilityMode("NONE") == DomainCompatibilityMode.NONE

    def test_invalid_compatibility_mode(self):
        """잘못된 호환성 모드 테스트"""
        # Given & When & Then
        with pytest.raises(ValueError):
            DomainCompatibilityMode("INVALID_MODE")
