"""Nerolac Operations Dashboard - OpenTelemetry & Prometheus Metrics Exporter.

Captures:
1. HTTP request duration & total request throughput (method, endpoint, status_code).
2. Database connection pool statistics (master & read-replica active, idle, overflow, utilization).
3. Redis multi-instance cache hit ratios (hits, misses, hit ratio across DB 0/1/2).
4. Celery asynchronous background worker queue depth (default, parsing, reconciliation).
5. ML Demand Forecasting performance metrics (MAPE, RMSE).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("nerolac.observability.telemetry")

# ------------------------------------------------------------------------------
# Isolated Metric Registry
# ------------------------------------------------------------------------------
REGISTRY = CollectorRegistry(auto_describe=True)

# ------------------------------------------------------------------------------
# 1. HTTP Request Metrics
# ------------------------------------------------------------------------------
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "nerolac_http_request_duration_seconds",
    "HTTP request execution latency in seconds.",
    ["method", "endpoint", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY,
)

HTTP_REQUESTS_TOTAL = Counter(
    "nerolac_http_requests_total",
    "Total count of processed HTTP requests.",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

# ------------------------------------------------------------------------------
# 2. Database Connection Pool Statistics
# ------------------------------------------------------------------------------
DB_POOL_CONNECTIONS = Gauge(
    "nerolac_db_pool_connections",
    "Current state of PostgreSQL SQLAlchemy connection pool connections.",
    ["pool_type", "state"],  # pool_type: master/replica; state: active, idle, overflow, total
    registry=REGISTRY,
)

DB_POOL_UTILIZATION_RATIO = Gauge(
    "nerolac_db_pool_utilization_ratio",
    "Ratio of active PostgreSQL connections to pool capacity (0.0 to 1.0).",
    ["pool_type"],
    registry=REGISTRY,
)

# ------------------------------------------------------------------------------
# 3. Redis Cache Hit Ratios
# ------------------------------------------------------------------------------
REDIS_CACHE_HITS_TOTAL = Counter(
    "nerolac_redis_cache_hits_total",
    "Total number of cache read hits in Redis.",
    ["db_instance"],
    registry=REGISTRY,
)

REDIS_CACHE_MISSES_TOTAL = Counter(
    "nerolac_redis_cache_misses_total",
    "Total number of cache read misses in Redis.",
    ["db_instance"],
    registry=REGISTRY,
)

REDIS_CACHE_HIT_RATIO = Gauge(
    "nerolac_redis_cache_hit_ratio",
    "Current rolling cache hit ratio (0.0 to 1.0).",
    ["db_instance"],
    registry=REGISTRY,
)

# ------------------------------------------------------------------------------
# 4. Celery Worker Queue Depth
# ------------------------------------------------------------------------------
CELERY_QUEUE_DEPTH = Gauge(
    "nerolac_celery_queue_depth",
    "Current pending tasks depth in Celery Redis queues.",
    ["queue_name"],
    registry=REGISTRY,
)

# ------------------------------------------------------------------------------
# 5. ML Demand Forecasting Errors (MAPE & RMSE)
# ------------------------------------------------------------------------------
ML_FORECAST_MAPE = Gauge(
    "nerolac_ml_forecast_mape",
    "Mean Absolute Percentage Error (MAPE) of ensemble demand forecast.",
    ["depot_id", "sku_id"],
    registry=REGISTRY,
)

ML_FORECAST_RMSE = Gauge(
    "nerolac_ml_forecast_rmse",
    "Root Mean Squared Error (RMSE) in metric tons of demand forecast.",
    ["depot_id", "sku_id"],
    registry=REGISTRY,
)


class TelemetryManager:
    """Manages telemetry metric recording, pool synchronization, and Prometheus export."""

    _instance: TelemetryManager | None = None

    def __init__(self) -> None:
        self.registry = REGISTRY
        # In-memory tracking of Redis hits/misses for ratio calculation
        self._cache_hits: dict[str, int] = {"db0_query_cache": 0, "db1_celery": 0, "db2_rate": 0}
        self._cache_misses: dict[str, int] = {
            "db0_query_cache": 0,
            "db1_celery": 0,
            "db2_rate": 0,
        }

    @classmethod
    def get_instance(cls) -> TelemetryManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_http_request(
        self, method: str, endpoint: str, status_code: int, duration_seconds: float
    ) -> None:
        """Record HTTP latency histogram and counter."""
        # Sanitize path to prevent cardinality explosion (e.g., replace IDs)
        clean_endpoint = endpoint.split("?")[0]
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method, endpoint=clean_endpoint, status_code=str(status_code)
        ).observe(duration_seconds)
        HTTP_REQUESTS_TOTAL.labels(
            method=method, endpoint=clean_endpoint, status_code=str(status_code)
        ).inc()

    def update_db_pool_stats(
        self,
        pool_type: str,
        active: int,
        idle: int,
        overflow: int,
        max_capacity: int = 50,
    ) -> None:
        """Update connection pool gauges."""
        DB_POOL_CONNECTIONS.labels(pool_type=pool_type, state="active").set(active)
        DB_POOL_CONNECTIONS.labels(pool_type=pool_type, state="idle").set(idle)
        DB_POOL_CONNECTIONS.labels(pool_type=pool_type, state="overflow").set(overflow)
        DB_POOL_CONNECTIONS.labels(pool_type=pool_type, state="total").set(active + idle)

        utilization = active / max_capacity if max_capacity > 0 else 0.0
        DB_POOL_UTILIZATION_RATIO.labels(pool_type=pool_type).set(min(utilization, 1.0))

    def record_cache_hit(self, db_instance: str = "db0_query_cache") -> None:
        """Increment Redis cache hit counter and update hit ratio."""
        REDIS_CACHE_HITS_TOTAL.labels(db_instance=db_instance).inc()
        self._cache_hits[db_instance] = self._cache_hits.get(db_instance, 0) + 1
        self._recalculate_cache_ratio(db_instance)

    def record_cache_miss(self, db_instance: str = "db0_query_cache") -> None:
        """Increment Redis cache miss counter and update hit ratio."""
        REDIS_CACHE_MISSES_TOTAL.labels(db_instance=db_instance).inc()
        self._cache_misses[db_instance] = self._cache_misses.get(db_instance, 0) + 1
        self._recalculate_cache_ratio(db_instance)

    def _recalculate_cache_ratio(self, db_instance: str) -> None:
        hits = self._cache_hits.get(db_instance, 0)
        misses = self._cache_misses.get(db_instance, 0)
        total = hits + misses
        ratio = (hits / total) if total > 0 else 1.0
        REDIS_CACHE_HIT_RATIO.labels(db_instance=db_instance).set(round(ratio, 4))

    def update_celery_queue_depth(self, queue_name: str, depth: int) -> None:
        """Set Celery queue depth gauge."""
        CELERY_QUEUE_DEPTH.labels(queue_name=queue_name).set(depth)

    def update_ml_metrics(self, depot_id: str, sku_id: str, mape: float, rmse: float) -> None:
        """Update ML forecasting error gauges for model drift tracking."""
        ML_FORECAST_MAPE.labels(depot_id=depot_id, sku_id=sku_id).set(mape)
        ML_FORECAST_RMSE.labels(depot_id=depot_id, sku_id=sku_id).set(rmse)

    async def sync_live_infrastructure_stats(self) -> None:
        """Collect current live connection pool and cache statistics."""
        try:
            from src.backend.database.session_router import get_routing_manager

            router = get_routing_manager()
            # Sample primary write pool
            primary_pool: Any = router.primary_engine.pool
            if hasattr(primary_pool, "checkedout"):
                self.update_db_pool_stats(
                    pool_type="primary",
                    active=primary_pool.checkedout(),
                    idle=primary_pool.checkedin(),
                    overflow=primary_pool.overflow(),
                    max_capacity=primary_pool.size() + getattr(primary_pool, "_max_overflow", 25),
                )
            # Sample read replica pool
            replica_pool: Any = router.replica_engine.pool
            if hasattr(replica_pool, "checkedout"):
                self.update_db_pool_stats(
                    pool_type="read_replica",
                    active=replica_pool.checkedout(),
                    idle=replica_pool.checkedin(),
                    overflow=replica_pool.overflow(),
                    max_capacity=replica_pool.size() + getattr(replica_pool, "_max_overflow", 25),
                )
        except Exception as e:
            logger.debug("Telemetry DB pool sampling note: %s", e)

        try:
            from typing import cast

            from src.backend.config.redis_config import DB_CELERY_BROKER, get_redis_routing_manager

            redis_mgr = get_redis_routing_manager()
            # Inspect queue depth on Celery Redis instance (DB 1)
            client_db1 = redis_mgr.get_client(DB_CELERY_BROKER)
            queue_len_raw = await cast(Any, client_db1.llen("celery"))
            queue_len = int(queue_len_raw) if queue_len_raw is not None else 0
            self.update_celery_queue_depth("celery_default", queue_len)
        except Exception as e:
            logger.debug("Telemetry Redis sampling note: %s", e)

    def export_metrics(self) -> bytes:
        """Export all registered metrics in standard Prometheus exposition format."""
        return generate_latest(self.registry)


def get_telemetry_manager() -> TelemetryManager:
    """Retrieve singleton TelemetryManager."""
    return TelemetryManager.get_instance()


def record_http_request(
    method: str, endpoint: str, status_code: int, duration_seconds: float
) -> None:
    """Convenience helper to record HTTP request metrics."""
    get_telemetry_manager().record_http_request(method, endpoint, status_code, duration_seconds)


class TelemetryMiddleware(BaseHTTPMiddleware):
    """ASGI Middleware capturing HTTP request durations and status codes."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start_time = time.perf_counter()
        status_code = 500
        try:
            raw_response = await call_next(request)
            response: Response = raw_response
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=status_code,
                duration_seconds=duration,
            )
