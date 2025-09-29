"""Schema 인터페이스 레이어 테스트 - 의존성 문제 해결 버전"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.schema.domain.models import (
    DomainEnvironment,
    DomainPlanAction,
    DomainSchemaApplyResult,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaUploadResult,
)
from app.schema.interface.router import router


@pytest.fixture
def mock_dry_run_use_case() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_apply_use_case() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_upload_use_case() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_plan_use_case() -> Mock:
    return Mock()


@pytest.fixture
def app_with_mocked_deps(
    mock_dry_run_use_case: AsyncMock,
    mock_apply_use_case: AsyncMock,
    mock_upload_use_case: AsyncMock,
    mock_plan_use_case: Mock,
) -> FastAPI:
    """모든 의존성이 모킹된 FastAPI 앱"""
    from app.schema.interface.router import (
        _get_apply_use_case_dep,
        _get_current_user_dep,
        _get_dry_run_use_case_dep,
        _get_plan_use_case_dep,
        _get_upload_use_case_dep,
    )
    from app.shared.database import get_db_session

    app = FastAPI()
    app.include_router(router, prefix="/v1/schemas")

    # 의존성 오버라이드
    app.dependency_overrides[get_db_session] = lambda: Mock()
    app.dependency_overrides[_get_dry_run_use_case_dep] = lambda session: mock_dry_run_use_case
    app.dependency_overrides[_get_apply_use_case_dep] = lambda session: mock_apply_use_case
    app.dependency_overrides[_get_upload_use_case_dep] = lambda session: mock_upload_use_case
    app.dependency_overrides[_get_plan_use_case_dep] = lambda session: mock_plan_use_case
    app.dependency_overrides[_get_current_user_dep] = lambda request: "test-user"

    return app


@pytest.fixture
def client(app_with_mocked_deps: FastAPI) -> TestClient:
    return TestClient(app_with_mocked_deps)


class TestSchemaBatchDryRunEndpoint:
    """스키마 배치 Dry-Run 엔드포인트 테스트"""

    @pytest.mark.unit
    def test_should_execute_dry_run_successfully(
        self,
        client: TestClient,
        mock_dry_run_use_case: AsyncMock,
    ) -> None:
        """Dry-Run이 성공적으로 실행되어야 한다"""
        # Arrange
        request_data = {
            "change_id": "change-123",
            "env": "dev",
            "subject_strategy": "TopicNameStrategy",
            "items": [
                {
                    "subject": "dev.user.event",
                    "type": "AVRO",
                    "compatibility": "BACKWARD",
                    "schema": '{"type": "record", "name": "User"}',
                }
            ],
        }

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
        mock_dry_run_use_case.execute.return_value = expected_plan

        # Act
        response = client.post("/v1/schemas/batch/dry-run", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["change_id"] == "change-123"
        assert data["env"] == "dev"
        mock_dry_run_use_case.execute.assert_called_once()

    @pytest.mark.unit
    def test_should_handle_validation_error(
        self,
        client: TestClient,
        mock_dry_run_use_case: AsyncMock,
    ) -> None:
        """검증 에러를 올바르게 처리해야 한다"""
        # Arrange - 잘못된 요청 데이터
        request_data = {
            "change_id": "",  # 빈 change_id
            "env": "invalid",  # 잘못된 환경
            "subject_strategy": "TopicNameStrategy",
            "items": [],  # 빈 아이템 리스트
        }

        # Act
        response = client.post("/v1/schemas/batch/dry-run", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # 유스케이스가 호출되지 않아야 함
        mock_dry_run_use_case.execute.assert_not_called()


class TestSchemaBatchApplyEndpoint:
    """스키마 배치 Apply 엔드포인트 테스트"""

    @pytest.mark.unit
    def test_should_execute_apply_successfully(
        self,
        client: TestClient,
        mock_apply_use_case: AsyncMock,
    ) -> None:
        """Apply가 성공적으로 실행되어야 한다"""
        # Arrange
        request_data = {
            "change_id": "change-123",
            "env": "dev",
            "subject_strategy": "TopicNameStrategy",
            "items": [
                {
                    "subject": "dev.user.event",
                    "type": "AVRO",
                    "compatibility": "BACKWARD",
                    "schema": '{"type": "record", "name": "User"}',
                }
            ],
        }

        expected_result = DomainSchemaApplyResult(
            change_id="change-123",
            env=DomainEnvironment.DEV,
            registered=("dev.user.event",),
            skipped=(),
            failed=(),
            audit_id="audit-456",
        )
        mock_apply_use_case.execute.return_value = expected_result

        # Act
        response = client.post("/v1/schemas/batch/apply", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["change_id"] == "change-123"
        assert data["env"] == "dev"
        mock_apply_use_case.execute.assert_called_once()


class TestSchemaUploadEndpoint:
    """스키마 업로드 엔드포인트 테스트"""

    @pytest.mark.unit
    def test_should_upload_files_successfully(
        self,
        client: TestClient,
        mock_upload_use_case: AsyncMock,
    ) -> None:
        """파일 업로드가 성공적으로 실행되어야 한다"""
        # Arrange
        expected_result = DomainSchemaUploadResult(
            upload_id="upload-123",
            artifacts=(),
        )
        mock_upload_use_case.execute.return_value = expected_result

        # Act
        response = client.post(
            "/v1/schemas/upload",
            data={"env": "dev", "change_id": "change-123"},
            files={"files": ("test.avsc", b'{"type": "record"}', "application/json")},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["upload_id"] == "upload-123"
        mock_upload_use_case.execute.assert_called_once()


class TestSchemaPlanEndpoint:
    """스키마 계획 조회 엔드포인트 테스트"""

    @pytest.mark.unit
    def test_should_get_existing_plan(
        self,
        client: TestClient,
        mock_plan_use_case: Mock,
    ) -> None:
        """기존 계획을 성공적으로 조회해야 한다"""
        # Arrange
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
        mock_plan_use_case.get_plan.return_value = expected_plan

        # Act
        response = client.get("/v1/schemas/plan/change-123")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["change_id"] == "change-123"
        assert data["env"] == "dev"
        mock_plan_use_case.get_plan.assert_called_once_with("change-123")


class TestSchemaHealthEndpoint:
    """스키마 헬스체크 엔드포인트 테스트"""

    @pytest.mark.unit
    def test_should_return_health_status(self, client: TestClient) -> None:
        """헬스 상태를 반환해야 한다"""
        # Act
        response = client.get("/v1/schemas/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["module"] == "schema"
        assert "version" in data
