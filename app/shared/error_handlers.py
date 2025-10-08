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


def handle_api_errors(
    validation_error_message: str = "Validation error",
    validation_status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
) -> ErrorHandlerType:
    """
    ValueError와 Exception을 처리하는 데코레이터

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

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except ValueError as exc:
                raise HTTPException(
                    status_code=validation_status_code,
                    detail=f"{validation_error_message}: {exc!s}",
                ) from exc
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal server error: {exc!s}",
                ) from exc

        return wrapper

    return decorator


def handle_server_errors(error_message: str = "Internal server error") -> ErrorHandlerType:
    """
    Exception만 처리하는 데코레이터

    모든 Exception -> 500 Internal Server Error

    Args:
        error_message: Exception 발생 시 에러 메시지 prefix

    Usage:
        @handle_server_errors(error_message="Schema sync failed")
        async def my_endpoint():
            ...
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"{error_message}: {exc!s}",
                ) from exc

        return wrapper

    return decorator
