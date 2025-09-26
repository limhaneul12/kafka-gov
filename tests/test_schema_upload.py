"""Schema Upload 기능 테스트"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schema.application.use_cases import SchemaUploadUseCase
from app.schema.domain.models import Environment, SchemaUploadResult


class TestSchemaUploadUseCase:
    """Schema Upload UseCase 테스트"""

    @pytest.fixture
    def mock_storage_repository(self):
        """Mock Object Storage Repository"""
        mock = AsyncMock()
        mock.put_object.return_value = "https://minio.local/bucket/test-file.avsc"
        return mock

    @pytest.fixture
    def mock_metadata_repository(self):
        """Mock Metadata Repository"""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_audit_repository(self):
        """Mock Audit Repository"""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def upload_use_case(self, mock_storage_repository, mock_metadata_repository, mock_audit_repository):
        """Schema Upload UseCase 인스턴스"""
        return SchemaUploadUseCase(
            storage_repository=mock_storage_repository,
            metadata_repository=mock_metadata_repository,
            audit_repository=mock_audit_repository,
        )

    @pytest.fixture
    def mock_avro_file(self):
        """Mock AVRO 파일"""
        mock_file = MagicMock()
        mock_file.filename = "test-schema.avsc"
        mock_file.content_type = "application/json"
        
        # AVRO 스키마 예제
        avro_content = '''
        {
            "type": "record",
            "name": "TestRecord",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "timestamp", "type": "long"}
            ]
        }
        '''
        mock_file.read = AsyncMock(return_value=avro_content.encode())
        return mock_file

    @pytest.fixture
    def mock_json_file(self):
        """Mock JSON 파일"""
        mock_file = MagicMock()
        mock_file.filename = "test-schema.json"
        mock_file.content_type = "application/json"
        
        json_content = '{"type": "object", "properties": {"id": {"type": "string"}}}'
        mock_file.read = AsyncMock(return_value=json_content.encode())
        return mock_file

    @pytest.mark.asyncio
    async def test_upload_single_avro_file(self, upload_use_case, mock_avro_file):
        """단일 AVRO 파일 업로드 테스트"""
        result = await upload_use_case.execute(
            env=Environment.DEV,
            change_id="test-change-001",
            files=[mock_avro_file],
            actor="test-user",
        )

        assert isinstance(result, SchemaUploadResult)
        assert result.upload_id.startswith("upload_test-change-001_")
        assert len(result.artifacts) == 1
        
        artifact = result.artifacts[0]
        assert artifact.subject == "dev.test-schema"
        assert artifact.version == 1
        assert artifact.storage_url == "https://minio.local/bucket/test-file.avsc"

    @pytest.mark.asyncio
    async def test_upload_multiple_files(self, upload_use_case, mock_avro_file, mock_json_file):
        """다중 파일 업로드 테스트"""
        result = await upload_use_case.execute(
            env=Environment.PROD,
            change_id="test-change-002",
            files=[mock_avro_file, mock_json_file],
            actor="test-user",
        )

        assert len(result.artifacts) == 2
        assert result.summary()["total_files"] == 2

    @pytest.mark.asyncio
    async def test_upload_empty_file_list(self, upload_use_case):
        """빈 파일 목록 업로드 테스트"""
        with pytest.raises(ValueError, match="No files provided"):
            await upload_use_case.execute(
                env=Environment.DEV,
                change_id="test-change-003",
                files=[],
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_unsupported_file_type(self, upload_use_case):
        """지원되지 않는 파일 타입 테스트"""
        mock_file = MagicMock()
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(return_value=b"test content")

        with pytest.raises(ValueError, match="Unsupported file type"):
            await upload_use_case.execute(
                env=Environment.DEV,
                change_id="test-change-004",
                files=[mock_file],
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_large_file(self, upload_use_case):
        """큰 파일 업로드 테스트"""
        mock_file = MagicMock()
        mock_file.filename = "large-schema.avsc"
        # 10MB보다 큰 파일
        large_content = b"x" * (11 * 1024 * 1024)
        mock_file.read = AsyncMock(return_value=large_content)

        with pytest.raises(ValueError, match=r"File .* is too large"):
            await upload_use_case.execute(
                env=Environment.DEV,
                change_id="test-change-005",
                files=[mock_file],
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_invalid_json_file(self, upload_use_case):
        """잘못된 JSON 파일 테스트"""
        mock_file = MagicMock()
        mock_file.filename = "invalid.json"
        mock_file.read = AsyncMock(return_value=b"invalid json content {")

        with pytest.raises(ValueError, match="Invalid schema file"):
            await upload_use_case.execute(
                env=Environment.DEV,
                change_id="test-change-006",
                files=[mock_file],
                actor="test-user",
            )


class TestSchemaUploadIntegration:
    """Schema Upload API 통합 테스트"""

    def test_upload_endpoint_exists(self):
        """업로드 엔드포인트 존재 확인"""
        from app.schema.interface.router import router
        
        # 라우터에서 업로드 엔드포인트 찾기
        upload_routes = [route for route in router.routes if hasattr(route, 'path') and '/upload' in route.path]
        assert len(upload_routes) > 0, "Upload endpoint should exist"

    def test_upload_endpoint_methods(self):
        """업로드 엔드포인트 HTTP 메서드 확인"""
        from app.schema.interface.router import router
        
        upload_routes = [route for route in router.routes if hasattr(route, 'path') and '/upload' in route.path]
        upload_route = upload_routes[0]
        
        assert 'POST' in upload_route.methods, "Upload endpoint should accept POST method"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
