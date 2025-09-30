"""테스트 헬퍼 함수들"""

from __future__ import annotations

import json
from typing import Any


def assert_dict_contains(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """실제 딕셔너리가 기대하는 키-값을 포함하는지 검증"""
    for key, value in expected.items():
        assert key in actual, f"Key '{key}' not found in actual dict"
        assert actual[key] == value, f"Value mismatch for key '{key}': {actual[key]} != {value}"


def assert_json_equal(actual: str, expected: str) -> None:
    """JSON 문자열 비교 (순서 무시)"""
    actual_obj = json.loads(actual)
    expected_obj = json.loads(expected)
    assert actual_obj == expected_obj


def normalize_whitespace(text: str) -> str:
    """공백 정규화 (비교용)"""
    return " ".join(text.split())


def is_valid_iso_datetime(dt_str: str) -> bool:
    """ISO 8601 날짜 형식 검증"""
    from datetime import datetime

    try:
        datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return True
    except (ValueError, AttributeError):
        return False


async def async_noop(*args: Any, **kwargs: Any) -> None:
    """비동기 no-op 함수 (Mock용)"""
    return None


def create_mock_response(status_code: int = 200, json_data: dict[str, Any] | None = None) -> Any:
    """Mock HTTP 응답 객체 생성"""

    class MockResponse:
        def __init__(self, status_code: int, json_data: dict[str, Any] | None):
            self.status_code = status_code
            self._json_data = json_data or {}

        async def json(self) -> dict[str, Any]:
            return self._json_data

        async def text(self) -> str:
            return json.dumps(self._json_data)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    return MockResponse(status_code, json_data)
