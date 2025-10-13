"""공통 API 에러 핸들링 유틸리티"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from fastapi import HTTPException, status

# 타입 변수 정의
T = TypeVar("T")  # 반환 타입
P = ParamSpec("P")  # 함수 파라미터

ErrorHandlerType = Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]


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
