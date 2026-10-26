"""Cache-Aside Invalidation Engine for Redis 7 Query Caching.

Implements the Cache-Aside invalidation pattern:
1. Sub-50ms query cache operates on Redis DB 0.
2. Invalidation hooks automatically flush relevant dashboard keys upon completion
   of SAP ETL batch drops (FAGLL03 Finance, VA05 Sales, MB52 Inventory, ME2L Procurement).
3. Uses non-blocking cursor scans (SCAN) to prevent latency spikes on production Redis instances.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any

import redis.asyncio as aioredis

from src.backend.config.redis_config import get_query_cache_client
from src.backend.etl.file_verifier import SAPReportType

logger = logging.getLogger("nerolac.cache.invalidation")

DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes default query cache TTL

# Mapping of SAP Report Drops to Redis DB 0 Dashboard Cache Key Patterns
REPORT_CACHE_INVALIDATION_PATTERNS: dict[str, list[str]] = {
    SAPReportType.FAGLL03.value: [
        "dash:finance:*",
        "dash:pnl:*",
        "dash:kpi:*",
        "cache:trial_balance:*",
        "cache:financial_actuals:*",
    ],
    SAPReportType.VA05.value: [
        "dash:sales:*",
        "dash:scm:*",
        "dash:kpi:*",
        "cache:historical_sales:*",
        "cache:reconciliation:*",
    ],
    SAPReportType.MB52.value: [
        "dash:inventory:*",
        "dash:stock:*",
        "dash:kpi:*",
        "cache:stockout:*",
        "cache:depot_inventory:*",
    ],
    SAPReportType.ME2L.value: [
        "dash:procurement:*",
        "dash:bom:*",
        "dash:kpi:*",
        "cache:procurement:*",
        "cache:supplier:*",
    ],
}


@dataclass
class InvalidationResult:
    """Detailed summary of cache keys flushed after a data pipeline drop."""

    report_type: str
    patterns_evaluated: list[str]
    keys_deleted_count: int
    depot_id: str | None = None
    flushed_keys: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


def _json_serializer(obj: Any) -> Any:
    """Helper serializer for dates and datetimes in cache payloads."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} is not JSON serializable")


class CacheAsideManager:
    """Manages Cache-Aside reads, writes, and pattern-based invalidations on Redis DB 0."""

    def __init__(self, client: aioredis.Redis | None = None) -> None:
        self._custom_client = client

    @property
    def client(self) -> aioredis.Redis:
        """Lazily retrieve the DB 0 query cache client."""
        if self._custom_client is not None:
            return self._custom_client
        return get_query_cache_client()

    async def get(self, key: str) -> Any | None:
        """Fetch and deserialize a cached object from Redis DB 0.

        Returns None on cache miss.
        """
        try:
            val = await self.client.get(key)
            if val is None:
                return None
            return json.loads(val)
        except Exception as exc:
            logger.warning("Cache GET failed for key '%s': %s", key, exc)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    ) -> bool:
        """Serialize and store an object in Redis DB 0 with an expiration TTL."""
        try:
            payload = json.dumps(value, default=_json_serializer)
            await self.client.set(key, payload, ex=ttl_seconds)
            return True
        except Exception as exc:
            logger.warning("Cache SET failed for key '%s': %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        """Explicitly delete a specific key from Redis DB 0."""
        try:
            res = await self.client.delete(key)
            return bool(res > 0)
        except Exception as exc:
            logger.warning("Cache DELETE failed for key '%s': %s", key, exc)
            return False

    async def flush_pattern(self, pattern: str) -> list[str]:
        """Non-blocking cursor scan and deletion of keys matching a glob pattern."""
        deleted_keys: list[str] = []
        try:
            keys_to_del: list[str] = []
            async for k in self.client.scan_iter(match=pattern, count=100):
                keys_to_del.append(k)
                if len(keys_to_del) >= 500:
                    await self.client.delete(*keys_to_del)
                    deleted_keys.extend(keys_to_del)
                    keys_to_del.clear()

            if keys_to_del:
                await self.client.delete(*keys_to_del)
                deleted_keys.extend(keys_to_del)

        except Exception as exc:
            logger.error("Error flushing cache pattern '%s': %s", pattern, exc)

        return deleted_keys

    async def invalidate_on_sap_drop(
        self,
        report_type: SAPReportType | str,
        depot_id: str | None = None,
    ) -> InvalidationResult:
        """Automatically flush relevant dashboard cache keys upon SAP ETL drop completion.

        Maps:
        - FAGLL03 -> flushes Finance P&L tree grids, KPI metrics.
        - VA05    -> flushes Sales trends, SCM forecasts, KPI metrics.
        - MB52    -> flushes Inventory snapshots, depot days-of-supply.
        - ME2L    -> flushes Procurement registers, supplier spend.
        """
        if isinstance(report_type, SAPReportType):
            r_type = report_type.value
        else:
            r_type = str(report_type).upper()

        base_patterns = REPORT_CACHE_INVALIDATION_PATTERNS.get(
            r_type, [f"dash:{r_type.lower()}:*", "dash:kpi:*"]
        )

        patterns_to_evaluate: list[str] = list(base_patterns)

        # If a specific depot was updated, add targeted depot cache patterns
        if depot_id:
            d_clean = depot_id.strip().upper()
            patterns_to_evaluate.extend(
                [
                    f"dash:*:{d_clean}:*",
                    f"cache:*:{d_clean}:*",
                ]
            )

        all_deleted_keys: list[str] = []
        for pat in patterns_to_evaluate:
            flushed = await self.flush_pattern(pat)
            all_deleted_keys.extend(flushed)

        unique_deleted = list(set(all_deleted_keys))

        logger.info(
            "Flushed %d cache keys across %d patterns for SAP drop '%s' [depot=%s]",
            len(unique_deleted),
            len(patterns_to_evaluate),
            r_type,
            depot_id or "ALL",
        )

        return InvalidationResult(
            report_type=r_type,
            patterns_evaluated=patterns_to_evaluate,
            keys_deleted_count=len(unique_deleted),
            depot_id=depot_id,
            flushed_keys=unique_deleted,
        )

    async def flush_all_dashboard_cache(self) -> int:
        """Emergency or daily full flush of all dashboard cache keys (`dash:*`)."""
        deleted = await self.flush_pattern("dash:*")
        return len(deleted)


# Global singleton instance
_cache_aside_manager: CacheAsideManager | None = None


def get_cache_manager() -> CacheAsideManager:
    """Return the global CacheAsideManager instance."""
    global _cache_aside_manager
    if _cache_aside_manager is None:
        _cache_aside_manager = CacheAsideManager()
    return _cache_aside_manager


async def invalidate_on_sap_drop(
    report_type: SAPReportType | str,
    depot_id: str | None = None,
) -> InvalidationResult:
    """Convenience helper to trigger cache-aside invalidation on SAP batch drop."""
    return await get_cache_manager().invalidate_on_sap_drop(report_type, depot_id)
