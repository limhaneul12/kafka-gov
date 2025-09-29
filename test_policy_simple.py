#!/usr/bin/env python3
"""간단한 Policy 테스트"""

import sys
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Policy 라우터 추가
from app.policy.interface.router import router
from app.shared.auth import get_current_user

# FastAPI 앱 생성
app = FastAPI()


app.include_router(router)


# 의존성 오버라이드
def mock_get_current_user(request):
    return {"sub": "test-user", "name": "Test User"}


app.dependency_overrides[get_current_user] = mock_get_current_user

# 테스트 클라이언트
client = TestClient(app)

# 모킹
with (
    patch("app.policy.interface.router.policy_use_case_factory") as mock_factory,
    patch("app.policy.interface.router.optimize_violation_memory_usage") as mock_optimize,
):
    # Mock 설정
    mock_service = AsyncMock()
    mock_factory.get_policy_evaluation_service.return_value = mock_service
    mock_optimize.return_value = []

    mock_service.evaluate_batch.return_value = []
    mock_service.has_blocking_violations.return_value = False
    mock_service.group_violations_by_severity.return_value = {}

    # 요청 데이터
    request_data = {
        "environment": "prod",
        "resource_type": "topic",
        "targets": [{"name": "user-events", "config": {"partitions": 3}}],
        "actor": "test-user",
    }

    # 테스트 실행
    response = client.post("/v1/policies/evaluate", json=request_data)

    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.json()}")
        sys.exit(1)
    else:
        print("Test passed!")
        print(f"Response: {response.json()}")
