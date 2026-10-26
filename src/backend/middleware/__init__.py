"""Middleware components for security, PII redaction, and audit logging."""

from src.backend.middleware.auth_middleware import (
    AuthMiddleware,
    current_depot_id,
    current_user_claims,
    current_user_id,
    current_user_role,
    get_current_depot_id,
    get_current_user_claims,
    get_current_user_id,
    get_current_user_role,
    require_authenticated_user,
    require_roles,
)
from src.backend.middleware.pii_masker import (
    PIIMaskingMiddleware,
    PIIRedactingFormatter,
    mask_dict,
    mask_llm_context,
    mask_pii,
)
from src.backend.middleware.rate_limiter import (
    RateLimitDecision,
    RateLimiterMiddleware,
    TokenBucketRateLimiter,
)

__all__ = [
    "AuthMiddleware",
    "current_user_id",
    "current_user_role",
    "current_depot_id",
    "current_user_claims",
    "get_current_user_id",
    "get_current_user_role",
    "get_current_depot_id",
    "get_current_user_claims",
    "require_authenticated_user",
    "require_roles",
    "PIIMaskingMiddleware",
    "PIIRedactingFormatter",
    "mask_pii",
    "mask_dict",
    "mask_llm_context",
    "RateLimiterMiddleware",
    "TokenBucketRateLimiter",
    "RateLimitDecision",
]
