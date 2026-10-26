"""Multi-Instance Redis 7 Database Routing & Infrastructure Configuration.

Architectural Specification:
- DB 0: Sub-50ms Analytical Query Cache (P&L tree grids, SCM trends, executive KPIs).
- DB 1: Celery Async Message Broker & Task Result Backend.
- DB 2: Token Bucket Rate Limiting Storage (Sliding window token state & quotas).

Security & Compliance:
- Bangladesh Data Sovereignty: Strict validation ensuring Redis residency.
- Enterprise Vault Integration: Runtime credential retrieval via VaultClient
  (Zero hardcoded secrets).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, cast
from urllib.parse import quote_plus

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

from src.backend.config.settings import is_sovereign_host
from src.backend.config.vault import get_vault_client

logger = logging.getLogger("nerolac.infrastructure.redis")

# Dedicated Redis Database Allocations
DB_QUERY_CACHE = 0  # DB 0: Sub-50ms Query & Dashboard Cache
DB_CELERY_BROKER = 1  # DB 1: Celery Async Message Broker
DB_RATE_LIMITER = 2  # DB 2: Token Bucket Rate Limiter Storage

DEFAULT_MAX_CONNECTIONS = 50


class RedisRoutingManager:
    """Enterprise connection router managing multi-database Redis 7 pools."""

    _instance: RedisRoutingManager | None = None

    def __init__(self, max_connections: int = DEFAULT_MAX_CONNECTIONS) -> None:
        self.max_connections = max_connections
        self._pools: dict[int, ConnectionPool] = {}
        self._clients: dict[int, aioredis.Redis] = {}
        self._active_loop: Any = None
        self._init_credentials()

    def _ensure_event_loop(self) -> None:
        """Ensure connection pools and clients attach to the current running event loop."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._active_loop is not current_loop:
            self._pools.clear()
            self._clients.clear()
            self._active_loop = current_loop

    def _init_credentials(self) -> None:
        """Retrieve connection credentials securely from Vault."""
        vault = get_vault_client()
        creds = vault.get_redis_credentials()

        self.host = str(os.getenv("REDIS_HOST", creds.get("host", "localhost"))).strip()
        self.port = int(os.getenv("REDIS_PORT", str(creds.get("port", 6379))))
        self.password = os.getenv("REDIS_PASSWORD", creds.get("password"))
        if self.password == "None" or not self.password:
            self.password = None

        # Enforce Bangladesh Data Sovereignty
        if not is_sovereign_host(self.host):
            raise ValueError(
                f"Bangladesh Data Sovereignty Violation: "
                f"Redis host '{self.host}' is outside sovereign bounds."
            )

    def get_connection_url(self, db_index: int) -> str:
        """Construct Redis connection URL for a specific database index."""
        if self.password:
            encoded_pw = quote_plus(self.password)
            return f"redis://:{encoded_pw}@{self.host}:{self.port}/{db_index}"
        return f"redis://{self.host}:{self.port}/{db_index}"

    def get_pool(self, db_index: int) -> ConnectionPool:
        """Retrieve or create an async ConnectionPool for the target DB index."""
        self._ensure_event_loop()
        if db_index not in self._pools:
            url = self.get_connection_url(db_index)
            self._pools[db_index] = ConnectionPool.from_url(
                url,
                max_connections=self.max_connections,
                decode_responses=True,
            )
        return self._pools[db_index]

    def get_client(self, db_index: int) -> aioredis.Redis:
        """Retrieve or instantiate an async Redis client for the target DB index."""
        self._ensure_event_loop()
        if db_index not in self._clients:
            pool = self.get_pool(db_index)
            self._clients[db_index] = aioredis.Redis(connection_pool=pool)
        return self._clients[db_index]

    async def audit_health(self) -> dict[str, Any]:
        """Verify connectivity and ping response across DB 0, DB 1, and DB 2."""
        results: dict[str, Any] = {
            "status": "HEALTHY",
            "host": self.host,
            "port": self.port,
            "databases": {},
        }
        db_descriptions = {
            DB_QUERY_CACHE: "DB 0: Sub-50ms Query Cache",
            DB_CELERY_BROKER: "DB 1: Celery Async Message Broker",
            DB_RATE_LIMITER: "DB 2: Token Bucket Rate Limiting Storage",
        }

        for db_idx, desc in db_descriptions.items():
            client = self.get_client(db_idx)
            try:
                pong = await cast(Any, client.ping())
                results["databases"][f"db_{db_idx}"] = {
                    "index": db_idx,
                    "description": desc,
                    "connected": pong is True or pong == "PONG",
                    "ping": pong,
                }
            except Exception as exc:
                results["status"] = "DEGRADED"
                results["databases"][f"db_{db_idx}"] = {
                    "index": db_idx,
                    "description": desc,
                    "connected": False,
                    "error": str(exc),
                }

        return results

    async def close(self) -> None:
        """Close all active clients and disconnect connection pools cleanly."""
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()

        for pool in self._pools.values():
            await pool.disconnect()
        self._pools.clear()


# Global Singleton Accessor
_router_instance: RedisRoutingManager | None = None


def get_redis_router() -> RedisRoutingManager:
    """Return the global RedisRoutingManager singleton."""
    global _router_instance
    if _router_instance is None:
        _router_instance = RedisRoutingManager()
    return _router_instance


get_redis_routing_manager = get_redis_router


def get_query_cache_client() -> aioredis.Redis:
    """Access Redis DB 0 dedicated to Sub-50ms Query Caching."""
    return get_redis_router().get_client(DB_QUERY_CACHE)


def get_celery_broker_url() -> str:
    """Retrieve Celery broker connection string for Redis DB 1."""
    return get_redis_router().get_connection_url(DB_CELERY_BROKER)


def get_rate_limiter_client() -> aioredis.Redis:
    """Access Redis DB 2 dedicated to Token Bucket Rate Limiting Storage."""
    return get_redis_router().get_client(DB_RATE_LIMITER)


def get_redis_client(db_index: int = DB_QUERY_CACHE) -> aioredis.Redis:
    """Generic accessor for any routed Redis database index."""
    return get_redis_router().get_client(db_index)
