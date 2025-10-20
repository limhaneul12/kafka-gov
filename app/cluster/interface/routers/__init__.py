"""Cluster Routers - 모듈화된 API 라우터"""

from fastapi import APIRouter

from .broker import router as broker_router
from .connect import router as connect_router
from .registry import router as registry_router
from .storage import router as storage_router

# 메인 라우터 생성
router = APIRouter(prefix="/v1/clusters", tags=["clusters"])

# 각 하위 라우터 포함
router.include_router(broker_router)
router.include_router(registry_router)
router.include_router(storage_router)
router.include_router(connect_router)

__all__ = ["router"]
