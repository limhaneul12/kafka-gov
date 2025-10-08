"""Schema Registry 에러 핸들링 유틸리티 - 이식 가능한 데코레이터"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from confluent_kafka.schema_registry.error import SchemaRegistryError

logger = logging.getLogger(__name__)

# 타입 변수 정의
P = ParamSpec("P")
R = TypeVar("R")


def handle_schema_registry_error(
    operation: str, context_builder: Callable[..., str] | None = None
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Schema Registry 에러를 자동으로 처리하는 데코레이터

    **이식성**: 이 데코레이터는 다른 모듈/프로젝트에서도 재사용 가능

    Args:
        operation: 작업 이름 (예: "Schema registration", "List subjects")
        context_builder: 컨텍스트 문자열을 생성하는 함수 (선택적)
            함수의 인자를 받아서 컨텍스트 문자열을 반환

    Returns:
        데코레이터 함수

    Example:
        # 기본 사용 (자동으로 subject 추출)
        @handle_schema_registry_error("Delete subject")
        async def delete_subject(self, subject: str) -> None:
            await self.client.delete_subject(subject)

        # 커스텀 컨텍스트 빌더 (복잡한 컨텍스트)
        @handle_schema_registry_error(
            "Get schema",
            lambda self, subject, version: f"{subject} v{version}"
        )
        async def get_schema_by_version(self, subject: str, version: int):
            return await self.client.get_version(subject, version)

        # 다른 프로젝트에서도 동일하게 사용 가능
        from your_module.error_handlers import handle_schema_registry_error

        @handle_schema_registry_error("Custom operation")
        async def your_function(self, param: str) -> Result:
            return await self.client.some_method(param)
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await func(*args, **kwargs)
            except SchemaRegistryError as e:
                # 컨텍스트 정보 추출
                context = ""
                if context_builder:
                    with suppress(Exception):
                        # 컨텍스트 빌더 실패 시 빈 문자열 사용
                        context = context_builder(*args, **kwargs)
                else:
                    # 기본 로직: subject 파라미터 자동 추출
                    args_tuple: tuple[Any, ...] = args
                    kwargs_dict: dict[str, Any] = kwargs
                    if len(args_tuple) > 1 and isinstance(args_tuple[1], str):
                        context = args_tuple[1]
                    elif "subject" in kwargs_dict:
                        context = str(kwargs_dict["subject"])

                # 에러 메시지 구성 및 로깅
                context_msg = f" ({context})" if context else ""
                error_msg = f"{operation} failed{context_msg}: {e}"
                logger.error(error_msg)

                # 도메인 예외로 변환하여 발생
                raise RuntimeError(error_msg) from e

        return async_wrapper

    return decorator
