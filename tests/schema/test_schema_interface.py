"""Schema 인터페이스 레이어 테스트 (재구성)"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.schema.application.use_cases import (
    SchemaBatchApplyUseCase,
    SchemaBatchDryRunUseCase,
    SchemaPlanUseCase,
    SchemaUploadUseCase,
)
from app.schema.domain.models import (
    DomainEnvironment,
    DomainPlanAction,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaUploadResult,
)
from app.schema.interface.router import router


@pytest.fixture
def mock_get_current_user() -> Mock:
    return Mock(return_value="test-user")


@pytest.fixture
def mock_dry_run_use_case() -> AsyncMock:
    return AsyncMock(spec=SchemaBatchDryRunUseCase)


@pytest.fixture
def mock_apply_use_case() -> AsyncMock:
    return AsyncMock(spec=SchemaBatchApplyUseCase)


@pytest.fixture
def mock_plan_use_case() -> AsyncMock:
    return AsyncMock(spec=SchemaPlanUseCase)


@pytest.fixture
def mock_upload_use_case() -> AsyncMock:
    return AsyncMock(spec=SchemaUploadUseCase)


@pytest.fixture
def app_with_overrides() -> FastAPI:
    """의존성이 오버라이드된 FastAPI 앱"""
    from fastapi import FastAPI

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
    app.dependency_overrides[_get_dry_run_use_case_dep] = lambda session: AsyncMock()
    app.dependency_overrides[_get_apply_use_case_dep] = lambda session: AsyncMock()
    app.dependency_overrides[_get_upload_use_case_dep] = lambda session: AsyncMock()
    app.dependency_overrides[_get_plan_use_case_dep] = lambda session: Mock()
    app.dependency_overrides[_get_current_user_dep] = lambda request: "test-user"

    return app


@pytest.fixture
def client(app_with_overrides: FastAPI) -> TestClient:
    return TestClient(app_with_overrides)


class TestSchemaBatchDryRunEndpoint:
    @pytest.mark.unit
    def test_should_execute_dry_run_successfully(
        self,
        client: TestClient,
        app_with_overrides: FastAPI,
    ) -> None:
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

        # 모킹된 유스케이스 설정
        from app.schema.interface.router import _get_dry_run_use_case_dep

        mocked_use_case = app_with_overrides.dependency_overrides[_get_dry_run_use_case_dep](None)
        mocked_use_case.execute.return_value = expected_plan

        # Act
        response = client.post("/v1/schemas/batch/dry-run", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["change_id"] == "change-123"
        assert data["env"] == "dev"
        mocked_use_case.execute.assert_called_once()

    @pytest.mark.unit
    def test_should_handle_validation_error(
        self,
        client: TestClient,
        mock_dry_run_use_case: AsyncMock,
        mock_get_current_user: Mock,
    ) -> None:
        # Arrange
        request_data = {
            "change_id": "change-123",
            "env": "dev",
            "subject_strategy": "TopicNameStrategy",
            "items": [
                {
                    "subject": "",  # invalid
                    "type": "AVRO",
                    "compatibility": "BACKWARD",
                    "schema": "{}",
                }
            ],
        }

        mock_dry_run_use_case.execute.side_effect = ValueError("subject is required")

        with (
            patch(
                "app.schema.interface.router._get_dry_run_use_case_dep",
                return_value=mock_dry_run_use_case,
            ),
            patch("app.schema.interface.router._get_current_user_dep", return_value="test-user"),
        ):
            # Act
            response = client.post("/v1/schemas/batch/dry-run", json=request_data)

            # Assert
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert "Validation error" in response.json()["detail"]

    @pytest.mark.unit
    def test_should_handle_internal_server_error(
        self,
        client: TestClient,
        mock_dry_run_use_case: AsyncMock,
        mock_get_current_user: Mock,
    ) -> None:
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
                    "schema": "{}",
                }
            ],
        }

        mock_dry_run_use_case.execute.side_effect = RuntimeError("boom")

        with (
            patch(
                "app.schema.interface.router._get_dry_run_use_case_dep",
                return_value=mock_dry_run_use_case,
            ),
            patch("app.schema.interface.router._get_current_user_dep", return_value="test-user"),
        ):
            # Act
            response = client.post("/v1/schemas/batch/dry-run", json=request_data)

            # Assert
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Internal server error" in response.json()["detail"]


class TestSchemaBatchApplyEndpoint:
    @pytest.mark.unit
    def test_should_execute_apply_successfully(
        self,
        client: TestClient,
        mock_apply_use_case: AsyncMock,
        mock_get_current_user: Mock,
    ) -> None:
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
                    "schema": "{}",
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

        with (
            patch(
                "app.schema.interface.router._get_apply_use_case_dep",
                return_value=mock_apply_use_case,
            ),
            patch("app.schema.interface.router._get_current_user_dep", return_value="test-user"),
        ):
            # Act
            response = client.post("/v1/schemas/batch/apply", json=request_data)

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["change_id"] == "change-123"
            assert data["env"] == "dev"
            assert "dev.user.event" in data["registered"]
            mock_apply_use_case.execute.assert_called_once()

    @pytest.mark.unit
    def test_should_handle_policy_violation(
        self,
        client: TestClient,
        mock_apply_use_case: AsyncMock,
        mock_get_current_user: Mock,
    ) -> None:
        # Arrange
        request_data = {
            "change_id": "change-123",
            "env": "dev",
            "subject_strategy": "TopicNameStrategy",
            "items": [
                {
                    "subject": "invalid-subject",
                    "type": "AVRO",
                    "compatibility": "BACKWARD",
                    "schema": "{}",
                }
            ],
        }

        mock_apply_use_case.execute.side_effect = ValueError("Policy violations detected")

        with (
            patch(
                "app.schema.interface.router._get_apply_use_case_dep",
                return_value=mock_apply_use_case,
            ),
            patch("app.schema.interface.router._get_current_user_dep", return_value="test-user"),
        ):
            # Act
            response = client.post("/v1/schemas/batch/apply", json=request_data)

            # Assert
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert "Policy violation" in response.json()["detail"]


class TestSchemaUploadEndpoint:
    @pytest.mark.unit
    def test_should_upload_files_successfully(
        self,
        client: TestClient,
        mock_upload_use_case: AsyncMock,
        mock_get_current_user: Mock,
    ) -> None:
        # Arrange
        file_content = b"{}"
        files = {"files": ("user.avsc", BytesIO(file_content), "application/json")}
        form_data = {"env": "dev", "change_id": "change-123"}

        expected_result = DomainSchemaUploadResult(
            upload_id="upload-123",
            artifacts=(
                DomainSchemaArtifact(
                    subject="dev.user",
                    version=1,
                    storage_url="http://minio.local/schemas/dev/user.avsc",
                ),
            ),
        )
        mock_upload_use_case.execute.return_value = expected_result

        with (
            patch(
                "app.schema.interface.router._get_upload_use_case_dep",
                return_value=mock_upload_use_case,
            ),
            patch("app.schema.interface.router._get_current_user_dep", return_value="test-user"),
        ):
            # Act
            response = client.post("/v1/schemas/upload", files=files, data=form_data)

            # Assert
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["upload_id"] == "upload-123"
            assert len(data["artifacts"]) == 1
            mock_upload_use_case.execute.assert_called_once()

    @pytest.mark.unit
    def test_should_reject_empty_file_list(
        self,
        client: TestClient,
        mock_get_current_user: Mock,
    ) -> None:
        # Arrange
        form_data = {"env": "dev", "change_id": "change-123"}

        with patch("app.schema.interface.router._get_current_user_dep", return_value="test-user"):
            # Act
            response = client.post("/v1/schemas/upload", data=form_data)

            # Assert
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert "at least one file must be provided" in response.json()["detail"]

    @pytest.mark.unit
    def test_should_handle_upload_validation_error(
        self,
        client: TestClient,
        mock_upload_use_case: AsyncMock,
        mock_get_current_user: Mock,
    ) -> None:
        # Arrange
        files = {"files": ("invalid.txt", BytesIO(b"bad"), "text/plain")}
        form_data = {"env": "dev", "change_id": "change-123"}

        mock_upload_use_case.execute.side_effect = ValueError("Unsupported file type")

        with (
            patch(
                "app.schema.interface.router._get_upload_use_case_dep",
                return_value=mock_upload_use_case,
            ),
            patch("app.schema.interface.router._get_current_user_dep", return_value="test-user"),
        ):
            # Act
            response = client.post("/v1/schemas/upload", files=files, data=form_data)

            # Assert
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert "Validation error" in response.json()["detail"]


class TestSchemaPlanEndpoint:
    @pytest.mark.unit
    def test_should_get_existing_plan(
        self,
        client: TestClient,
        mock_plan_use_case: AsyncMock,
    ) -> None:
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
        mock_plan_use_case.execute.return_value = expected_plan

        with patch(
            "app.schema.interface.router._get_plan_use_case_dep", return_value=mock_plan_use_case
        ):
            # Act
            response = client.get("/v1/schemas/plan/change-123")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["change_id"] == "change-123"
            assert data["env"] == "dev"
            mock_plan_use_case.execute.assert_called_once_with("change-123")

    @pytest.mark.unit
    def test_should_handle_plan_not_found(
        self,
        client: TestClient,
        mock_plan_use_case: AsyncMock,
    ) -> None:
        # Arrange
        mock_plan_use_case.execute.return_value = None

        with patch(
            "app.schema.interface.router._get_plan_use_case_dep", return_value=mock_plan_use_case
        ):
            # Act
            response = client.get("/v1/schemas/plan/nonexistent-change")

            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in response.json()["detail"]


class TestSchemaHealthEndpoint:
    @pytest.mark.unit
    def test_should_return_health_status(self, client: TestClient) -> None:
        response = client.get("/v1/schemas/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["module"] == "schema"
        assert "version" in data
