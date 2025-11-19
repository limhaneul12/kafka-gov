"""Cluster Routers - 모듈화된 API 라우터"""

from fastapi import APIRouter

from .broker import router as broker_router
from .registry import router as registry_router

# 메인 라우터 생성
router = APIRouter(prefix="/v1/clusters", tags=["clusters"])

# 각 하위 라우터 포함 (Kafka Connect 라우터 제거됨)
router.include_router(broker_router)
router.include_router(registry_router)

__all__ = ["router"]
