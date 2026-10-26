"""API v1 root router."""

from fastapi import APIRouter

from src.backend.api.v1.finance import router as finance_router
from src.backend.api.v1.hr import router as hr_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(finance_router)
api_v1_router.include_router(hr_router)

__all__ = ["api_v1_router", "finance_router", "hr_router"]
