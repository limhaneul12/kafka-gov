"""Kafka Governance API 메인 애플리케이션"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .analysis.interface.router import router as analysis_router
from .cluster.interface.router import router as cluster_router
from .connect.interface.router import router as connect_router
from .container import AppContainer, register_event_handlers
from .schema.interface.router import router as schema_router
from .shared.interface.router import router as shared_router
from .topic.interface.router import router as topic_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 생명주기 관리"""
    container = app.state.container  # type: ignore[attr-defined]

    try:
        container.init_resources()
        register_event_handlers(container)

        logger.info("컨테이너 초기화 및 이벤트 핸들러 등록 완료")
        yield
    except Exception:
        logger.exception("초기화 중 오류 발생")
        raise
    finally:
        # Resource 종료
        container.shutdown_resources()
        logger.info("리소스 정리 완료")


def create_app() -> FastAPI:
    app = FastAPI(
        default_response_class=ORJSONResponse,
        title="Kafka Governance API",
        description="Kafka Topic / Schema Registry 관리용 API",
        version="0.1.0",
        docs_url="/swagger",
        redoc_url="/redoc",
        lifespan=lifespan,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "defaultModelRendering": "example",  # ← 유효한 값으로 교체
            "displayRequestDuration": True,
            "docExpansion": "none",
            "syntaxHighlight.theme": "obsidian",
            "persistAuthorization": True,
        },
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=["*"],  # 운영에선 화이트리스트 권장
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 정적 파일
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # ✅ 컨테이너 인스턴스 생성 & 보관
    container = AppContainer()
    app.state.container = container

    # (선택) 하위 컨테이너 인스턴스를 접근 용도로 보관하고 싶다면 호출해서 저장
    app.state.infrastructure_container = container.infrastructure_container()
    app.state.cluster_container = container.cluster_container()
    app.state.topic_container = container.topic_container()
    app.state.schema_container = container.schema_container()
    app.state.analysis_container = container.analysis_container()
    app.state.connect_container = container.connect_container()

    # ✅ (중요) 와이어링 - wiring_config가 있으면 생략 가능하지만,
    # 명시적으로 호출하면 import 타이밍 이슈를 줄일 수 있음
    container.wire(
        packages=[
            # 라우터/핸들러 패키지들
            "app.cluster.interface",  # Cluster API (ConnectionManager 제공)
            "app.connect.interface",  # Connect API
            "app.topic.interface",
            "app.schema.interface",
            "app.analysis.interface",
            "app.shared.interface",
            "app.analysis.application",
        ]
    )

    # 라우터 등록
    app.include_router(shared_router, prefix="/api")
    app.include_router(cluster_router, prefix="/api")  # Cluster API
    app.include_router(connect_router, prefix="/api")  # Connect API
    app.include_router(topic_router, prefix="/api")
    app.include_router(schema_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")

    @app.get("/")
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/static/index.html")

    @app.get("/api")
    async def api_info() -> dict[str, str]:
        return {"message": "Kafka Governance API", "version": "1.0.0"}

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Pydantic validation 에러를 상세히 로깅"""
        logger.error(f"Validation error on {request.method} {request.url.path}")
        logger.error(f"Request body: {await request.body()}")
        logger.error(f"Validation errors: {exc.errors()}")

        return ORJSONResponse(
            status_code=422,
            content={
                "detail": exc.errors(),
                "body": exc.body if hasattr(exc, "body") else None,
            },
        )

    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exc: Exception):
        return ORJSONResponse(status_code=404, content={"message": "Not Found"})

    return app


app = create_app()
