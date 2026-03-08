"""공통 API 에러 핸들링 유틸리티"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

# 타입 변수 정의
T = TypeVar("T")  # 반환 타입
P = ParamSpec("P")  # 함수 파라미터


def format_validation_error(error: ValidationError | RequestValidationError) -> str:
    """
    Pydantic ValidationError를 사용자 친화적인 메시지로 변환
    """
    errors = []

    # 정규표현식별 한국어 설명 매핑
    pattern_descriptions = {
        r"^[a-z0-9-]+$": "소문자, 숫자, 하이픈(-)만 사용할 수 있습니다.",
        r"^[a-z0-9._-]+(-key|-value)?$": "소문자, 숫자, 점(.), 밑줄(_), 하이픈(-)만 사용 가능하며 -key 또는 -value로 끝나야 할 수 있습니다.",
        r"^https?://.+$": "올바른 HTTP/HTTPS URL 형식이어야 합니다. (예: http://...)",
        r"^[a-zA-Z0-9_-]+$": "영문, 숫자, 하이픈(-), 밑줄(_)만 사용할 수 있습니다.",
    }

    for err in error.errors():
        # 필드 경로를 읽기 쉽게 변환 (그리드 경로 등)
        loc_parts = []
        for loc in err["loc"]:
            if isinstance(loc, int):
                loc_parts.append("[" + str(loc + 1) + "번째 항목]")
            else:
                loc_parts.append(str(loc))

        field = " → ".join(loc_parts)
        error_type = err["type"]
        input_value = err.get("input", "N/A")
        msg = err["msg"]

        # 에러 타입별 한글 메시지
        if error_type == "string_pattern_mismatch":
            pattern = err.get("ctx", {}).get("pattern", "")
            friendly_pattern = pattern_descriptions.get(
                pattern, f"패턴({pattern})이 일치하지 않습니다."
            )
            message = f"{field}: 형식이 올바르지 않습니다. {friendly_pattern}"
        elif error_type == "string_type":
            message = f"{field}: 문자열이어야 합니다"
        elif error_type == "int_type":
            message = f"{field}: 정수여야 합니다"
        elif error_type == "missing":
            message = f"{field}: 필수 입력 항목입니다"
        elif error_type == "value_error":
            message = f"{field}: {msg.replace('Value error, ', '')}"
        elif "enumeration" in error_type:
            allowed = err.get("ctx", {}).get("expected", "")
            message = f"{field}: 허용되지 않는 값입니다. (허용값: {allowed})"
        else:
            message = f"{field}: {msg}"

        # 입력값이 너무 길지 않으면 표시
        if (
            str(input_value) not in ["N/A", "None"]
            and len(str(input_value)) < 100
            and error_type != "missing"
        ):
            message += f" (입력값: {input_value})"

        errors.append(message)

    return "데이터 유효성 검사 실패:\n" + "\n".join(f"  • {e}" for e in errors)


def endpoint_error_handler(
    error_mappings: dict[type[Exception], tuple[int, str]] | None = None,
    default_message: str = "Internal server error",
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    다양한 예외를 HTTP 에러로 변환하는 범용 데코레이터

    예외 타입별로 상태 코드와 메시지를 매핑하여 처리합니다.
    HTTPException은 그대로 re-raise하며, 매핑되지 않은 예외는 500으로 처리됩니다.

    Args:
        error_mappings: {예외_클래스: (상태_코드, 메시지_prefix)} 매핑 딕셔너리
        default_message: 매핑되지 않은 예외 발생 시 메시지 prefix

    Usage:
        # 기본 사용 (ValueError -> 422, 나머지 -> 500)
        @endpoint_error_handler(
            error_mappings={
                ValueError: (422, "Validation error"),
                PermissionError: (403, "Permission denied"),
            }
        )
        async def my_endpoint():
            ...
    """
    mappings = error_mappings or {
        ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")
    }

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # FastAPI HTTPException은 그대로 전달
                raise
            except ValidationError as exc:
                # Pydantic ValidationError는 사용자 친화적인 메시지로 변환
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=format_validation_error(exc),
                ) from exc
            except Exception as exc:
                # 예외 타입에 따라 매핑된 상태 코드와 메시지 사용
                for exc_type, (status_code, message_prefix) in mappings.items():
                    if isinstance(exc, exc_type):
                        # 4xx 에러인 경우 사용자에게 구체적인 실패 원인을 알려주는 것이 좋습니다 (예: 스키마 문법 오류 등).
                        # 5xx 에러인 경우에만 내부 구현 정보를 숨기기 위해 prefix만 사용합니다.
                        detail = (
                            f"{message_prefix}: {exc!s}" if status_code < 500 else message_prefix
                        )
                        raise HTTPException(
                            status_code=status_code,
                            detail=detail,
                        ) from exc

                # 매핑되지 않은 예외는 500으로 처리 (보안을 위해 내부 에러 메시지 노출 방지)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=default_message,
                ) from exc

        return wrapper

    return decorator


# 하위 호환성을 위한 기존 함수들 (내부적으로 endpoint_error_handler 사용)
def handle_api_errors(
    validation_error_message: str = "Validation error",
    validation_status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    ValueError와 Exception을 처리하는 데코레이터 (하위 호환성 유지)

    ValueError -> validation_status_code (기본: 422)
    Exception -> 500 Internal Server Error

    Args:
        validation_error_message: ValueError 발생 시 에러 메시지 prefix
        validation_status_code: ValueError 발생 시 HTTP 상태 코드 (기본: 422)

    Usage:
        @handle_api_errors(validation_error_message="Policy violation")
        async def my_endpoint():
            ...
    """
    return endpoint_error_handler(
        error_mappings={
            ValueError: (validation_status_code, validation_error_message),
            RuntimeError: (validation_status_code, validation_error_message),
        },
        default_message="An internal server error occurred",
    )


def handle_server_errors(
    error_message: str = "Internal server error",
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Exception만 처리하는 데코레이터 (하위 호환성 유지)

    모든 Exception -> 500 Internal Server Error

    Args:
        error_message: Exception 발생 시 에러 메시지 prefix

    Usage:
        @handle_server_errors(error_message="Schema sync failed")
        async def my_endpoint():
            ...
    """
    return endpoint_error_handler(
        error_mappings={},
        default_message=error_message,
    )
