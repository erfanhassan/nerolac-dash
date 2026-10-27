"""JWT Validation & Context Middleware for Microsoft Entra ID (Azure AD).

Extracts claims (user_id, user_role, depot_id) on incoming API requests and sets
asynchronous context variables for downstream PostgreSQL Row-Level Security (RLS) enforcement.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.backend.auth.sso_handler import (
    AuthenticationError,
    TokenExpiredError,
    UserClaims,
    get_sso_handler,
)

logger = logging.getLogger("nerolac.middleware.auth")

# Async Context Variables for RLS & User Context tracking across concurrent requests
current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)
current_user_role: ContextVar[str | None] = ContextVar("current_user_role", default=None)
current_depot_id: ContextVar[str | None] = ContextVar("current_depot_id", default=None)
current_user_claims: ContextVar[UserClaims | None] = ContextVar("current_user_claims", default=None)


def get_current_user_id() -> str | None:
    """Return the active user_id for the current asynchronous request context."""
    return current_user_id.get()


def get_current_user_role() -> str | None:
    """Return the active user_role for the current asynchronous request context."""
    return current_user_role.get()


def get_current_depot_id() -> str | None:
    """Return the active depot_id for the current asynchronous request context."""
    return current_depot_id.get()


def get_current_user_claims() -> UserClaims | None:
    """Return the active UserClaims object for the current asynchronous request context."""
    return current_user_claims.get()


class AuthMiddleware(BaseHTTPMiddleware):
    """ASGI Middleware extracting Microsoft Entra ID JWT claims on every API request.

    Binds user_id, user_role, and depot_id to:
    1. request.state (FastAPI request scope)
    2. Python contextvars (current_user_id, current_user_role, current_depot_id)
    """

    def __init__(
        self,
        app: ASGIApp,
        exempt_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.sso_handler = get_sso_handler()
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/",
            "/api/v1/auth/login",
            "/api/v1/auth/callback",
        ]

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Inspect Authorization header, validate JWT, and propagate claims."""
        auth_header = request.headers.get("Authorization")
        x_depot = request.headers.get("X-Depot-Id")
        x_role = request.headers.get("X-User-Role")

        token_uid = None
        token_role = None
        token_depot = None
        token_claims = None

        try:
            if auth_header:
                if not auth_header.startswith("Bearer "):
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "detail": (
                                "Invalid Authorization header format. Expected 'Bearer <token>'."
                            )
                        },
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                raw_token = auth_header[7:].strip()
                try:
                    claims: UserClaims = self.sso_handler.decode_and_validate_token(raw_token)
                except TokenExpiredError as exc:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Authentication token has expired.", "error": str(exc)},
                        headers={
                            "WWW-Authenticate": (
                                'Bearer error="invalid_token", error_description="token_expired"'
                            )
                        },
                    )
                except AuthenticationError as exc:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "detail": "Authentication failed: Invalid token.",
                            "error": str(exc),
                        },
                        headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
                    )

                # Store claims in request.state
                request.state.user = claims
                request.state.user_id = claims.user_id
                request.state.user_role = claims.user_role
                request.state.depot_id = claims.depot_id

                # Set async ContextVars
                token_uid = current_user_id.set(claims.user_id)
                token_role = current_user_role.set(claims.user_role)
                token_depot = current_depot_id.set(claims.depot_id)
                token_claims = current_user_claims.set(claims)

            elif x_depot and x_role:
                # Support direct test session headers when token not explicitly passed
                req_uid = request.headers.get("X-User-Id", "TEST_SYS_USER")
                request.state.user = None
                request.state.user_id = req_uid
                request.state.user_role = x_role
                request.state.depot_id = x_depot

                token_uid = current_user_id.set(req_uid)
                token_role = current_user_role.set(x_role)
                token_depot = current_depot_id.set(x_depot)

            else:
                # No token provided
                request.state.user = None
                request.state.user_id = None
                request.state.user_role = None
                request.state.depot_id = None

            # Process downstream request
            response = await call_next(request)
            return response

        finally:
            # Clean up context variables to prevent leakage across pooled event-loop coroutines
            if token_uid is not None:
                current_user_id.reset(token_uid)
            if token_role is not None:
                current_user_role.reset(token_role)
            if token_depot is not None:
                current_depot_id.reset(token_depot)
            if token_claims is not None:
                current_user_claims.reset(token_claims)


def require_authenticated_user(request: Request) -> UserClaims:
    """FastAPI route dependency ensuring request is authenticated via Entra ID."""
    user = getattr(request.state, "user", None)
    if not isinstance(user, UserClaims):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*allowed_roles: str) -> Any:
    """FastAPI route dependency enforcing role-based access control (RBAC)."""

    def role_checker(request: Request) -> UserClaims:
        user = require_authenticated_user(request)
        if user.user_role not in allowed_roles:
            detail_msg = (
                f"Access denied for role '{user.user_role}'. Required roles: {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail_msg,
            )
        return user

    return role_checker
