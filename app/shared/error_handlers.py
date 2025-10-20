"""공통 API 에러 핸들링 유틸리티"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from fastapi import HTTPException, status
from pydantic import ValidationError

# 타입 변수 정의
T = TypeVar("T")  # 반환 타입
P = ParamSpec("P")  # 함수 파라미터

ErrorHandlerType = Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]


def format_validation_error(error: ValidationError) -> str:
    """
    Pydantic ValidationError를 사용자 친화적인 메시지로 변환

    Example:
        Input: "1 validation error for TopicBatchApplyResponse
                change_id
                  Input should be a valid string [type=string_type, input_value=20251020001]"

        Output: "YAML 형식 오류: change_id는 문자열이어야 합니다 (입력값: 20251020001)"
    """
    errors = []
    for err in error.errors():
        field = " → ".join(str(loc) for loc in err["loc"])
        error_type = err["type"]
        input_value = err.get("input", "N/A")

        # 에러 타입별 한글 메시지
        type_messages = {
            "string_type": f"{field}는 문자열이어야 합니다",
            "int_type": f"{field}는 정수여야 합니다",
            "missing": f"{field}는 필수 항목입니다",
            "value_error": f"{field}의 값이 유효하지 않습니다",
            "type_error": f"{field}의 타입이 올바르지 않습니다",
        }

        message = type_messages.get(error_type, f"{field}: {err['msg']}")

        # 입력값이 너무 길지 않으면 표시
        if str(input_value) not in ["N/A", "None"] and len(str(input_value)) < 100:
            message += f" (입력값: {input_value})"

        errors.append(message)

    return "YAML 형식 오류:\n" + "\n".join(f"  • {e}" for e in errors)


def endpoint_error_handler(
    error_mappings: dict[type[Exception], tuple[int, str]] | None = None,
    default_message: str = "Internal server error",
) -> ErrorHandlerType:
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
                        raise HTTPException(
                            status_code=status_code,
                            detail=f"{message_prefix}: {exc!s}",
                        ) from exc

                # 매핑되지 않은 예외는 500으로 처리
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"{default_message}: {exc!s}",
                ) from exc

        return wrapper

    return decorator


# 하위 호환성을 위한 기존 함수들 (내부적으로 endpoint_error_handler 사용)
def handle_api_errors(
    validation_error_message: str = "Validation error",
    validation_status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
) -> ErrorHandlerType:
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
        error_mappings={ValueError: (validation_status_code, validation_error_message)},
        default_message="Internal server error",
    )


def handle_server_errors(error_message: str = "Internal server error") -> ErrorHandlerType:
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
