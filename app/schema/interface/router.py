from fastapi import APIRouter

from .routers.batch_router import router as batch_router
from .routers.governance_router import router as governance_router
from .routers.management_router import router as management_router

router = APIRouter()

router.include_router(batch_router)
router.include_router(governance_router)
router.include_router(management_router)
