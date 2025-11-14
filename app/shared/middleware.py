"""FastAPI Middleware - 구조화 로깅 지원

trace_id 전파 및 요청/응답 로깅
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_config import bind_context, clear_context, get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 및 trace_id 전파 Middleware

    모든 요청에 trace_id를 할당하고 context에 바인딩하여
    해당 요청의 모든 로그에 자동으로 trace_id가 포함되도록 함
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # trace_id 생성 또는 헤더에서 추출
        trace_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # trace_id를 context에 바인딩 (모든 로그에 자동 포함)
        bind_context(
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            # 응답 헤더에 trace_id 추가
            response.headers["X-Request-ID"] = trace_id

            # 요청 완료 로깅
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            return response

        except Exception as exc:
            # 예외 발생 시 로깅
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                "request_failed",
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )

            raise

        finally:
            # context 정리 (메모리 누수 방지)
            clear_context()
