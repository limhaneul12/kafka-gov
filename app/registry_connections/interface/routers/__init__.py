"""Schema Registry connection routers."""

from fastapi import APIRouter

from .registry import router as registry_router

router = APIRouter(prefix="/v1", tags=["schema-registries"])
router.include_router(registry_router)

__all__ = ["router"]
