"""Kafka Connect Routers - 모듈화된 라우터"""

from __future__ import annotations

from fastapi import APIRouter

from .connector_control_router import router as connector_control_router
from .connector_crud_router import router as connector_crud_router
from .metadata_router import router as metadata_router
from .plugins_router import router as plugins_router
from .tasks_router import router as tasks_router
from .topics_router import router as topics_router

# 통합 라우터
router = APIRouter(prefix="/v1/connect", tags=["Kafka Connect"])

# 각 서브 라우터 포함
router.include_router(connector_crud_router)
router.include_router(connector_control_router)
router.include_router(tasks_router)
router.include_router(topics_router)
router.include_router(plugins_router)
router.include_router(metadata_router)

__all__ = ["router"]
