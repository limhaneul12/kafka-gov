"""Topic 인터페이스 레이어 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.policy.domain.models import (
    DomainPolicySeverity as PolicySeverity,
    DomainPolicyViolation as PolicyViolation,
    DomainResourceType as ResourceType,
)
from app.shared.database import get_db_session
from app.topic.domain.models import (
    DomainEnvironment as Environment,
    DomainPlanAction as PlanAction,
    DomainTopicAction as TopicAction,
    DomainTopicApplyResult as TopicApplyResult,
    DomainTopicBatch as TopicBatch,
    DomainTopicPlan as TopicPlan,
    DomainTopicPlanItem as TopicPlanItem,
)
from app.topic.interface.adapters import (
    safe_convert_plan_to_response,
    safe_convert_request_to_batch,
)
from app.topic.interface.router import router
from app.topic.interface.schema import (
    TopicBatchApplyResponse,
    TopicBatchDryRunResponse,
    TopicBatchRequest,
    TopicDetailResponse,
    TopicPlanResponse,
)


class TestTopicBatchRequest:
    """TopicBatchRequest 스키마 테스트."""

    def test_should_create_valid_request(self) -> None:
        """유효한 요청을 생성해야 한다."""
        # Arrange & Act
        request_data = {
            "change_id": "change-123",
            "env": "dev",
            "items": [
                {
                    "name": "dev.user.events",
                    "action": "create",
                    "config": {
                        "partitions": 3,
                        "replication_factor": 2,
                    },
                    "metadata": {
                        "owner": "data-team",
                    },
                }
            ],
        }

        request = TopicBatchRequest.model_validate(request_data)

        # Assert
        assert request.change_id == "change-123"
        assert request.env == "dev"
        assert len(request.items) == 1
        assert request.items[0].name == "dev.user.events"
        assert request.items[0].action == "create"

    def test_should_validate_required_fields(self) -> None:
        """필수 필드를 검증해야 한다."""
        # Arrange
        invalid_data = {
            "change_id": "",  # 빈 문자열
            "env": "dev",
            "items": [],  # 빈 리스트
        }

        # Act & Assert
        with pytest.raises(ValueError):
            TopicBatchRequest.model_validate(invalid_data)

    def test_should_validate_environment_values(self) -> None:
        """환경 값을 검증해야 한다."""
        # Arrange
        invalid_data = {
            "change_id": "change-123",
            "env": "invalid",  # 유효하지 않은 환경
            "items": [
                {
                    "name": "dev.user.events",
                    "action": "create",
                    "config": {"partitions": 3, "replication_factor": 2},
                    "metadata": {"owner": "data-team"},
                }
            ],
        }

        # Act & Assert
        with pytest.raises(ValueError):
            TopicBatchRequest.model_validate(invalid_data)

    def test_should_validate_topic_config(self) -> None:
        """토픽 설정을 검증해야 한다."""
        # Arrange
        invalid_data = {
            "change_id": "change-123",
            "env": "dev",
            "items": [
                {
                    "name": "dev.user.events",
                    "action": "create",
                    "config": {
                        "partitions": 0,  # 유효하지 않은 파티션 수
                        "replication_factor": 2,
                    },
                    "metadata": {"owner": "data-team"},
                }
            ],
        }

        # Act & Assert
        with pytest.raises(ValueError):
            TopicBatchRequest.model_validate(invalid_data)


class TestTopicAdapters:
    """Topic 어댑터 테스트."""

    @pytest.fixture
    def sample_request(self) -> TopicBatchRequest:
        """샘플 요청."""
        request_data = {
            "change_id": "change-123",
            "env": "dev",
            "items": [
                {
                    "name": "dev.user.events",
                    "action": "create",
                    "config": {
                        "partitions": 3,
                        "replication_factor": 2,
                    },
                    "metadata": {
                        "owner": "data-team",
                    },
                }
            ],
        }
        return TopicBatchRequest.model_validate(request_data)

    @pytest.fixture
    def sample_plan(self) -> TopicPlan:
        """샘플 계획."""
        item = TopicPlanItem(
            name="dev.user.events",
            action=PlanAction.CREATE,
            diff={"status": "new→created"},
            target_config={"partitions": "3", "replication.factor": "2"},
        )

        violation = PolicyViolation(
            resource_type=ResourceType.TOPIC,
            resource_name="dev.user.events",
            rule_id="naming_rule",
            message="토픽 이름이 권장 패턴과 다릅니다",
            severity=PolicySeverity.WARNING,
        )

        return TopicPlan(
            change_id="change-123",
            env=Environment.DEV,
            items=(item,),
            violations=(violation,),
        )

    def test_should_convert_request_to_batch(self, sample_request: TopicBatchRequest) -> None:
        """요청을 배치로 변환해야 한다."""
        # Act
        batch = safe_convert_request_to_batch(sample_request)

        # Assert
        assert isinstance(batch, TopicBatch)
        assert batch.change_id == "change-123"
        assert batch.env == Environment.DEV
        assert len(batch.specs) == 1
        assert batch.specs[0].name == "dev.user.events"
        assert batch.specs[0].action == TopicAction.CREATE

    def test_should_convert_plan_to_response(
        self, sample_plan: TopicPlan, sample_request: TopicBatchRequest
    ) -> None:
        """계획을 응답으로 변환해야 한다."""
        # Act
        response = safe_convert_plan_to_response(sample_plan, sample_request)

        # Assert
        assert isinstance(response, TopicBatchDryRunResponse)
        assert response.change_id == "change-123"
        assert response.env == "dev"
        assert len(response.plan) == 1
        assert response.plan[0].name == "dev.user.events"
        assert response.plan[0].action == "CREATE"

    def test_should_handle_conversion_error(self) -> None:
        """변환 에러를 처리해야 한다."""
        # Arrange
        invalid_request_data = {
            "change_id": "change-123",
            "env": "dev",
            "items": [
                {
                    "name": "",  # 빈 이름
                    "action": "create",
                    "config": {"partitions": 3, "replication_factor": 2},
                    "metadata": {"owner": "data-team"},
                }
            ],
        }

        # Act & Assert
        with pytest.raises(ValueError):
            request = TopicBatchRequest.model_validate(invalid_request_data)
            safe_convert_request_to_batch(request)


class TestTopicRouter:
    """Topic 라우터 테스트."""

    @pytest.fixture
    def client(self, test_db_session) -> TestClient:
        """테스트 클라이언트."""

        app = FastAPI()

        # 전역 DB 의존성 오버라이드 (SQLite 세션 주입)
        async def _override_get_db_session():
            yield test_db_session

        app.dependency_overrides[get_db_session] = _override_get_db_session
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def sample_request_data(self) -> dict:
        """샘플 요청 데이터."""
        return {
            "change_id": "change-123",
            "env": "dev",
            "items": [
                {
                    "name": "dev.user.events",
                    "action": "create",
                    "config": {
                        "partitions": 3,
                        "replication_factor": 2,
                    },
                    "metadata": {
                        "owner": "data-team",
                    },
                }
            ],
        }

    @patch("app.topic.interface.router.get_dry_run_use_case")
    @patch("app.shared.auth.get_current_user")
    def test_should_handle_dry_run_request(
        self,
        mock_get_user: AsyncMock,
        mock_get_use_case: AsyncMock,
        client: TestClient,
        sample_request_data: dict,
    ) -> None:
        """Dry-run 요청을 처리해야 한다."""
        # Arrange
        mock_get_user.return_value = "test-user"

        mock_use_case = AsyncMock()
        mock_plan = TopicPlan(
            change_id="change-123",
            env=Environment.DEV,
            items=(),
            violations=(),
        )
        mock_use_case.execute.return_value = mock_plan
        mock_get_use_case.return_value = mock_use_case
        response = client.post("/v1/topics/batch/dry-run", json=sample_request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["change_id"] == "change-123"
        assert data["env"] == "dev"

    @patch("app.topic.interface.router.get_apply_use_case")
    @patch("app.shared.auth.get_current_user")
    def test_should_handle_apply_request(
        self,
        mock_get_user: AsyncMock,
        mock_get_use_case: AsyncMock,
        client: TestClient,
        sample_request_data: dict,
    ) -> None:
        """Apply 요청을 처리해야 한다."""
        # Arrange
        mock_get_user.return_value = "test-user"

        mock_use_case = AsyncMock()
        mock_result = TopicApplyResult(
            change_id="change-123",
            env=Environment.DEV,
            applied=("dev.user.events",),
            skipped=(),
            failed=(),
            audit_id="audit-456",
        )
        mock_use_case.execute.return_value = mock_result
        mock_get_use_case.return_value = mock_use_case

        # Act
        response = client.post("/v1/topics/batch/apply", json=sample_request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["change_id"] == "change-123"
        assert data["env"] == "dev"

    @patch("app.shared.auth.get_current_user")
    def test_should_handle_validation_error(
        self,
        mock_get_user: AsyncMock,
        client: TestClient,
    ) -> None:
        """검증 에러를 처리해야 한다."""
        # Arrange
        mock_get_user.return_value = "test-user"

        invalid_data = {
            "change_id": "",  # 빈 문자열
            "env": "dev",
            "items": [],
        }

        # Act
        response = client.post("/v1/topics/batch/dry-run", json=invalid_data)

        # Assert
        assert response.status_code == 422

    @patch("app.topic.interface.router.get_dry_run_use_case")
    @patch("app.shared.auth.get_current_user")
    def test_should_handle_internal_server_error(
        self,
        mock_get_user: AsyncMock,
        mock_get_use_case: AsyncMock,
        client: TestClient,
        sample_request_data: dict,
    ) -> None:
        """내부 서버 에러를 처리해야 한다."""
        # Arrange
        mock_get_user.return_value = "test-user"

        mock_use_case = AsyncMock()
        mock_use_case.execute.side_effect = Exception("Internal error")
        mock_get_use_case.return_value = mock_use_case

        # Act
        response = client.post("/v1/topics/batch/dry-run", json=sample_request_data)

        # Assert
        assert response.status_code == 500

    @patch("app.topic.interface.router.get_detail_use_case")
    @patch("app.shared.auth.get_current_user")
    def test_should_handle_topic_detail_request(
        self,
        mock_get_user: AsyncMock,
        mock_get_use_case: AsyncMock,
        client: TestClient,
    ) -> None:
        """토픽 상세 조회 요청을 처리해야 한다."""
        # Arrange
        mock_get_user.return_value = "test-user"

        mock_use_case = AsyncMock()
        mock_detail = {
            "name": "dev.user.events",
            "kafka_metadata": {"partition_count": 3, "replication_factor": 2},
            "metadata": {"owner": "data-team"},
        }
        mock_use_case.execute.return_value = mock_detail
        mock_get_use_case.return_value = mock_use_case

        # Act
        response = client.get("/v1/topics/dev.user.events")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "dev.user.events"

    @patch("app.topic.interface.router.get_detail_use_case")
    @patch("app.shared.auth.get_current_user")
    def test_should_handle_nonexistent_topic(
        self,
        mock_get_user: AsyncMock,
        mock_get_use_case: AsyncMock,
        client: TestClient,
    ) -> None:
        """존재하지 않는 토픽을 처리해야 한다."""
        # Arrange
        mock_get_user.return_value = "test-user"

        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = None
        mock_get_use_case.return_value = mock_use_case

        # Act
        response = client.get("/v1/topics/nonexistent.topic")

        # Assert
        assert response.status_code == 404

    @patch("app.topic.interface.router.get_plan_use_case")
    @patch("app.shared.auth.get_current_user")
    def test_should_handle_plan_request(
        self,
        mock_get_user: AsyncMock,
        mock_get_use_case: AsyncMock,
        client: TestClient,
    ) -> None:
        """계획 조회 요청을 처리해야 한다."""
        # Arrange
        mock_get_user.return_value = "test-user"

        mock_use_case = AsyncMock()
        mock_plan = TopicPlan(
            change_id="change-123",
            env=Environment.DEV,
            items=(),
            violations=(),
        )
        mock_use_case.execute.return_value = mock_plan
        # 새 계약: 메타 정보 리턴(mock)
        mock_use_case.get_meta.return_value = {
            "status": "pending",
            "created_at": "2025-09-27T00:00:00Z",
            "applied_at": None,
        }
        mock_get_use_case.return_value = mock_use_case

        # Act
        response = client.get("/v1/topics/plans/change-123")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["change_id"] == "change-123"


class TestTopicResponseSchemas:
    """Topic 응답 스키마 테스트."""

    def test_should_create_dry_run_response(self) -> None:
        """Dry-run 응답을 생성해야 한다."""
        # Arrange
        response_data = {
            "change_id": "change-123",
            "env": "dev",
            "plan": [
                {
                    "name": "dev.user.events",
                    "action": "CREATE",
                    "diff": {"status": "new→created"},
                    "current_config": None,
                    "target_config": {"partitions": "3"},
                }
            ],
            "violations": [],
            "summary": {
                "total_items": 1,
                "create_count": 1,
                "alter_count": 0,
                "delete_count": 0,
                "violation_count": 0,
            },
        }

        # Act
        response = TopicBatchDryRunResponse.model_validate(response_data)

        # Assert
        assert response.change_id == "change-123"
        assert response.env == "dev"
        assert len(response.plan) == 1

    def test_should_create_apply_response(self) -> None:
        """Apply 응답을 생성해야 한다."""
        # Arrange
        response_data = {
            "change_id": "change-123",
            "env": "dev",
            "applied": ["dev.user.events"],
            "skipped": [],
            "failed": [],
            "audit_id": "audit-456",
            "summary": {
                "total_items": 1,
                "applied_count": 1,
                "skipped_count": 0,
                "failed_count": 0,
            },
        }

        # Act
        response = TopicBatchApplyResponse.model_validate(response_data)

        # Assert
        assert response.change_id == "change-123"
        assert response.env == "dev"
        assert len(response.applied) == 1
        assert response.audit_id == "audit-456"

    def test_should_create_detail_response(self) -> None:
        """상세 조회 응답을 생성해야 한다."""
        # Arrange
        response_data = {
            "name": "dev.user.events",
            "config": {
                "partitions": 3,
                "replication_factor": 2,
            },
            "kafka_metadata": {
                "partition_count": 3,
                "leader_replicas": [1, 2, 3],
                "created_at": "2025-09-25T10:00:00Z",
            },
            "metadata": {
                "owner": "data-team",
                "sla": "99.9%",
            },
        }

        # Act
        response = TopicDetailResponse.model_validate(response_data)

        # Assert
        assert response.name == "dev.user.events"
        assert response.kafka_metadata.partition_count == 3
        assert response.metadata.owner == "data-team"

    def test_should_create_plan_response(self) -> None:
        """계획 조회 응답을 생성해야 한다 (신규 계약)."""
        # Arrange
        response_data = {
            "change_id": "change-123",
            "env": "dev",
            "status": "pending",
            "created_at": "2025-09-27T00:00:00Z",
            "applied_at": None,
            "plan": [
                {
                    "name": "dev.user.events",
                    "action": "CREATE",
                    "diff": {"status": "new→created"},
                    "current_config": None,
                    "target_config": {"partitions": "3"},
                }
            ],
        }

        # Act
        response = TopicPlanResponse.model_validate(response_data)

        # Assert
        assert response.change_id == "change-123"
        assert response.env == "dev"
        assert response.status == "pending"
        assert response.applied_at is None
        assert len(response.plan) == 1
