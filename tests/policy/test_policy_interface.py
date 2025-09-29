"""Policy API 인터페이스 테스트"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.policy.domain.models import (
    DomainEnvironment,
    DomainPolicySeverity,
    DomainResourceType,
)
from app.policy.interface.dto import (
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
    PolicyViolationResponse,
    ValidationSummaryResponse,
)
from app.policy.interface.router import router
from app.shared.auth import get_current_user


class TestPolicyEvaluationRequest:
    """PolicyEvaluationRequest DTO 테스트"""

    @pytest.mark.unit
    def test_should_create_valid_request(self) -> None:
        """유효한 요청을 생성해야 한다."""
        # Arrange & Act
        request = PolicyEvaluationRequest(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            targets=[{"name": "user-events", "config": {"partitions": 3}}],
            actor="test-user",
            metadata={"team": "data-platform"},
        )

        # Assert
        assert request.environment == DomainEnvironment.PROD
        assert request.resource_type == DomainResourceType.TOPIC
        assert len(request.targets) == 1
        assert request.actor == "test-user"
        assert request.metadata == {"team": "data-platform"}

    @pytest.mark.unit
    def test_should_require_non_empty_targets(self) -> None:
        """빈 대상 목록을 거부해야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="at least 1 item"):
            PolicyEvaluationRequest(
                environment=DomainEnvironment.PROD,
                resource_type=DomainResourceType.TOPIC,
                targets=[],  # 빈 목록
                actor="test-user",
            )

    @pytest.mark.unit
    def test_should_require_non_empty_actor(self) -> None:
        """빈 액터를 거부해야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="at least 1 character"):
            PolicyEvaluationRequest(
                environment=DomainEnvironment.PROD,
                resource_type=DomainResourceType.TOPIC,
                targets=[{"name": "test"}],
                actor="",  # 빈 문자열
            )

    @pytest.mark.unit
    def test_should_strip_whitespace_from_actor(self) -> None:
        """액터에서 공백을 제거해야 한다."""
        # Arrange & Act
        request = PolicyEvaluationRequest(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            targets=[{"name": "test"}],
            actor="  test-user  ",
        )

        # Assert
        assert request.actor == "test-user"

    @pytest.mark.unit
    def test_should_allow_none_metadata(self) -> None:
        """메타데이터가 None일 수 있어야 한다."""
        # Arrange & Act
        request = PolicyEvaluationRequest(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            targets=[{"name": "test"}],
            actor="test-user",
            metadata=None,
        )

        # Assert
        assert request.metadata is None


class TestPolicyViolationResponse:
    """PolicyViolationResponse DTO 테스트"""

    @pytest.mark.unit
    def test_should_create_violation_response_with_required_fields(self) -> None:
        """필수 필드로 위반 응답을 생성해야 한다."""
        # Arrange & Act
        response = PolicyViolationResponse(
            resource_type=DomainResourceType.TOPIC,
            resource_name="test-topic",
            rule_id="naming.pattern",
            message="Name does not match pattern",
            severity=DomainPolicySeverity.ERROR,
        )

        # Assert
        assert response.resource_type == DomainResourceType.TOPIC
        assert response.resource_name == "test-topic"
        assert response.rule_id == "naming.pattern"
        assert response.message == "Name does not match pattern"
        assert response.severity == DomainPolicySeverity.ERROR
        assert response.field is None
        assert response.current_value is None
        assert response.expected_value is None

    @pytest.mark.unit
    def test_should_create_violation_response_with_optional_fields(self) -> None:
        """선택적 필드를 포함하여 위반 응답을 생성해야 한다."""
        # Arrange & Act
        response = PolicyViolationResponse(
            resource_type=DomainResourceType.TOPIC,
            resource_name="test-topic",
            rule_id="config.partitions",
            message="Partition count is too low",
            severity=DomainPolicySeverity.WARNING,
            field="config.partitions",
            current_value=1,
            expected_value=">= 3",
        )

        # Assert
        assert response.field == "config.partitions"
        assert response.current_value == 1
        assert response.expected_value == ">= 3"

    @pytest.mark.unit
    def test_should_require_non_empty_strings(self) -> None:
        """빈 문자열을 거부해야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="at least 1 character"):
            PolicyViolationResponse(
                resource_type=DomainResourceType.TOPIC,
                resource_name="",  # 빈 문자열
                rule_id="test",
                message="test",
                severity=DomainPolicySeverity.ERROR,
            )


class TestPolicyEvaluationResponse:
    """PolicyEvaluationResponse DTO 테스트"""

    @pytest.mark.unit
    def test_should_create_evaluation_response(self) -> None:
        """평가 응답을 생성해야 한다."""
        # Arrange
        violations = [
            PolicyViolationResponse(
                resource_type=DomainResourceType.TOPIC,
                resource_name="test",
                rule_id="rule1",
                message="Warning",
                severity=DomainPolicySeverity.WARNING,
            ),
            PolicyViolationResponse(
                resource_type=DomainResourceType.TOPIC,
                resource_name="test",
                rule_id="rule2",
                message="Error",
                severity=DomainPolicySeverity.ERROR,
            ),
        ]

        # Act
        response = PolicyEvaluationResponse(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            total_targets=2,
            violations=violations,
            has_blocking_violations=True,
            summary={"warning": 1, "error": 1},
        )

        # Assert
        assert response.environment == DomainEnvironment.PROD
        assert response.resource_type == DomainResourceType.TOPIC
        assert response.total_targets == 2
        assert len(response.violations) == 2
        assert response.has_blocking_violations is True
        assert response.summary == {"warning": 1, "error": 1}

    @pytest.mark.unit
    def test_should_require_non_negative_total_targets(self) -> None:
        """음수 대상 개수를 거부해야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            PolicyEvaluationResponse(
                environment=DomainEnvironment.PROD,
                resource_type=DomainResourceType.TOPIC,
                total_targets=-1,  # 음수
                violations=[],
                has_blocking_violations=False,
                summary={},
            )


class TestValidationSummaryResponse:
    """ValidationSummaryResponse DTO 테스트"""

    @pytest.mark.unit
    def test_should_create_success_summary(self) -> None:
        """성공 요약을 생성해야 한다."""
        # Arrange & Act
        summary = ValidationSummaryResponse(
            status="success",
            total_violations=0,
            blocking_violations=0,
            warning_violations=0,
            can_proceed=True,
        )

        # Assert
        assert summary.status == "success"
        assert summary.total_violations == 0
        assert summary.blocking_violations == 0
        assert summary.warning_violations == 0
        assert summary.can_proceed is True

    @pytest.mark.unit
    def test_should_create_error_summary(self) -> None:
        """에러 요약을 생성해야 한다."""
        # Arrange & Act
        summary = ValidationSummaryResponse(
            status="error",
            total_violations=3,
            blocking_violations=2,
            warning_violations=1,
            can_proceed=False,
        )

        # Assert
        assert summary.status == "error"
        assert summary.total_violations == 3
        assert summary.blocking_violations == 2
        assert summary.warning_violations == 1
        assert summary.can_proceed is False

    @pytest.mark.unit
    def test_should_require_non_negative_violation_counts(self) -> None:
        """음수 위반 개수를 거부해야 한다."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            ValidationSummaryResponse(
                status="error",
                total_violations=-1,  # 음수
                blocking_violations=0,
                warning_violations=0,
                can_proceed=False,
            )


class TestPolicyRouter:
    """Policy API 라우터 테스트"""

    @pytest.fixture
    def mock_evaluation_service(self) -> AsyncMock:
        """모의 정책 평가 서비스 픽스처"""
        return AsyncMock()

    @pytest.fixture
    def mock_management_service(self) -> AsyncMock:
        """모의 정책 관리 서비스 픽스처"""
        return AsyncMock()

    @pytest.fixture
    def mock_current_user(self) -> dict[str, str]:
        """모의 현재 사용자 픽스처"""
        return {"sub": "test-user", "name": "Test User"}

    @pytest.fixture
    def app(self, mock_current_user: dict[str, str]) -> FastAPI:
        """테스트용 FastAPI 앱 픽스처"""
        from fastapi import FastAPI

        from app.policy.interface.router import router
        from app.shared.auth import get_current_user

        app = FastAPI()
        app.include_router(router)

        # 의존성 오버라이드
        def mock_get_current_user_dep():
            return mock_current_user

        app.dependency_overrides[get_current_user] = mock_get_current_user_dep

        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """테스트 클라이언트 픽스처"""
        return TestClient(app)

    @pytest.mark.unit
    def test_should_evaluate_policies_successfully(
        self,
        client: TestClient,
        mock_current_user: dict[str, str],
    ) -> None:
        """정책을 성공적으로 평가해야 한다."""
        # Arrange - 완전히 모킹된 서비스 사용
        with (
            patch("app.policy.interface.router.policy_use_case_factory") as mock_factory,
            patch("app.policy.interface.router.optimize_violation_memory_usage") as mock_optimize,
        ):
            # Mock 서비스 설정 - 동기/비동기 메서드 구분
            from unittest.mock import Mock

            mock_service = Mock()
            mock_factory.get_policy_evaluation_service.return_value = mock_service
            mock_optimize.return_value = []

            # 비동기 메서드는 AsyncMock 사용
            mock_service.evaluate_batch = AsyncMock(return_value=[])
            # 동기 메서드는 일반 Mock 사용
            mock_service.has_blocking_violations.return_value = False
            mock_service.group_violations_by_severity.return_value = {}

            request_data = {
                "environment": "prod",
                "resource_type": "topic",
                "targets": [{"name": "user-events", "config": {"partitions": 3}}],
                "actor": "test-user",
            }

            # Act
            response = client.post("/v1/policies/evaluate", json=request_data)

            # Assert
            if response.status_code != status.HTTP_200_OK:
                print(f"Error response: {response.json()}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["environment"] == "prod"
            assert data["resource_type"] == "topic"
            assert data["total_targets"] == 1
            assert data["violations"] == []
            assert data["has_blocking_violations"] is False
            assert data["summary"] == {}

    @pytest.mark.unit
    def test_should_evaluate_policies_with_violations(
        self,
        client: TestClient,
        mock_current_user: dict[str, str],
    ) -> None:
        """위반이 있는 정책 평가를 처리해야 한다."""
        # Arrange
        with (
            patch("app.policy.interface.router.policy_use_case_factory") as mock_factory,
            patch("app.policy.interface.router.optimize_violation_memory_usage") as mock_optimize,
        ):
            # Mock 서비스 설정
            from unittest.mock import Mock

            mock_service = Mock()
            mock_factory.get_policy_evaluation_service.return_value = mock_service

            # 위반이 있는 케이스 - 도메인 모델 사용
            from app.policy.domain.models import DomainPolicyViolation

            violations = [
                DomainPolicyViolation(
                    resource_type=DomainResourceType.TOPIC,
                    resource_name="test-topic",
                    rule_id="naming.pattern",
                    message="Name does not match pattern",
                    severity=DomainPolicySeverity.ERROR,
                )
            ]

            mock_service.evaluate_batch = AsyncMock(return_value=violations)
            mock_service.has_blocking_violations.return_value = True
            mock_service.group_violations_by_severity.return_value = {"error": violations}
            mock_optimize.return_value = violations

            request_data = {
                "environment": "prod",
                "resource_type": "topic",
                "targets": [{"name": "InvalidName"}],
                "actor": "test-user",
            }

            # Act
            response = client.post("/v1/policies/evaluate", json=request_data)

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["has_blocking_violations"] is True
            assert len(data["violations"]) == 1
            assert data["violations"][0]["rule_id"] == "naming.pattern"
            assert data["summary"] == {"error": 1}

    @pytest.mark.unit
    def test_should_return_400_for_invalid_request(self, client: TestClient) -> None:
        """잘못된 요청에 대해 400을 반환해야 한다."""
        # Arrange
        invalid_request_data = {
            "environment": "invalid_env",  # 잘못된 환경
            "resource_type": "topic",
            "targets": [{"name": "test"}],
            "actor": "test-user",
        }

        # Act
        response = client.post("/v1/policies/evaluate", json=invalid_request_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    @patch("app.policy.interface.router.policy_use_case_factory")
    @patch("app.policy.interface.router.optimize_violation_memory_usage")
    def test_should_return_500_for_internal_error(
        self,
        mock_optimize,
        mock_factory,
        client: TestClient,
        mock_evaluation_service: AsyncMock,
        mock_current_user: dict[str, str],
    ) -> None:
        """내부 에러에 대해 500을 반환해야 한다."""
        # Arrange
        mock_factory.get_policy_evaluation_service.return_value = mock_evaluation_service
        mock_optimize.return_value = []

        # 서비스에서 예외 발생
        mock_evaluation_service.evaluate_batch.side_effect = Exception("Internal error")

        request_data = {
            "environment": "prod",
            "resource_type": "topic",
            "targets": [{"name": "test"}],
            "actor": "test-user",
        }

        # Act
        response = client.post("/v1/policies/evaluate", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.unit
    def test_should_require_authentication(self) -> None:
        """인증이 필요해야 한다."""
        # Arrange - 인증 없는 클라이언트 사용
        from fastapi import FastAPI

        from app.policy.interface.router import router

        app = FastAPI()
        app.include_router(router)
        # 의존성 오버라이드 없이 사용 (인증 실패 유도)

        client_no_auth = TestClient(app)

        request_data = {
            "environment": "prod",
            "resource_type": "topic",
            "targets": [{"name": "test"}],
            "actor": "test-user",
        }

        # Act
        response = client_no_auth.post("/v1/policies/evaluate", json=request_data)

        # Assert
        # get_current_user 의존성이 실패하면 401 또는 500 반환
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.unit
    @patch("app.policy.interface.router.policy_use_case_factory")
    @patch("app.policy.interface.router.optimize_violation_memory_usage")
    def test_should_handle_empty_targets_list(
        self,
        mock_optimize,
        mock_factory,
        client: TestClient,
        mock_current_user: dict[str, str],
    ) -> None:
        """빈 대상 목록을 처리해야 한다."""
        # Arrange
        request_data = {
            "environment": "prod",
            "resource_type": "topic",
            "targets": [],  # 빈 목록
            "actor": "test-user",
        }

        # Act
        response = client.post("/v1/policies/evaluate", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "targets" in str(data["detail"])

    @pytest.mark.unit
    def test_should_extract_actor_from_current_user(self) -> None:
        """현재 사용자에서 액터를 추출해야 한다."""
        # Arrange - 다른 사용자로 설정된 클라이언트

        app = FastAPI()
        app.include_router(router)

        # 다른 사용자로 오버라이드
        def mock_extracted_user():
            return {"sub": "extracted-user", "name": "Extracted User"}

        app.dependency_overrides[get_current_user] = mock_extracted_user
        client = TestClient(app)

        with (
            patch("app.policy.interface.router.policy_use_case_factory") as mock_factory,
            patch("app.policy.interface.router.optimize_violation_memory_usage") as mock_optimize,
        ):
            # Mock 서비스 설정
            from unittest.mock import Mock

            mock_service = Mock()
            mock_factory.get_policy_evaluation_service.return_value = mock_service

            mock_service.evaluate_batch = AsyncMock(return_value=[])
            mock_service.has_blocking_violations.return_value = False
            mock_service.group_violations_by_severity.return_value = {}
            mock_optimize.return_value = []

            request_data = {
                "environment": "prod",
                "resource_type": "topic",
                "targets": [{"name": "test"}],
                "actor": "request-user",  # 요청의 액터는 무시되고 토큰에서 추출
            }

            # Act
            response = client.post("/v1/policies/evaluate", json=request_data)

            # Assert
            assert response.status_code == status.HTTP_200_OK

            # 실제로 extracted-user가 사용되었는지 확인
            mock_service.evaluate_batch.assert_called_once()
            call_args = mock_service.evaluate_batch.call_args
            assert call_args.kwargs["actor"] == "extracted-user"
