"""Kafka Governance API 메인 애플리케이션"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from .celery_app import celery_app
from .cluster.interface.router import router as cluster_router
from .consumer.interface.routers import (
    router as consumer_router,
    topic_router as consumer_topic_router,
)
from .consumer.interface.routers.websocket_routes import router as consumer_websocket_router
from .container import AppContainer
from .schema.interface.router import router as schema_router
from .shared.error_handlers import format_validation_error
from .shared.interface.router import router as shared_router
from .shared.logging_config import configure_structlog, get_logger
from .shared.middleware import RequestLoggingMiddleware
from .shared.settings import settings
from .topic.interface.routers.metrics_router import router as metrics_router
from .topic.interface.routers.policy_router import router as policy_router
from .topic.interface.routers.topic_router import router as topic_router

# structlog 초기화 (애플리케이션 최상단에서 1회만)
configure_structlog()

logger = get_logger(__name__)


async def _trigger_initial_metrics_sync(container: AppContainer) -> None:
    """클러스터별 초기 메트릭 스냅샷을 확보합니다."""
    try:
        list_clusters_use_case = container.cluster_container.list_kafka_clusters_use_case()
        clusters = await list_clusters_use_case.execute(active_only=True)

        metrics_repository = container.topic_container.metrics_repository()

        for cluster in clusters:
            snapshot = await metrics_repository.get_latest_snapshot(cluster.cluster_id)
            if snapshot is None:
                logger.info(
                    "trigger_initial_metrics_sync",
                    cluster_id=cluster.cluster_id,
                    cluster_name=cluster.name,
                )
                celery_app.send_task(
                    "app.tasks.metrics_tasks.manual_sync_metrics", args=[cluster.cluster_id]
                )
    except Exception as e:
        logger.error(
            "initial_metrics_sync_failed",
            error_type=e.__class__.__name__,
            error_message=str(e),
            exc_info=True,
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 생명주기 관리"""
    container = app.state.container  # type: ignore[attr-defined]

    try:
        container.init_resources()
        await _trigger_initial_metrics_sync(container)

        logger.info("app_startup_completed", environment=settings.environment)
        yield
    except Exception as e:
        logger.error(
            "app_startup_failed",
            error_type=e.__class__.__name__,
            error_message=str(e),
            exc_info=True,
        )
        raise
    finally:
        # Resource 종료
        container.shutdown_resources()
        logger.info("app_shutdown_completed")


def create_app() -> FastAPI:
    # 환경별 API 문서 설정 (프로덕션에서는 비활성화)
    docs_url = None if settings.is_production else "/swagger"
    redoc_url = None if settings.is_production else "/redoc"
    openapi_url = None if settings.is_production else "/openapi.json"

    app = FastAPI(
        default_response_class=ORJSONResponse,
        title="Kafka Governance API",
        description="Kafka Topic / Schema Registry 관리용 API",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "defaultModelRendering": "example",
            "displayRequestDuration": True,
            "docExpansion": "none",
            "syntaxHighlight.theme": "obsidian",
            "persistAuthorization": True,
        },
    )

    # CORS - 환경별 설정
    cors_origins = settings.parsed_cors_origins
    logger.info(
        "cors_configured",
        origins=cors_origins,
        environment=settings.environment,
    )

    # Request Logging Middleware (trace_id 전파)
    app.add_middleware(RequestLoggingMiddleware)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ✅ 컨테이너 인스턴스 생성 & 보관
    container = AppContainer()
    app.state.container = container

    # (선택) 하위 컨테이너 인스턴스를 접근 용도로 보관하고 싶다면 호출해서 저장
    app.state.infrastructure_container = container.infrastructure_container()
    app.state.cluster_container = container.cluster_container()
    app.state.topic_container = container.topic_container()
    app.state.consumer_container = container.consumer_container()
    app.state.schema_container = container.schema_container()

    # ✅ (중요) 와이어링 - wiring_config가 있으면 생략 가능하지만,
    # 명시적으로 호출하면 import 타이밍 이슈를 줄일 수 있음
    container.wire(
        packages=[
            # 라우터/핸들러 패키지들
            "app.cluster.interface",
            "app.topic.interface",
            "app.consumer.interface",
            "app.schema.interface",
            "app.shared.interface",
        ]
    )

    # 라우터 등록
    app.include_router(shared_router, prefix="/api")
    app.include_router(cluster_router, prefix="/api")  # Cluster API
    app.include_router(topic_router, prefix="/api")
    app.include_router(metrics_router, prefix="/api")
    app.include_router(policy_router, prefix="/api")  # Policy API
    app.include_router(schema_router, prefix="/api")
    # Consumer REST routes (already prefixed with /api)
    app.include_router(consumer_router)
    app.include_router(consumer_topic_router)
    # Consumer WebSocket routes
    app.include_router(consumer_websocket_router)

    @app.get("/api")
    @app.get("/api/")
    async def api_info() -> dict[str, str]:
        return {"message": "Kafka Governance API", "version": "1.0.0"}

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Pydantic validation 에러를 사용자 친화적인 메시지로 변환"""
        # 구조화된 로깅 (trace_id는 middleware에서 자동 추가됨)
        logger.error(
            "validation_error",
            error_count=len(exc.errors()),
            errors=exc.errors(),
        )

        # 사용자 친화적인 메시지로 변환
        friendly_message = format_validation_error(exc)  # type: ignore[arg-type]

        return ORJSONResponse(
            status_code=422,
            content={"detail": friendly_message},
        )

    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exc: Exception):
        return ORJSONResponse(status_code=404, content={"message": "Not Found"})

    return app


app = create_app()
