"""FastAPI Token Bucket Rate Limiter Middleware.

Enforces:
1. 100 requests per minute per user using an atomic Token Bucket algorithm.
2. State stored exclusively in Redis DB 2 (Token Bucket Rate Limiting Storage).
3. Rejection with HTTP 429 Too Many Requests and `Retry-After` headers on exhaustion.
4. Seamless identification of authenticated users (via X-User-ID or Auth token)
   with fallback to client IP.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Callable, cast

import redis.asyncio as aioredis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.backend.config.redis_config import get_rate_limiter_client

logger = logging.getLogger("nerolac.middleware.rate_limiter")

# Default SLA: 100 requests per minute
DEFAULT_RATE_LIMIT_PER_MINUTE = 100
DEFAULT_BURST_CAPACITY = 100
DEFAULT_KEY_TTL_SECONDS = 120

# Atomic Token Bucket Lua Script executed on Redis DB 2
TOKEN_BUCKET_LUA_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local data = redis.call("HMGET", key, "tokens", "last_updated")
local tokens = tonumber(data[1])
local last_updated = tonumber(data[2])

if not tokens or not last_updated then
    tokens = capacity
    last_updated = now
else
    local delta = math.max(0, now - last_updated)
    tokens = math.min(capacity, tokens + (delta * refill_rate))
    last_updated = now
end

local allowed = 0
local remaining = tokens
local retry_after = 0

if tokens >= requested then
    allowed = 1
    tokens = tokens - requested
    remaining = tokens
    redis.call("HMSET", key, "tokens", tokens, "last_updated", now)
    redis.call("EXPIRE", key, ttl)
else
    allowed = 0
    remaining = tokens
    local missing = requested - tokens
    retry_after = math.ceil(missing / refill_rate)
end

return {allowed, tostring(math.floor(remaining)), tostring(retry_after)}
"""


@dataclass
class RateLimitDecision:
    """Outcome of a token bucket rate limit evaluation."""

    allowed: bool
    remaining_tokens: int
    retry_after_seconds: int
    limit_per_minute: int
    client_id: str


class TokenBucketRateLimiter:
    """Core Token Bucket rate limiter communicating directly with Redis DB 2."""

    def __init__(
        self,
        rate_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE,
        burst_capacity: int = DEFAULT_BURST_CAPACITY,
        client: aioredis.Redis | None = None,
        key_ttl_seconds: int = DEFAULT_KEY_TTL_SECONDS,
    ) -> None:
        self.rate_per_minute = rate_per_minute
        self.burst_capacity = burst_capacity
        self.refill_rate_per_second = rate_per_minute / 60.0
        self.key_ttl_seconds = key_ttl_seconds
        self._custom_client = client
        self._lua_sha: str | None = None

    @property
    def client(self) -> aioredis.Redis:
        """Lazily retrieve the DB 2 rate limiter Redis client."""
        if self._custom_client is not None:
            return self._custom_client
        return get_rate_limiter_client()

    async def check_rate_limit(
        self,
        client_id: str,
        cost: int = 1,
    ) -> RateLimitDecision:
        """Evaluate if the client has sufficient tokens available to proceed."""
        key = f"ratelimit:{client_id.strip()}"
        now = time.time()

        try:
            # Execute atomic token bucket Lua script on Redis DB 2
            res: list[Any] = await cast(
                Any,
                self.client.eval(
                    TOKEN_BUCKET_LUA_SCRIPT,
                    1,
                    key,
                    str(self.burst_capacity),
                    str(self.refill_rate_per_second),
                    str(now),
                    str(cost),
                    str(self.key_ttl_seconds),
                ),
            )

            allowed = bool(int(res[0]) == 1)
            remaining = int(res[1])
            retry_after = int(res[2])

            return RateLimitDecision(
                allowed=allowed,
                remaining_tokens=max(0, remaining),
                retry_after_seconds=max(1, retry_after) if not allowed else 0,
                limit_per_minute=self.rate_per_minute,
                client_id=client_id,
            )

        except Exception as exc:
            logger.error("Rate limiter evaluation failed for client '%s': %s", client_id, exc)
            # Fail-open under Redis partition to avoid taking down critical dashboard operations
            return RateLimitDecision(
                allowed=True,
                remaining_tokens=self.rate_per_minute,
                retry_after_seconds=0,
                limit_per_minute=self.rate_per_minute,
                client_id=client_id,
            )

    async def reset(self, client_id: str) -> None:
        """Reset or clear rate limiting tokens for a specific client."""
        key = f"ratelimit:{client_id.strip()}"
        await self.client.delete(key)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """FastAPI / Starlette middleware enforcing 100 req/min token bucket rate limiting."""

    def __init__(
        self,
        app: Any,
        rate_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE,
        burst_capacity: int = DEFAULT_BURST_CAPACITY,
        exempt_paths: Sequence[str] | None = None,
        client: aioredis.Redis | None = None,
        key_identifier_fn: Callable[[Request], str] | None = None,
    ) -> None:
        super().__init__(app)
        self.limiter = TokenBucketRateLimiter(
            rate_per_minute=rate_per_minute,
            burst_capacity=burst_capacity,
            client=client,
        )
        self.exempt_paths = set(exempt_paths or ["/health", "/docs", "/openapi.json", "/redoc"])
        self.key_identifier_fn = key_identifier_fn or self._default_identifier

    @staticmethod
    def _default_identifier(request: Request) -> str:
        """Extract user identification from request headers, state, or client IP."""
        # 1. Authenticated user ID header
        user_id = request.headers.get("X-User-ID") or request.headers.get("x-user-id")
        if user_id:
            return f"user:{user_id.strip()}"

        # 2. Authorization Bearer token hash
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if len(token) > 16:
                return f"token:{token[-16:]}"

        # 3. Client IP address (with X-Forwarded-For support)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
            return f"ip:{ip}"

        client_host = request.client.host if request.client else "127.0.0.1"
        return f"ip:{client_host}"

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Intercept request, evaluate rate limit token bucket, and enforce HTTP 429."""
        # Skip exempt endpoints (health checks, API docs)
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        client_id = self.key_identifier_fn(request)
        decision = await self.limiter.check_rate_limit(client_id)

        if not decision.allowed:
            logger.warning(
                "Rate limit exceeded for client '%s'. Maximum %d req/min allowed.",
                client_id,
                decision.limit_per_minute,
            )
            content = {
                "error": "Too Many Requests",
                "detail": (
                    f"Rate limit exceeded. Maximum {decision.limit_per_minute} "
                    "requests per minute permitted."
                ),
                "retry_after_seconds": decision.retry_after_seconds,
            }
            headers = {
                "Retry-After": str(decision.retry_after_seconds),
                "X-RateLimit-Limit": str(decision.limit_per_minute),
                "X-RateLimit-Remaining": "0",
            }
            return JSONResponse(status_code=429, content=content, headers=headers)

        response = await call_next(request)

        # Inject rate limit telemetry headers
        response.headers["X-RateLimit-Limit"] = str(decision.limit_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining_tokens)
        response.headers["X-RateLimit-Reset"] = "60"

        return response
