"""Nerolac Operations Dashboard - Production FastAPI Application.

Architecture:
- Async ASGI application (FastAPI + Uvicorn)
- Redis 7 Multi-Instance Caching (DB 0: Query Cache, DB 1: Celery Broker, DB 2: Rate Limiter)
- Security: HashiCorp Vault Secrets, Bangladesh Data Sovereignty, PII Redaction
- Module 1: Finance Control Center API
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api.v1 import api_v1_router
from src.backend.config.redis_config import get_redis_routing_manager
from src.backend.database.session_router import get_routing_manager
from src.backend.middleware.pii_masker import PIIMaskingMiddleware
from src.backend.middleware.rate_limiter import RateLimiterMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nerolac.backend")


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Manage application startup and clean teardown."""
    logger.info("Initializing Nerolac Operations Dashboard Backend...")
    # Verify Redis connectivity
    redis_mgr = get_redis_routing_manager()
    redis_health = await redis_mgr.audit_health()
    logger.info("Redis Health Status: %s", redis_health.get("status"))

    yield

    logger.info("Shutting down database and cache connections...")
    await get_routing_manager().dispose()
    await redis_mgr.close()


def create_app() -> FastAPI:
    """Construct and configure the production FastAPI application."""
    app = FastAPI(
        title="Nerolac Operations Dashboard API",
        description="Enterprise Operations & Finance Control Center API for Nerolac Bangladesh",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 1. CORS Middleware (Next.js 15 Frontend integration)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Token Bucket Rate Limiter Middleware (100 req/min enforced in Redis DB 2)
    app.add_middleware(
        RateLimiterMiddleware,
        rate_per_minute=100,
        burst_capacity=100,
        exempt_paths=["/health", "/docs", "/openapi.json", "/redoc", "/"],
    )

    # 3. PII Masking Middleware (Bangladeshi NID, Phone, Bank Account Redaction)
    app.add_middleware(PIIMaskingMiddleware)

    # 4. Include API Routers
    app.include_router(api_v1_router, prefix="/api")

    @app.get("/health", tags=["System Health"])
    async def health_check() -> dict[str, Any]:
        """System health and infrastructure audit."""
        db_audit = await get_routing_manager().audit_status()
        redis_audit = await get_redis_routing_manager().audit_health()
        return {
            "status": "HEALTHY"
            if db_audit["status"] == "HEALTHY" and redis_audit["status"] == "HEALTHY"
            else "DEGRADED",
            "database": db_audit,
            "redis": redis_audit,
        }

    @app.get("/", tags=["Root"])
    async def root_info() -> dict[str, str]:
        """API Service Information."""
        return {
            "service": "Nerolac Operations Dashboard API",
            "environment": "production",
            "documentation": "/docs",
        }

    return app


app = create_app()
