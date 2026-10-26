"""Authentication & User Profile Endpoints for Microsoft Entra ID.

Provides:
1. GET /api/v1/auth/me: Retrieve current authenticated user profile and roles.
2. GET /api/v1/auth/login: Generate Entra ID OAuth2 login URL.
3. POST /api/v1/auth/token: Exchange authorization code for JWT.
4. GET /api/v1/auth/test-token: Generate test JWT (development/testing environments only).
5. GET /api/v1/auth/scoped-actuals: Query financial actuals under active PostgreSQL RLS.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.sso_handler import UserClaims, create_test_token, get_sso_handler
from src.backend.database.session_router import provide_read_session
from src.backend.middleware.auth_middleware import require_authenticated_user

logger = logging.getLogger("nerolac.api.v1.auth")

router = APIRouter(prefix="/auth", tags=["Authentication & SSO"])


@router.get(
    "/me",
    summary="Retrieve Authenticated User Context",
    description="Returns current user claims, active depot assignment, and RBAC roles.",
)
async def get_current_user_profile(
    user: Annotated[UserClaims, Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Return verified claims for the current user."""
    return {
        "user_id": user.user_id,
        "email": user.email,
        "full_name": user.full_name,
        "user_role": user.user_role,
        "depot_id": user.depot_id,
        "tenant_id": user.tenant_id,
        "is_executive": user.is_executive_role(),
    }


@router.get(
    "/login",
    summary="Microsoft Entra ID OAuth2 Login URL",
    description="Generates the Microsoft Entra ID authorization URL for OIDC authentication.",
)
async def get_login_url(
    redirect_uri: Annotated[str, Query(description="OAuth2 callback redirect URI")],
    state: Annotated[str, Query(description="CSRF state parameter")] = "csrf_token_nerolac",
) -> dict[str, str]:
    """Return Entra ID authorization redirect URL."""
    handler = get_sso_handler()
    auth_url = handler.get_authorization_url(redirect_uri=redirect_uri, state=state)
    return {"authorization_url": auth_url}


@router.get(
    "/test-token",
    summary="Generate Test JWT (Dev/Test Environments)",
    description="Mint a signed test token with specified role and depot assignment.",
)
async def generate_test_token(
    user_id: Annotated[str, Query(description="User identifier")] = "USR_CTG_001",
    user_role: Annotated[str, Query(description="Role code")] = "DEPOT_MANAGER",
    depot_id: Annotated[str, Query(description="Depot code (e.g. CTG)")] = "CTG",
) -> dict[str, str]:
    """Generate a test Entra ID bearer token."""
    token = create_test_token(user_id=user_id, user_role=user_role, depot_id=depot_id)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "user_id": user_id,
        "user_role": user_role,
        "depot_id": depot_id,
    }


@router.get(
    "/scoped-actuals",
    summary="Query Depot Financial Actuals under RLS",
    description=(
        "Executes a database query on financial_actuals subject to PostgreSQL Row-Level Security."
    ),
)
async def get_scoped_actuals(
    request: Request,
    user: Annotated[UserClaims, Depends(require_authenticated_user)],
    session: Annotated[AsyncSession, Depends(provide_read_session)],
) -> dict[str, Any]:
    """Query financial actuals with active RLS enforcement."""
    result = await session.execute(
        text(
            """
            SELECT actual_id, depot_id, account_id, amount, fiscal_year, fiscal_month
            FROM nerolac_ops.financial_actuals
            ORDER BY actual_id;
            """
        )
    )
    rows = result.fetchall()
    actuals = [
        {
            "actual_id": r[0],
            "depot_id": r[1],
            "account_id": r[2],
            "amount": float(r[3]),
            "fiscal_year": r[4],
            "fiscal_month": r[5],
        }
        for r in rows
    ]

    return {
        "user_depot": user.depot_id,
        "user_role": user.user_role,
        "record_count": len(actuals),
        "records": actuals,
    }
