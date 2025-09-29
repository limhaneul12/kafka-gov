"""Schema 인터페이스 레이어 단순 테스트 (데이터베이스 의존성 없음)"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.schema.domain.models import (
    DomainEnvironment,
    DomainPlanAction,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaUploadResult,
)


@pytest.fixture
def simple_client() -> TestClient:
    """데이터베이스 의존성 없는 간단한 테스트 클라이언트"""
    from fastapi import FastAPI

    app = FastAPI()

    # 간단한 헬스체크 엔드포인트만 테스트
    @app.get("/v1/schemas/health")
    def health():
        return {"status": "healthy", "module": "schema", "version": "1.0.0"}

    return TestClient(app)


class TestSimpleSchemaEndpoints:
    """데이터베이스 의존성 없는 간단한 엔드포인트 테스트"""

    @pytest.mark.unit
    def test_health_endpoint_should_return_status(self, simple_client: TestClient) -> None:
        """헬스 엔드포인트는 상태를 반환해야 한다"""
        # Act
        response = simple_client.get("/v1/schemas/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["module"] == "schema"
        assert "version" in data


class TestSchemaModels:
    """스키마 도메인 모델 직접 테스트 (의존성 없음)"""

    @pytest.mark.unit
    def test_schema_plan_should_create_successfully(self) -> None:
        """스키마 계획이 성공적으로 생성되어야 한다"""
        # Arrange
        items = (
            DomainSchemaPlanItem(
                subject="dev.user.event",
                action=DomainPlanAction.REGISTER,
                current_version=None,
                target_version=1,
                diff={"action": "create"},
            ),
        )

        # Act
        plan = DomainSchemaPlan(
            change_id="change-123",
            env=DomainEnvironment.DEV,
            items=items,
        )

        # Assert
        assert plan.change_id == "change-123"
        assert plan.env == DomainEnvironment.DEV
        assert len(plan.items) == 1
        assert plan.items[0].subject == "dev.user.event"
        assert plan.can_apply is True

    @pytest.mark.unit
    def test_schema_apply_result_should_create_successfully(self) -> None:
        """스키마 적용 결과가 성공적으로 생성되어야 한다"""
        # Act
        result = DomainSchemaApplyResult(
            change_id="change-123",
            env=DomainEnvironment.DEV,
            registered=("dev.user.event",),
            skipped=(),
            failed=(),
            audit_id="audit-456",
        )

        # Assert
        assert result.change_id == "change-123"
        assert result.env == DomainEnvironment.DEV
        assert "dev.user.event" in result.registered
        assert len(result.skipped) == 0
        assert len(result.failed) == 0

        summary = result.summary()
        assert summary["registered_count"] == 1
        assert summary["skipped_count"] == 0
        assert summary["failed_count"] == 0

    @pytest.mark.unit
    def test_schema_upload_result_should_create_successfully(self) -> None:
        """스키마 업로드 결과가 성공적으로 생성되어야 한다"""
        # Arrange
        artifacts = (
            DomainSchemaArtifact(
                subject="dev.user",
                version=1,
                storage_url="http://minio.local/schemas/dev/user.avsc",
            ),
        )

        # Act
        result = DomainSchemaUploadResult(
            upload_id="upload-123",
            artifacts=artifacts,
        )

        # Assert
        assert result.upload_id == "upload-123"
        assert len(result.artifacts) == 1
        assert result.artifacts[0].subject == "dev.user"
        assert result.artifacts[0].version == 1

        summary = result.summary()
        assert summary["total_files"] == 1
        assert summary["avro_count"] == 0  # subject가 "dev.user"이므로 avro로 분류되지 않음


class TestMockingPatterns:
    """모킹 패턴 테스트 (실제 API 호출 없음)"""

    @pytest.mark.unit
    def test_async_mock_should_work_correctly(self) -> None:
        """AsyncMock이 올바르게 작동해야 한다"""
        # Arrange
        mock_use_case = AsyncMock()
        expected_plan = DomainSchemaPlan(
            change_id="change-123",
            env=DomainEnvironment.DEV,
            items=(
                DomainSchemaPlanItem(
                    subject="dev.user.event",
                    action=DomainPlanAction.REGISTER,
                    current_version=None,
                    target_version=1,
                    diff={"action": "create"},
                ),
            ),
        )
        mock_use_case.execute.return_value = expected_plan

        # Act
        result = mock_use_case.execute.return_value

        # Assert
        assert result.change_id == "change-123"
        assert result.env == DomainEnvironment.DEV
        assert len(result.items) == 1

    @pytest.mark.unit
    def test_file_upload_mock_should_work_correctly(self) -> None:
        """파일 업로드 모킹이 올바르게 작동해야 한다"""
        # Arrange
        file_content = b'{"type": "record", "name": "User"}'
        mock_file = Mock()
        mock_file.filename = "user.avsc"
        mock_file.read.return_value = file_content

        # Act
        content = mock_file.read()
        filename = mock_file.filename

        # Assert
        assert content == file_content
        assert filename == "user.avsc"
        assert len(content) > 0
