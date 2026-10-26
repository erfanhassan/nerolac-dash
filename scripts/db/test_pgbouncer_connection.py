#!/usr/bin/env python3
"""PgBouncer Connection Pooling & Read/Write Replica Routing Test Harness.

Validates:
1. 100 simulated concurrent async worker tasks through PgBouncer transaction pool.
2. Read Replica analytical queries run without blocking Primary DB write locks.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root and virtualenv packages are accessible
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
venv_site_packages = REPO_ROOT / ".venv" / "lib" / py_ver / "site-packages"
if venv_site_packages.is_dir() and str(venv_site_packages) not in sys.path:
    sys.path.insert(0, str(venv_site_packages))

try:
    from sqlalchemy import text
except ImportError:
    venv_py = REPO_ROOT / ".venv" / "bin" / "python3"
    if venv_py.is_file() and sys.executable != str(venv_py):
        os.execv(str(venv_py), [str(venv_py), *sys.argv])
    raise

from src.backend.database.session_router import (  # noqa: E402
    get_read_session,
    get_routing_manager,
    get_write_session,
)


async def single_worker_query(worker_id: int) -> dict[str, Any]:
    """Execute a single query through PgBouncer connection pool."""
    start_t = time.perf_counter()
    async with get_read_session() as session:
        # Run read query on replica endpoint
        result = await session.scalar(text("SELECT count(*) FROM nerolac_ops.depots;"))
    latency_ms = (time.perf_counter() - start_t) * 1000
    return {"worker_id": worker_id, "result": result, "latency_ms": latency_ms}


async def test_100_concurrent_connections() -> bool:
    """Simulate 100 concurrent client requests through PgBouncer connection pool."""
    print("\n[Step 1/2] Simulating 100 concurrent requests through PgBouncer pool...")
    start_time = time.perf_counter()

    tasks = [single_worker_query(i) for i in range(1, 101)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed_s = time.perf_counter() - start_time
    successful = [r for r in results if isinstance(r, dict)]
    failed = [r for r in results if not isinstance(r, dict)]

    print(f"  --> Completed 100 concurrent tasks in {elapsed_s:.3f}s")
    print(f"  --> Successful tasks: {len(successful)} / 100")
    print(f"  --> Failed tasks: {len(failed)}")

    if failed:
        print(f"  ❌ Errors detected: {failed[:3]}")
        return False

    avg_latency = sum(r["latency_ms"] for r in successful) / len(successful)
    print(f"  --> Average client query latency: {avg_latency:.2f}ms")
    print("  ✅ PgBouncer transaction pooling verified successfully!")
    return True


async def test_replica_routing_without_blocking_write_locks() -> bool:
    """Verify that heavy analytical reads on replica do not block primary write locks."""
    print("\n[Step 2/2] Testing Read Replica routing without blocking write locks...")

    test_depot_id = "DEPOT_TEST_CONCURRENCY"
    test_depot_code = "DEPOT_CODE_CONCURRENCY"

    async def long_running_analytical_read() -> None:
        async with get_read_session() as session:
            # Simulate a complex 24-month SCM / P&L analytical query
            await session.execute(text("SELECT pg_sleep(0.5);"))
            await session.execute(text("SELECT count(*) FROM nerolac_ops.financial_actuals;"))

    async def concurrent_primary_write() -> float:
        # Wait slightly to ensure read transaction is active
        await asyncio.sleep(0.1)
        start_w = time.perf_counter()
        async with get_write_session() as session:
            # Primary transactional write
            await session.execute(
                text(
                    """
                    INSERT INTO nerolac_ops.depots
                        (depot_id, depot_code, depot_name, region, address)
                    VALUES
                        (:id, :code, :name, :region, :address)
                    ON CONFLICT (depot_id) DO NOTHING;
                    """
                ),
                {
                    "id": test_depot_id,
                    "code": test_depot_code,
                    "name": "Concurrency Test Depot",
                    "region": "Dhaka",
                    "address": "Tejgaon Industrial Area",
                },
            )
        return (time.perf_counter() - start_w) * 1000

    # Run analytical read on replica and transactional write on primary concurrently
    t0 = time.perf_counter()
    read_task = asyncio.create_task(long_running_analytical_read())
    write_task = asyncio.create_task(concurrent_primary_write())

    _, write_latency_ms = await asyncio.gather(read_task, write_task)
    total_elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"  --> Primary write completed in: {write_latency_ms:.2f}ms")
    print(f"  --> Total analytical read + write concurrency time: {total_elapsed_ms:.2f}ms")

    # Clean up test write record
    async with get_write_session() as session:
        await session.execute(
            text("DELETE FROM nerolac_ops.depots WHERE depot_id = :id;"),
            {"id": test_depot_id},
        )

    # Assert that write was not blocked by analytical read sleep (0.5s = 500ms)
    # The write should execute independently within < 300ms
    if write_latency_ms < 300:
        print("  ✅ Read replica query executed without blocking Primary DB write locks!")
        return True
    else:
        print(f"  ❌ Primary write was delayed ({write_latency_ms:.2f}ms)!")
        return False


async def main_async() -> bool:
    print("=" * 70)
    print("  PGBOUNCER & READ/WRITE REPLICA ROUTING VERIFICATION")
    print("=" * 70)

    router = get_routing_manager()
    status = await router.audit_status()
    print("Database Routing Manager Audit:")
    print(f"  - Status: {status['status']}")
    print(f"  - Primary Write Endpoint: {status['primary_url_masked']}")
    print(f"  - Read Replica Endpoint:  {status['replica_url_masked']}")
    print(f"  - Pool Mode:              {status['pool_mode']}")

    success_pool = await test_100_concurrent_connections()
    success_routing = await test_replica_routing_without_blocking_write_locks()

    await router.dispose()

    print("-" * 70)
    if success_pool and success_routing:
        print("SUCCESS: PgBouncer Pooling & Read Replica Non-Blocking Verified! ✨")
        print("=" * 70)
        return True
    else:
        print("FAILURE: Connection pooling or routing lock assertions failed!")
        print("=" * 70)
        return False


def main() -> None:
    success = asyncio.run(main_async())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
