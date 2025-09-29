"""Topic 라우터 에러 경로 커버리지 보강"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.database import get_db_session
from app.topic.interface.router import router


def _make_app(test_db_session) -> TestClient:
    app = FastAPI()

    async def _override_get_db_session():
        yield test_db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    app.include_router(router)
    return TestClient(app)


@patch("app.topic.interface.router.get_detail_use_case")
@patch("app.shared.auth.get_current_user")
def test_topic_detail_500_when_config_unparsable(
    mock_get_user: AsyncMock,
    mock_get_use_case: AsyncMock,
    test_db_session,
) -> None:
    """Kafka 메타데이터에서 config를 파생할 수 없으면 500을 반환해야 한다."""
    client = _make_app(test_db_session)
    mock_get_user.return_value = "tester"

    mock_use_case = AsyncMock()
    # partition_count 없음, config에도 num.partitions 없음 -> interface_config None
    mock_use_case.execute.return_value = {
        "name": "dev.bad.topic",
        "kafka_metadata": {"config": {"retention.ms": "1000"}},
        "metadata": {},
    }
    mock_get_use_case.return_value = mock_use_case

    response = client.get("/v1/topics/dev.bad.topic")
    assert response.status_code == 500


@patch("app.topic.interface.router.get_plan_use_case")
@patch("app.shared.auth.get_current_user")
def test_topic_plan_404_when_missing(
    mock_get_user: AsyncMock,
    mock_get_use_case: AsyncMock,
    test_db_session,
) -> None:
    """계획이 없으면 404를 반환해야 한다."""
    client = _make_app(test_db_session)
    mock_get_user.return_value = "tester"

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = None
    mock_get_use_case.return_value = mock_use_case

    response = client.get("/v1/topics/plans/nonexistent")
    assert response.status_code == 404
