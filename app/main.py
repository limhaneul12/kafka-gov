"""Kafka Governance API 메인 애플리케이션"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
        title="Kafka Governance API",
        description="Kafka 토픽과 스키마 배치 관리 및 거버넌스 API",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
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
