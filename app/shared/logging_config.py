"""구조화 로깅 설정 - structlog + standard library logging 통합

structlog를 사용하여 JSON 기반 구조화 로깅 제공:
- 개발 환경: 컬러 콘솔 출력
- 프로덕션: JSON 출력
- trace_id 자동 전파 (asyncio context variables)
- 민감 정보 마스킹

Usage:
    from app.shared.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("user_login", user_id="user123", email="test@example.com")
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from .settings import settings


def mask_sensitive_keys(logger: Any, method_name: str, event_dict: dict) -> dict:
    """민감 정보 마스킹 processor

    password, token, secret, api_key 등의 키를 자동으로 마스킹
    """
    sensitive_keys = {
        "password",
        "passwd",
        "pwd",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "sasl_password",
        "ssl_key",
    }

    for key in event_dict:
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            event_dict[key] = "***MASKED***"

    return event_dict


def add_app_context(logger: Any, method_name: str, event_dict: dict) -> dict:
    """애플리케이션 컨텍스트 추가 processor"""
    event_dict["app_name"] = settings.app_name
    event_dict["environment"] = settings.environment
    return event_dict


def configure_structlog() -> None:
    """structlog 전역 설정

    개발 환경: 컬러 콘솔 렌더러
    프로덕션: JSON 렌더러
    """
    # 개발 환경: 가독성 좋은 콘솔 출력
    if settings.is_development:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            mask_sensitive_keys,
            add_app_context,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]

        formatter = structlog.stdlib.ProcessorFormatter(
            # 표준 logging에서 들어온 로그도 structlog 스타일로 처리
            foreign_pre_chain=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
            ],
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
        )

    # 프로덕션: JSON 출력 (로그 수집 시스템 연동)
    else:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            mask_sensitive_keys,
            add_app_context,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]

        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
            ],
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )

    # structlog 설정
    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 표준 logging 설정
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # 기존 핸들러 제거
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)

    # 외부 라이브러리 로깅 레벨 조정
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aiokafka").setLevel(logging.WARNING)
    logging.getLogger("confluent_kafka").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """구조화 로거 인스턴스 반환

    Args:
        name: 로거 이름 (보통 __name__)

    Returns:
        structlog.stdlib.BoundLogger 인스턴스

    Example:
        logger = get_logger(__name__)
        logger.info("topic_created",
                    topic_name="prod.orders",
                    cluster_id="prod-kafka",
                    partitions=12)
    """
    return structlog.stdlib.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """현재 context에 변수 바인딩 (asyncio context 전파)

    Args:
        **kwargs: 바인딩할 컨텍스트 변수

    Example:
        # Middleware에서 trace_id 바인딩
        bind_context(trace_id=request_id, user_id=user.id)

        # 이후 모든 로그에 자동으로 trace_id, user_id 포함됨
        logger.info("operation_completed")
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """context 변수 언바인딩

    Args:
        *keys: 제거할 컨텍스트 키들
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """모든 context 변수 초기화"""
    structlog.contextvars.clear_contextvars()
