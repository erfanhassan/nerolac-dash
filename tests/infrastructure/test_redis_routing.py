"""Test suite for Multi-Instance Redis 7 Routing, Cache-Aside, and Token Bucket Rate Limiter.

Verification Protocols:
1. Multi-DB routing across DB 0 (query cache), DB 1 (celery broker), DB 2 (rate limiter).
2. Data isolation across separate Redis DB namespaces.
3. Cache-Aside pattern with non-blocking scans and automatic SAP batch drop invalidation.
4. Token Bucket rate limiter enforcement (100 req/min, burst limits, client isolation).
5. FastAPI middleware HTTP 429 Too Many Requests enforcement with Retry-After headers.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.backend.cache.cache_invalidation import (
    SAPReportType,
    get_cache_manager,
    invalidate_on_sap_drop,
)
from src.backend.config.redis_config import (
    DB_CELERY_BROKER,
    DB_QUERY_CACHE,
    DB_RATE_LIMITER,
    get_celery_broker_url,
    get_query_cache_client,
    get_rate_limiter_client,
    get_redis_routing_manager,
)
from src.backend.middleware.rate_limiter import (
    RateLimiterMiddleware,
    TokenBucketRateLimiter,
)


class TestRedisDatabaseRouting:
    """Verifies Redis 7 multi-DB routing and logical database isolation."""

    def test_database_index_constants(self) -> None:
        """Assert architectural DB assignments match specification."""
        assert DB_QUERY_CACHE == 0, "DB 0 must be dedicated to Sub-50ms Query Cache"
        assert DB_CELERY_BROKER == 1, "DB 1 must be dedicated to Celery Broker"
        assert DB_RATE_LIMITER == 2, "DB 2 must be dedicated to Rate Limiter"

    def test_celery_broker_url_construction(self) -> None:
        """Verify Celery broker URL routes to DB 1 and complies with sovereignty."""
        broker_url = get_celery_broker_url()
        assert broker_url.startswith("redis://")
        assert broker_url.endswith("/1"), "Celery broker must target Redis DB index 1"

    async def test_multi_db_live_connections(self) -> None:
        """Verify live connectivity and ping response on DB 0, DB 1, and DB 2."""
        manager = get_redis_routing_manager()
        audit = await manager.audit_health()

        assert audit["status"] == "HEALTHY", f"Redis health audit degraded: {audit}"
        assert audit["databases"]["db_0"]["connected"] is True
        assert audit["databases"]["db_1"]["connected"] is True
        assert audit["databases"]["db_2"]["connected"] is True

    async def test_multi_db_key_isolation(self) -> None:
        """Verify keys written to DB 0, DB 1, and DB 2 remain strictly isolated."""
        client_db0 = get_query_cache_client()
        client_db1 = get_redis_routing_manager().get_client(DB_CELERY_BROKER)
        client_db2 = get_rate_limiter_client()

        key_db0 = "test:isolation:db0:unique"
        key_db2 = "test:isolation:db2:unique"

        # Write to DB 0 and DB 2
        await client_db0.set(key_db0, "cache_data", ex=30)
        await client_db2.set(key_db2, "rate_data", ex=30)

        try:
            # DB 0 key must exist in DB 0, but NOT in DB 1 or DB 2
            assert await client_db0.get(key_db0) == "cache_data"
            assert await client_db1.get(key_db0) is None
            assert await client_db2.get(key_db0) is None

            # DB 2 key must exist in DB 2, but NOT in DB 0 or DB 1
            assert await client_db2.get(key_db2) == "rate_data"
            assert await client_db0.get(key_db2) is None
            assert await client_db1.get(key_db2) is None
        finally:
            await client_db0.delete(key_db0)
            await client_db2.delete(key_db2)


@pytest.mark.asyncio
class TestCacheAsideInvalidation:
    """Verifies Cache-Aside storage and automated SAP ETL drop invalidation."""

    async def test_cache_aside_crud(self) -> None:
        """Verify CacheAsideManager set, get, and delete operations on DB 0."""
        cache = get_cache_manager()
        test_key = "dash:test:pnl:q1"
        test_payload = {
            "depot": "DHK",
            "net_revenue_bdt": 4500000.50,
            "items": ["BOM_RESIN_01", "BOM_SOLVENT_02"],
        }

        # Set
        success = await cache.set(test_key, test_payload, ttl_seconds=60)
        assert success is True

        # Get
        cached_data = await cache.get(test_key)
        assert cached_data == test_payload

        # Delete
        deleted = await cache.delete(test_key)
        assert deleted is True
        assert await cache.get(test_key) is None

    async def test_invalidation_on_fagll03_finance_drop(self) -> None:
        """Assert FAGLL03 drops invalidate finance and KPI caches while preserving sales."""
        cache = get_cache_manager()
        k_finance = "dash:finance:ebitda_summary"
        k_kpi = "dash:kpi:monthly_run_rate"
        k_sales = "dash:sales:reconciliation_trend"

        await cache.set(k_finance, {"val": 100}, ttl_seconds=60)
        await cache.set(k_kpi, {"val": 200}, ttl_seconds=60)
        await cache.set(k_sales, {"val": 300}, ttl_seconds=60)

        try:
            result = await invalidate_on_sap_drop(SAPReportType.FAGLL03)
            assert result.report_type == "FAGLL03"
            assert result.keys_deleted_count >= 2

            # Finance and KPI keys must be invalidated
            assert await cache.get(k_finance) is None
            assert await cache.get(k_kpi) is None

            # Unrelated sales keys must be preserved
            assert await cache.get(k_sales) == {"val": 300}
        finally:
            await cache.delete(k_sales)

    async def test_invalidation_on_va05_sales_drop(self) -> None:
        """Assert VA05 sales drops invalidate sales and SCM trends while preserving inventory."""
        cache = get_cache_manager()
        k_sales = "dash:sales:dealer_ranking"
        k_scm = "dash:scm:24m_trend"
        k_inventory = "dash:inventory:stockout_mask"

        await cache.set(k_sales, {"val": 1}, ttl_seconds=60)
        await cache.set(k_scm, {"val": 2}, ttl_seconds=60)
        await cache.set(k_inventory, {"val": 3}, ttl_seconds=60)

        try:
            result = await invalidate_on_sap_drop("VA05")
            assert result.report_type == "VA05"

            assert await cache.get(k_sales) is None
            assert await cache.get(k_scm) is None
            assert await cache.get(k_inventory) == {"val": 3}
        finally:
            await cache.delete(k_inventory)

    async def test_invalidation_on_mb52_inventory_drop(self) -> None:
        """Assert MB52 inventory drops flush inventory snapshots and stockout caches."""
        cache = get_cache_manager()
        k_stock = "dash:inventory:ctg_stockout_flag"
        k_procurement = "dash:procurement:active_pos"

        await cache.set(k_stock, {"status": "stockout"}, ttl_seconds=60)
        await cache.set(k_procurement, {"status": "pending"}, ttl_seconds=60)

        try:
            result = await invalidate_on_sap_drop("MB52")
            assert result.report_type == "MB52"

            assert await cache.get(k_stock) is None
            assert await cache.get(k_procurement) == {"status": "pending"}
        finally:
            await cache.delete(k_procurement)

    async def test_invalidation_on_me2l_procurement_drop(self) -> None:
        """Assert ME2L procurement drops flush raw material and supplier caches."""
        cache = get_cache_manager()
        k_proc = "dash:procurement:tio2_import_cost"
        k_bom = "dash:bom:contribution_margins"

        await cache.set(k_proc, {"cost": 420.50}, ttl_seconds=60)
        await cache.set(k_bom, {"margin": 0.38}, ttl_seconds=60)

        result = await invalidate_on_sap_drop("ME2L")
        assert result.report_type == "ME2L"

        assert await cache.get(k_proc) is None
        assert await cache.get(k_bom) is None

    async def test_invalidation_depot_scoping(self) -> None:
        """Verify depot scoping adds targeted depot invalidation patterns."""
        cache = get_cache_manager()
        k_ctg = "dash:inventory:CTG:batch_stock"
        k_dhk = "dash:inventory:DHK:batch_stock"

        await cache.set(k_ctg, {"depot": "CTG"}, ttl_seconds=60)
        await cache.set(k_dhk, {"depot": "DHK"}, ttl_seconds=60)

        result = await invalidate_on_sap_drop("MB52", depot_id="CTG")
        assert result.depot_id == "CTG"
        assert any("CTG" in p for p in result.patterns_evaluated)

        assert await cache.get(k_ctg) is None
        assert await cache.get(k_dhk) is None  # MB52 flushes dash:inventory:* as well


@pytest.mark.asyncio
class TestTokenBucketRateLimiter:
    """Verifies atomic Token Bucket algorithm behavior on Redis DB 2."""

    async def test_token_bucket_exhaustion_and_refill(self) -> None:
        """Verify token depletion and rejection when capacity is exceeded."""
        client_id = "test_user_unit_01"
        limiter = TokenBucketRateLimiter(rate_per_minute=60, burst_capacity=5)

        # Clear any prior test state
        await limiter.reset(client_id)

        try:
            # First 5 calls consume the 5 initial burst tokens
            for i in range(5):
                decision = await limiter.check_rate_limit(client_id, cost=1)
                assert decision.allowed is True, f"Request {i+1} should be allowed"
                assert decision.remaining_tokens == 4 - i

            # 6th call must be denied immediately
            decision = await limiter.check_rate_limit(client_id, cost=1)
            assert decision.allowed is False
            assert decision.remaining_tokens == 0
            assert decision.retry_after_seconds >= 1
            assert decision.limit_per_minute == 60

            # Resetting tokens restores availability
            await limiter.reset(client_id)
            decision = await limiter.check_rate_limit(client_id, cost=1)
            assert decision.allowed is True
        finally:
            await limiter.reset(client_id)

    async def test_token_bucket_user_isolation(self) -> None:
        """Verify tokens are isolated across different user identifiers."""
        limiter = TokenBucketRateLimiter(rate_per_minute=60, burst_capacity=3)
        user_a = "user_account_a"
        user_b = "user_account_b"

        await limiter.reset(user_a)
        await limiter.reset(user_b)

        try:
            # Exhaust User A
            for _ in range(3):
                await limiter.check_rate_limit(user_a)

            decision_a = await limiter.check_rate_limit(user_a)
            assert decision_a.allowed is False

            # User B must still have full tokens
            decision_b = await limiter.check_rate_limit(user_b)
            assert decision_b.allowed is True
            assert decision_b.remaining_tokens == 2
        finally:
            await limiter.reset(user_a)
            await limiter.reset(user_b)


@pytest.mark.asyncio
class TestFastAPIRateLimiterMiddleware:
    """Verifies FastAPI middleware returns HTTP 429 and Retry-After headers."""

    def _build_test_app(self, burst_capacity: int = 5, rate_per_minute: int = 60) -> FastAPI:
        """Build test FastAPI app with RateLimiterMiddleware attached."""
        app = FastAPI(title="Nerolac Test API")
        app.add_middleware(
            RateLimiterMiddleware,
            rate_per_minute=rate_per_minute,
            burst_capacity=burst_capacity,
            exempt_paths=["/health"],
        )

        @app.get("/health")
        async def health_endpoint() -> dict[str, str]:
            return {"status": "healthy"}

        @app.get("/api/v1/dashboard/pnl")
        async def dashboard_pnl() -> dict[str, str]:
            return {"report": "pnl_summary", "currency": "BDT"}

        return app

    async def test_exempt_endpoint_bypasses_rate_limiter(self) -> None:
        """Verify exempt endpoints like /health are never throttled."""
        app = self._build_test_app(burst_capacity=2, rate_per_minute=60)
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Send 10 consecutive requests to /health
            for _ in range(10):
                resp = await client.get("/health")
                assert resp.status_code == 200
                assert resp.json() == {"status": "healthy"}

    async def test_rate_limiter_allows_requests_within_capacity(self) -> None:
        """Verify requests within token quota succeed with 200 and telemetry headers."""
        app = self._build_test_app(burst_capacity=10, rate_per_minute=100)
        transport = ASGITransport(app=app)
        user_header = {"X-User-ID": "director_finance_dhaka"}

        # Reset limiter for test client
        limiter = TokenBucketRateLimiter()
        await limiter.reset("user:director_finance_dhaka")

        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/api/v1/dashboard/pnl", headers=user_header)
            assert resp.status_code == 200
            assert resp.json() == {"report": "pnl_summary", "currency": "BDT"}
            assert resp.headers["X-RateLimit-Limit"] == "100"
            assert "X-RateLimit-Remaining" in resp.headers

        await limiter.reset("user:director_finance_dhaka")

    async def test_rate_limiter_enforces_http_429_on_burst_exhaustion(self) -> None:
        """Assert rate limiter returns HTTP 429 when client requests exceed token limit."""
        burst_cap = 4
        app = self._build_test_app(burst_capacity=burst_cap, rate_per_minute=60)
        transport = ASGITransport(app=app)
        user_id = "analyst_burst_test_user"
        user_header = {"X-User-ID": user_id}

        limiter = TokenBucketRateLimiter()
        await limiter.reset(f"user:{user_id}")

        try:
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                # 1. Exhaust allowed burst capacity (4 requests)
                for i in range(burst_cap):
                    resp = await client.get("/api/v1/dashboard/pnl", headers=user_header)
                    assert (
                        resp.status_code == 200
                    ), f"Request {i+1} failed with status {resp.status_code}"

                # 2. 5th request must be rejected with HTTP 429 Too Many Requests
                throttled_resp = await client.get("/api/v1/dashboard/pnl", headers=user_header)
                assert (
                    throttled_resp.status_code == 429
                ), f"Expected HTTP 429, got {throttled_resp.status_code}"

                # 3. Assert RFC-compliant telemetry headers
                assert "Retry-After" in throttled_resp.headers
                assert int(throttled_resp.headers["Retry-After"]) >= 1
                assert throttled_resp.headers["X-RateLimit-Limit"] == "60"
                assert throttled_resp.headers["X-RateLimit-Remaining"] == "0"

                # 4. Assert structured error body
                payload = throttled_resp.json()
                assert payload["error"] == "Too Many Requests"
                assert "Maximum 60 requests per minute permitted" in payload["detail"]
                assert payload["retry_after_seconds"] >= 1
        finally:
            await limiter.reset(f"user:{user_id}")
