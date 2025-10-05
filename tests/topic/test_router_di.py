"""Topic Router DI 패턴 검증 테스트"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.topic.container import container


@pytest.fixture
def mock_use_cases():
    """UseCase Mock 설정"""
    # Container의 UseCase Provider를 Mock으로 교체
    mock_dry_run = AsyncMock()
    mock_dry_run.execute.return_value = MagicMock(
        env="dev",
        items=[],
        can_apply=True,
        policy_violations=[],
    )

    mock_apply = AsyncMock()
    mock_apply.execute.return_value = MagicMock(
        applied=[],
        skipped=[],
        failed=[],
        audit_id="test-audit-123",
        summary=lambda: "Test summary",
    )

    mock_list = AsyncMock()
    mock_list.execute.return_value = []

    # Container override
    with container.dry_run_use_case.override(mock_dry_run):
        with container.apply_use_case.override(mock_apply):
            with container.list_use_case.override(mock_list):
                yield {
                    "dry_run": mock_dry_run,
                    "apply": mock_apply,
                    "list": mock_list,
                }


@pytest.mark.skip(reason="Requires MySQL connection - integration test")
def test_provide_pattern_works(mock_use_cases):
    """Provide 패턴이 실제로 작동하는지 검증"""
    app = create_app()
    client = TestClient(app)

    # List API 호출
    response = client.get("/api/v1/topics")

    # 에러 확인
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # 200 응답이면 DI가 작동한 것
    assert response.status_code == 200

    # Mock이 호출되었는지 확인
    assert mock_use_cases["list"].execute.called


@pytest.mark.skip(reason="Requires MySQL connection - integration test")
def test_dry_run_endpoint_di(mock_use_cases):
    """Dry-Run 엔드포인트 DI 검증"""
    app = create_app()
    client = TestClient(app)

    request_data = {
        "env": "dev",
        "change_id": "test-change-123",
        "topics": [],
    }

    response = client.post("/api/v1/topics/batch/dry-run", json=request_data)

    # DI가 작동하면 200
    assert response.status_code == 200
    assert mock_use_cases["dry_run"].execute.called
