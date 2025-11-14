"""공통 예외 처리 모듈"""

import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

import aiofiles
from pydantic import ValidationError

logger = logging.getLogger(__name__)
T = TypeVar("T")


class ParseError(Exception):
    """파싱 에러 기본 클래스"""

    def __init__(self, message: str, source_error: Exception | None = None) -> None:
        super().__init__(message)
        self.source_error = source_error


class ValidationParseError(ParseError):
    """검증 파싱 에러"""


class FormatParseError(ParseError):
    """포맷 파싱 에러"""


def safe_parse(
    operation_name: str,
    format_errors: tuple[type[Exception], ...] = (),
    validation_errors: tuple[type[Exception], ...] = (ValidationError,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """안전한 파싱을 위한 데코레이터

    Args:
        operation_name: 작업 이름 (로깅용)
        format_errors: 포맷 에러로 처리할 예외 타입들
        validation_errors: 검증 에러로 처리할 예외 타입들
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:  # 범용 데코레이터 - 다양한 함수 시그니처 지원
            try:
                return func(*args, **kwargs)
            except format_errors as e:
                logger.warning(f"{operation_name} format error: {e}")
                raise FormatParseError(f"{operation_name} format error: {e!s}") from e
            except validation_errors as e:
                logger.warning(f"{operation_name} validation error: {e}")
                raise ValidationParseError(f"{operation_name} validation error: {e!s}") from e
            except Exception as e:
                logger.error(f"{operation_name} unexpected error: {e}")
                raise ParseError(f"{operation_name} error: {e!s}") from e

        return wrapper

    return decorator


def safe_async_parse(
    operation_name: str,
    format_errors: tuple[type[Exception], ...] = (),
    validation_errors: tuple[type[Exception], ...] = (ValidationError,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """비동기 안전한 파싱을 위한 데코레이터

    Args:
        operation_name: 작업 이름 (로깅용)
        format_errors: 포맷 에러로 처리할 예외 타입들
        validation_errors: 검증 에러로 처리할 예외 타입들
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(
            *args: Any, **kwargs: Any
        ) -> T:  # 범용 데코레이터 - 다양한 함수 시그니처 지원
            try:
                return await func(*args, **kwargs)
            except format_errors as e:
                logger.warning(f"{operation_name} format error: {e}")
                raise FormatParseError(f"{operation_name} format error: {e!s}") from e
            except validation_errors as e:
                logger.warning(f"{operation_name} validation error: {e}")
                raise ValidationParseError(f"{operation_name} validation error: {e!s}") from e
            except Exception as e:
                logger.error(f"{operation_name} unexpected error: {e}")
                raise ParseError(f"{operation_name} error: {e!s}") from e

        return wrapper

    return decorator


async def safe_file_read(file_path: str) -> str:
    """안전한 비동기 파일 읽기"""
    try:
        # 비동기 파일 읽기 (I/O 바운드 작업) - aiofiles 사용
        async with aiofiles.open(file_path, encoding="utf-8") as f:
            content = await f.read()
        return content
    except FileNotFoundError as e:
        raise ParseError(f"File not found: {file_path}") from e
    except PermissionError as e:
        raise ParseError(f"Permission denied: {file_path}") from e
    except Exception as e:
        raise ParseError(f"File reading error: {e!s}") from e
