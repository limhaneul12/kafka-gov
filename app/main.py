"""Kafka Governance API 메인 애플리케이션"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .analysis.interface.router import router as analysis_router
from .policy import policy_router, policy_use_case_factory
from .schema.interface.router import router as schema_router
from .shared.database import get_db_session
from .topic.interface.router import router as topic_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 생명주기 관리"""
    # 시작 시 초기화
    try:
        # Policy 기본 정책 초기화
        await policy_use_case_factory.initialize_default_policies()
        logger.info("Policy 기본 정책이 초기화되었습니다.")

        # Analysis 이벤트 핸들러 등록
        from .analysis.container import register_event_handlers

        async for session in get_db_session():
            register_event_handlers(session)
            logger.info("Analysis 이벤트 핸들러가 등록되었습니다.")
            break

    except Exception as e:
        logger.error(f"초기화 중 오류 발생: {e}", exc_info=True)

    yield

    # 종료 시 정리 작업 (필요시)


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 생성"""
    app = FastAPI(
        default_response_class=ORJSONResponse,
        title="Kafka Governance API",
        description="Kafka Topic / Schema Registry 관리용 API",
        version="0.1.0",
        docs_url="/swagger",  # Swagger 경로 변경 (기본은 /docs)
        redoc_url="/redoc",
        lifespan=lifespan,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,  # 모델 섹션 기본 접기
            "defaultModelRendering": "example",  # Example 뷰 기본
            "displayRequestDuration": True,  # 요청-응답 시간 표시
            "docExpansion": "none",  # 전체 접기
            "syntaxHighlight.theme": "obsidian",  # 다크 테마
            "persistAuthorization": True,  # Authorize 토큰 유지
        },
    )
    # CORS 설정
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=["*"],  # 운영에서는 구체적인 도메인 지정
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 정적 파일 서빙
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # 라우터 등록
    app.include_router(topic_router, prefix="/api")
    app.include_router(schema_router, prefix="/api")
    app.include_router(policy_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")  # 🆕 Analysis 라우터

    @app.get("/")
    async def root() -> RedirectResponse:
        """루트 엔드포인트 - 프론트엔드로 리다이렉트"""
        return RedirectResponse(url="/static/index.html")

    @app.get("/api")
    async def api_info() -> dict[str, str]:
        """API 정보 엔드포인트"""
        return {"message": "Kafka Governance API", "version": "1.0.0"}

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """헬스 체크 엔드포인트"""
        return {"status": "healthy"}

    return app


# 애플리케이션 인스턴스 생성
app = create_app()
