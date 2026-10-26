#!/usr/bin/env python3
"""Verification Script: 50,000-Row Historical SAP Backfill Test Harness.

BUILD & VERIFICATION PROTOCOL:
1. Run `/scripts/etl/run_historical_backfill_test.py` with 50,000 synthetic rows.
2. Verify backfill completes in <10 seconds.
3. Verify re-running the script results in zero duplicate rows (idempotent upserts).
4. Verify execution performance metrics are logged to `audit_logs` table.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any

# Ensure workspace root is in sys.path when invoked directly
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import asyncpg  # noqa: E402

from src.backend.config.vault import get_vault_client  # noqa: E402
from src.backend.etl.historical_backfill import (  # noqa: E402
    DEFAULT_BATCH_SIZE,
    HistoricalSAPBackfillWorker,
    TrialBalanceRecord,
)

MAX_ALLOWED_DURATION_SECONDS = 10.0


async def get_db_connection() -> asyncpg.Connection:
    """Retrieve database connection credentials securely from Vault."""
    vault = get_vault_client()
    creds = vault.get_database_credentials()
    user = creds["user"]
    password = creds["password"]
    host = creds["host"]
    port = creds["port"]
    database = creds["database"]
    dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return await asyncpg.connect(dsn)


async def run_backfill_test(
    num_rows: int = 50000,
    batch_size: int = DEFAULT_BATCH_SIZE,
    reset: bool = True,
) -> bool:
    """Execute the full backfill and re-run verification protocol."""
    print("=" * 78)
    print("  NEROLAC DASH: 24-MONTH HISTORICAL SAP BACKFILL PERFORMANCE TEST")
    print("=" * 78)
    print(f"Target Row Count:   {num_rows:,} synthetic records")
    print(f"Batch Chunk Size:   {batch_size:,} rows per transaction")
    print(f"SLA Time Threshold: < {MAX_ALLOWED_DURATION_SECONDS:.1f} seconds")
    print("Conflict Target:    (fiscal_year, fiscal_month, depot_id, gl_code, segment_code)")
    print("-" * 78)

    # 1. Generate 50,000 synthetic records across 24 historical months
    print(f"--> Generating {num_rows:,} synthetic SAP trial balance records (24-month span)...")
    t_gen_start = time.perf_counter()
    records = HistoricalSAPBackfillWorker.generate_synthetic_trial_balances(
        count=num_rows,
        start_year=2024,
        months_span=24,
    )
    t_gen = time.perf_counter() - t_gen_start
    print(f"    Generated {len(records):,} records in {t_gen:.3f}s.")

    if len(records) != num_rows:
        print(f"ERROR: Expected {num_rows} records, got {len(records)}")
        return False

    conn = await get_db_connection()

    if reset:
        print("--> Truncating nerolac_ops.sap_trial_balances for clean baseline...")
        await conn.execute("TRUNCATE TABLE nerolac_ops.sap_trial_balances;")

    worker = HistoricalSAPBackfillWorker(batch_size=batch_size)

    # 2. RUN 1: Initial Historical Backfill
    print("\n--> [RUN 1] Executing initial historical backfill...")
    t0_run1 = time.perf_counter()
    res1 = await worker.backfill_trial_balances(
        records=records,
        batch_id="TEST_RUN_1_INITIAL",
    )
    t_run1 = time.perf_counter() - t0_run1

    db_count_run1: int = await conn.fetchval("SELECT count(*) FROM nerolac_ops.sap_trial_balances;")

    # Verify audit_log entry for Run 1
    audit_row_1 = await conn.fetchrow(
        """
        SELECT log_id, action, entity_type, entity_id, changes, created_at
        FROM nerolac_ops.audit_logs
        WHERE entity_id = $1
        ORDER BY log_id DESC LIMIT 1;
        """,
        res1.batch_id,
    )

    print(f"    Duration:         {t_run1:.3f}s (SLA limit: < {MAX_ALLOWED_DURATION_SECONDS}s)")
    print(f"    Rows Ingested:    {res1.total_rows:,}")
    print(f"    Throughput:       {res1.throughput_rows_per_sec:,.1f} rows/second")
    print(f"    DB Total Rows:    {db_count_run1:,}")
    print(f"    Audit Log ID:     {audit_row_1['log_id'] if audit_row_1 else 'MISSING'}")

    # Assertions for Run 1
    if t_run1 >= MAX_ALLOWED_DURATION_SECONDS:
        print(f"FAIL: Run 1 duration ({t_run1:.3f}s) exceeded {MAX_ALLOWED_DURATION_SECONDS}s SLA.")
        await conn.close()
        return False

    if db_count_run1 != num_rows:
        print(f"FAIL: DB row count ({db_count_run1}) does not match expected ({num_rows}).")
        await conn.close()
        return False

    if audit_row_1 is None:
        print("FAIL: No audit log entry recorded for Run 1.")
        await conn.close()
        return False

    # 3. RUN 2: Re-run with Updated Amounts (Idempotency Verification)
    print("\n--> [RUN 2] Executing re-run of the exact same 50,000 keys (idempotent upsert)...")
    updated_records: list[TrialBalanceRecord] = [
        TrialBalanceRecord(
            fiscal_year=r.fiscal_year,
            fiscal_month=r.fiscal_month,
            depot_id=r.depot_id,
            gl_code=r.gl_code,
            segment_code=r.segment_code,
            amount=round(r.amount + 500.00, 2),  # modify amount to test update
        )
        for r in records
    ]

    t0_run2 = time.perf_counter()
    res2 = await worker.backfill_trial_balances(
        records=updated_records,
        batch_id="TEST_RUN_2_RERUN",
    )
    t_run2 = time.perf_counter() - t0_run2

    db_count_run2: int = await conn.fetchval("SELECT count(*) FROM nerolac_ops.sap_trial_balances;")

    # Verify audit_log entry for Run 2
    audit_row_2 = await conn.fetchrow(
        """
        SELECT log_id, action, entity_type, entity_id, changes, created_at
        FROM nerolac_ops.audit_logs
        WHERE entity_id = $1
        ORDER BY log_id DESC LIMIT 1;
        """,
        res2.batch_id,
    )

    duplicate_rows = db_count_run2 - num_rows
    print(f"    Duration:         {t_run2:.3f}s (SLA limit: < {MAX_ALLOWED_DURATION_SECONDS}s)")
    print(f"    Rows Processed:   {res2.total_rows:,}")
    print(f"    Throughput:       {res2.throughput_rows_per_sec:,.1f} rows/second")
    print(f"    DB Total Rows:    {db_count_run2:,}")
    print(f"    Duplicate Rows:   {duplicate_rows} (Expected: 0)")
    print(f"    Audit Log ID:     {audit_row_2['log_id'] if audit_row_2 else 'MISSING'}")

    # Assertions for Run 2
    if t_run2 >= MAX_ALLOWED_DURATION_SECONDS:
        print(f"FAIL: Run 2 duration ({t_run2:.3f}s) exceeded {MAX_ALLOWED_DURATION_SECONDS}s SLA.")
        await conn.close()
        return False

    if duplicate_rows != 0:
        print(f"FAIL: Re-run produced {duplicate_rows} duplicate rows! Idempotency failed.")
        await conn.close()
        return False

    if audit_row_2 is None:
        print("FAIL: No audit log entry recorded for Run 2.")
        await conn.close()
        return False

    # 4. Spot check updated values
    sample_check: Any = await conn.fetchrow(
        """
        SELECT fiscal_year, fiscal_month, depot_id, gl_code, segment_code, amount
        FROM nerolac_ops.sap_trial_balances
        WHERE fiscal_year = $1 AND fiscal_month = $2 AND depot_id = $3
          AND gl_code = $4 AND segment_code = $5;
        """,
        updated_records[0].fiscal_year,
        updated_records[0].fiscal_month,
        updated_records[0].depot_id,
        updated_records[0].gl_code,
        updated_records[0].segment_code,
    )

    if sample_check is None or float(sample_check["amount"]) != float(updated_records[0].amount):
        print(f"FAIL: Sample value not updated correctly: {sample_check}")
        await conn.close()
        return False

    await conn.close()

    print("\n" + "=" * 78)
    print("  VERIFICATION PROTOCOL RESULTS: ALL CHECKS PASSED ✨")
    print("=" * 78)
    print(f"  [✓] 50,000 Synthetic Rows Backfill Time:  {t_run1:.3f}s (< 10.0s SLA)")
    print(f"  [✓] 50,000 Rows Re-run Time:             {t_run2:.3f}s (< 10.0s SLA)")
    print("  [✓] Duplicate Rows on Re-run:            0 duplicates")
    print("  [✓] Execution Metrics Logged:            audit_logs table verified")
    print(f"  [✓] Batch Chunking:                      {batch_size:,} rows/chunk")
    print("  [✓] Idempotent ON CONFLICT Upsert:       Verified")
    print("=" * 78)
    return True


def main() -> None:
    """CLI entry point for historical backfill verification."""
    parser = argparse.ArgumentParser(
        description="Verify 50,000-Row Historical SAP Backfill with Idempotent Upserts"
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=50000,
        help="Number of synthetic rows to test (default: 50,000)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Chunk batch size (default: 5,000)",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not truncate table before running",
    )

    args = parser.parse_args()

    success = asyncio.run(
        run_backfill_test(
            num_rows=args.rows,
            batch_size=args.batch_size,
            reset=not args.no_reset,
        )
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
