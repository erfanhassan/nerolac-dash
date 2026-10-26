"""API v1 root router."""

from fastapi import APIRouter

from src.backend.api.v1.auth import router as auth_router
from src.backend.api.v1.finance import router as finance_router
from src.backend.api.v1.hr import router as hr_router
from src.backend.api.v1.reports import router as reports_router
from src.backend.api.v1.supply_chain import router as supply_chain_router
from src.backend.api.v1.whatsapp import whatsapp_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(finance_router)
api_v1_router.include_router(hr_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(supply_chain_router)
api_v1_router.include_router(whatsapp_router)

__all__ = [
    "api_v1_router",
    "auth_router",
    "finance_router",
    "hr_router",
    "reports_router",
    "supply_chain_router",
    "whatsapp_router",
]
