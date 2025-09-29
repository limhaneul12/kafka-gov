"""Kafka Governance API 메인 애플리케이션"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from .policy import policy_router, policy_use_case_factory
from .schema.interface.router import router as schema_router
from .topic.interface.router import router as topic_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 생명주기 관리"""
    # 시작 시 초기화
    try:
        # Policy 기본 정책 초기화
        await policy_use_case_factory.initialize_default_policies()
        print("✅ Policy 기본 정책이 초기화되었습니다.")
    except Exception as e:
        print(f"⚠️ Policy 초기화 중 오류 발생: {e}")

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

    # 라우터 등록
    app.include_router(topic_router, prefix="/api")
    app.include_router(schema_router, prefix="/api")
    app.include_router(policy_router, prefix="/api")

    @app.get("/")
    async def root() -> dict[str, str]:
        """루트 엔드포인트"""
        return {"message": "Kafka Governance API", "version": "1.0.0"}

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """헬스 체크 엔드포인트"""
        return {"status": "healthy"}

    return app


# 애플리케이션 인스턴스 생성
app = create_app()
